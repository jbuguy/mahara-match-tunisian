"""
Onboarding agent - transcription vocale guidée par contexte
=============================================================
Architecture en 2 couches :
  1. ASR (faster-whisper) avec initial_prompt riche en entités attendues
  2. Post-traitement : matching flou contre listes fermées + parsing de dates

Pourquoi faster-whisper plutôt que openai-whisper :
  - Même qualité de modèle (mêmes poids Whisper), mais backend CTranslate2
  - 3-4x plus rapide sur CPU grâce à la quantification (int8)
  - Pour des clips courts (2-5s), le CPU est largement suffisant : pas besoin de GPU ici.
    Le GPU ne devient utile que si tu as beaucoup de requêtes concurrentes ou du
    streaming long en continu.

Installation :
    pip install faster-whisper pydub rapidfuzz
    (pydub nécessite ffmpeg installé sur la machine : https://ffmpeg.org/download.html)
"""

import os
import re
from dataclasses import dataclass
from typing import Optional

from faster_whisper import WhisperModel
from pydub import AudioSegment
from rapidfuzz import fuzz, process

print("Chargement du modèle Whisper 'small' (faster-whisper, CPU, int8)...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Modèle prêt !")

GOUVERNORATS = [
    "Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Zaghouan", "Bizerte",
    "Béja", "Jendouba", "Le Kef", "Siliana", "Sousse", "Monastir", "Mahdia",
    "Sfax", "Kairouan", "Kasserine", "Sidi Bouzid", "Gabès", "Médenine",
    "Tataouine", "Gafsa", "Tozeur", "Kébili",
]
GOUVERNORATS_AR = [
    "تونس", "أريانة", "بن عروس", "منوبة", "نابل", "زغوان", "بنزرت",
    "باجة", "جندوبة", "الكاف", "سليانة", "سوسة", "المنستير", "المهدية",
    "صفاقس", "القيروان", "القصرين", "سيدي بوزيد", "قابس", "مدنين",
    "تطاوين", "قفصة", "توزر", "قبلي",
]
METIERS = [
    "najar", "haddad", "banna", "dahan", "plombier", "fellah",
    "électricien", "maçon", "menuisier", "agriculture", "peintre", "soudeur",
]
METIERS_AR = [
    "نجار", "حداد", "بناء", "دهان", "بلوماسي", "فلاح",
    "كهربائي", "معلم بناء", "نجار", "زراعة", "صباغ", "لحام",
]
MOIS_AR_FOSHA = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]
MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
CHIFFRES_ARABES = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}
NOMBRES_LETTRES_AR = {
    "واحد": "1", "اثنين": "2", "ثلاثة": "3", "أربعة": "4", "خمسة": "5",
    "ستة": "6", "سبعة": "7", "ثمانية": "8", "تسعة": "9", "عشرة": "10",
    "أحد عشر": "11", "اثنا عشر": "12", "ثلاثة عشر": "13", "أربعة عشر": "14",
    "خمسة عشر": "15", "ستة عشر": "16", "سبعة عشر": "17", "ثمانية عشر": "18",
    "تسعة عشر": "19", "عشرين": "20", "ثلاثين": "30",
}
UNITES_AR = {
    "صفر": 0, "واحد": 1, "أحد": 1, "اثنان": 2, "اثنين": 2, "ثلاثة": 3, "أربعة": 4,
    "خمسة": 5, "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9,
}
DIZAINES_SPECIALES_AR = {
    "عشرة": 10, "أحد عشر": 11, "اثنا عشر": 12, "اثنى عشر": 12,
    "ثلاثة عشر": 13, "أربعة عشر": 14, "خمسة عشر": 15, "ستة عشر": 16,
    "سبعة عشر": 17, "ثمانية عشر": 18, "تسعة عشر": 19,
}
DIZAINES_AR = {
    "عشرون": 20, "عشرين": 20, "ثلاثون": 30, "ثلاثين": 30,
    "أربعون": 40, "أربعين": 40, "خمسون": 50, "خمسين": 50,
    "ستون": 60, "ستين": 60, "سبعون": 70, "سبعين": 70,
    "ثمانون": 80, "ثمانين": 80, "تسعون": 90, "تسعين": 90,
}
CENTAINES_AR = {
    "مائة": 100, "مئة": 100, "مئتان": 200, "مئتين": 200, "مائتان": 200, "مائتين": 200,
    "ثلاثمائة": 300, "ثلاثمئة": 300, "أربعمائة": 400, "أربعمئة": 400,
    "خمسمائة": 500, "خمسمئة": 500, "ستمائة": 600, "ستمئة": 600,
    "سبعمائة": 700, "سبعمئة": 700, "ثمانمائة": 800, "ثمانمئة": 800,
    "تسعمائة": 900, "تسعمئة": 900,
}
SEUIL_FUZZY = 75


def construire_prompt(type_reponse: str) -> str:
    if type_reponse == "job":
        return "إجابة عن سؤال المهنة. المهن الممكنة: " + "، ".join(METIERS_AR) + "."
    if type_reponse == "date":
        return "إجابة عن سؤال التاريخ باللغة العربية الفصحى. الأشهر الممكنة: " + "، ".join(MOIS_AR_FOSHA) + "."
    if type_reponse == "adresse":
        return "إجابة عن سؤال الولاية. الولايات الممكنة: " + "، ".join(GOUVERNORATS_AR) + "."
    if type_reponse == "phone":
        return (
            "المترشح يعطي رقم هاتفه المكون من 8 أرقام، مقسم إلى مجموعات من ثلاثة "
            "أرقام باللغة العربية الفصحى، مثل: تسعمائة وثمانية وتسعون، مئة وثلاثة "
            "وعشرون، خمسة وأربعون."
        )
    return "إجابة قصيرة باللغة العربية الفصحى."


def preparer_audio_court(chemin_audio: str) -> str:
    audio = AudioSegment.from_file(chemin_audio)
    if len(audio) < 2500:
        silence = AudioSegment.silent(duration=500)
        audio_rembourre = silence + audio + silence
        base, _ext = os.path.splitext(chemin_audio)
        chemin_temp = base + "_padded.wav"
        audio_rembourre.export(chemin_temp, format="wav")
        return chemin_temp
    return chemin_audio


def transcrire_brut(chemin_audio: str, type_reponse: str = "") -> str:
    if not os.path.exists(chemin_audio):
        raise FileNotFoundError(f"Fichier introuvable : {chemin_audio}")
    chemin_final = preparer_audio_court(chemin_audio)
    segments, _info = model.transcribe(
        chemin_final,
        language="ar",
        initial_prompt=construire_prompt(type_reponse),
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        condition_on_previous_text=False,
        vad_filter=False,
        beam_size=5,
    )
    texte = " ".join(seg.text for seg in segments).strip()
    if chemin_final != chemin_audio and os.path.exists(chemin_final):
        os.remove(chemin_final)
    return texte


@dataclass
class ResultatExtraction:
    texte_brut: str
    valeur_normalisee: Optional[str]
    score_confiance: Optional[float]


def nettoyer_repetitions(texte: str) -> str:
    return re.sub(r'(\b[\w،]+\b[\s،]*)\1{2,}', r'\1', texte).strip()


def normaliser_chiffres_arabes(texte: str) -> str:
    for ar, latin in CHIFFRES_ARABES.items():
        texte = texte.replace(ar, latin)
    return texte


def extraire_metier(texte_brut: str, seuil: int = 60) -> ResultatExtraction:
    texte_brut = nettoyer_repetitions(texte_brut)
    candidats = METIERS + METIERS_AR
    match = process.extractOne(texte_brut, candidats, scorer=fuzz.ratio)
    if match:
        cand, score, _ = match
        ecart = abs(len(texte_brut) - len(cand))
        tolerance = max(1, round(0.2 * len(cand)))
        if score >= 70 and ecart <= tolerance:
            return ResultatExtraction(texte_brut, cand, score)
    return ResultatExtraction(texte_brut, None, match[1] if match else None)


def extraire_gouvernorat(texte_brut: str, seuil: int = 60) -> ResultatExtraction:
    texte_brut = nettoyer_repetitions(texte_brut)
    candidats = GOUVERNORATS + GOUVERNORATS_AR
    match = process.extractOne(texte_brut, candidats, scorer=fuzz.ratio)
    if match:
        cand, score, _ = match
        ecart = abs(len(texte_brut) - len(cand))
        tolerance = max(1, round(0.2 * len(cand)))
        if score >= 70 and ecart <= tolerance:
            idx = candidats.index(cand)
            idx_ar = idx if idx >= len(GOUVERNORATS) else idx + len(GOUVERNORATS)
            idx_arabe = idx - len(GOUVERNORATS) if idx >= len(GOUVERNORATS) else idx
            return ResultatExtraction(texte_brut, GOUVERNORATS_AR[idx_arabe], score)
    return ResultatExtraction(texte_brut, None, match[1] if match else None)


def extraire_date(texte_brut: str) -> ResultatExtraction:
    texte_brut = nettoyer_repetitions(texte_brut)
    texte = normaliser_chiffres_arabes(texte_brut)
    for mot, chiffre in NOMBRES_LETTRES_AR.items():
        texte = texte.replace(mot, chiffre)
    if not re.search(r"\b\d{1,2}\b", texte):
        for mot in texte.split():
            match_nombre = process.extractOne(
                mot, NOMBRES_LETTRES_AR.keys(), scorer=fuzz.ratio
            )
            if match_nombre:
                candidat, score, _ = match_nombre
                ecart = abs(len(mot) - len(candidat))
                tolerance = max(1, round(0.35 * len(candidat)))
                if score >= 52 and ecart <= tolerance:
                    texte = texte.replace(mot, NOMBRES_LETTRES_AR[candidat], 1)
                    break
    match_jour = re.search(r"\b(\d{1,2})\b", texte)
    jour = match_jour.group(1) if match_jour else None
    mois_trouve = None
    for mois_ar, mois_fr in zip(MOIS_AR_FOSHA, MOIS_FR):
        if mois_ar in texte or mois_fr.lower() in texte.lower():
            mois_trouve = mois_ar
            break
    if jour and mois_trouve:
        return ResultatExtraction(texte_brut, f"{jour} {mois_trouve}", 100.0)
    if jour or mois_trouve:
        return ResultatExtraction(texte_brut, f"{jour or '?'} {mois_trouve or '?'}", 50.0)
    return ResultatExtraction(texte_brut, None, 0.0)


def _nettoyer_token(token: str) -> str:
    token = token.strip("،, .")
    if token.startswith("و") and len(token) > 2:
        return token[1:]
    return token


def _meilleur_match(token: str, dictionnaire: dict, seuil: int = SEUIL_FUZZY):
    if not token:
        return None
    resultat = process.extractOne(token, dictionnaire.keys(), scorer=fuzz.ratio)
    if not resultat:
        return None
    candidat, score, _ = resultat
    ecart_longueur = abs(len(token) - len(candidat))
    tolerance = max(1, round(0.15 * len(candidat)))
    if score >= seuil and ecart_longueur <= tolerance:
        return dictionnaire[candidat]
    return None


def parse_groupe_nombre(texte_groupe: str) -> Optional[int]:
    texte_groupe = texte_groupe.strip()
    if not texte_groupe:
        return None
    _meilleur_match(texte_groupe, DIZAINES_SPECIALES_AR, seuil=70)
    tokens = texte_groupe.split()
    total = 0
    trouve_quelque_chose = False
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            paire = _nettoyer_token(tokens[i]) + " " + _nettoyer_token(tokens[i + 1])
            candidat_teen = process.extractOne(paire, DIZAINES_SPECIALES_AR.keys(), scorer=fuzz.ratio)
            if candidat_teen:
                cand, score, _ = candidat_teen
                if score >= 88 and abs(len(paire) - len(cand)) <= 1:
                    total += DIZAINES_SPECIALES_AR[cand]
                    trouve_quelque_chose = True
                    i += 2
                    continue
        token = _nettoyer_token(tokens[i])
        candidats = []
        for dico in (CENTAINES_AR, DIZAINES_AR, UNITES_AR):
            meilleur = process.extractOne(token, dico.keys(), scorer=fuzz.ratio)
            if meilleur:
                cand, score, _ = meilleur
                ecart = abs(len(token) - len(cand))
                tolerance = max(1, round(0.15 * len(cand)))
                if score >= SEUIL_FUZZY and ecart <= tolerance:
                    candidats.append((score, dico[cand]))
        if candidats:
            candidats.sort(key=lambda c: c[0], reverse=True)
            total += candidats[0][1]
            trouve_quelque_chose = True
        i += 1
    return total if trouve_quelque_chose else None


def extraire_telephone(texte_brut: str) -> ResultatExtraction:
    texte_brut = nettoyer_repetitions(texte_brut)
    chiffres_ar = {"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"}
    for ar, latin in chiffres_ar.items():
        texte_brut = texte_brut.replace(ar, latin)
    resultat = ""
    for groupe in re.split(r"[،,.]", texte_brut):
        groupe = groupe.strip()
        if not groupe:
            continue
        if re.fullmatch(r"\d+", groupe):
            resultat += groupe
            continue
        valeur = parse_groupe_nombre(groupe)
        if valeur is not None:
            resultat += str(valeur)
    numero = resultat if resultat else None
    return ResultatExtraction(texte_brut, numero, 90.0 if numero is not None else 0.0)


def transcrire_reponse_exacte(chemin_audio: str, type_reponse: str = "") -> ResultatExtraction:
    texte_brut = transcrire_brut(chemin_audio, type_reponse)
    if type_reponse == "job":
        return extraire_metier(texte_brut)
    if type_reponse == "adresse":
        return extraire_gouvernorat(texte_brut)
    if type_reponse == "date":
        return extraire_date(texte_brut)
    if type_reponse == "phone":
        return extraire_telephone(texte_brut)
    return ResultatExtraction(texte_brut, texte_brut, None)


if __name__ == "__main__":
    import os

    dossier = r"C:\Users\wesle\OneDrive\Desktop\mahara-match-tunisian\onboarding-agent-wp2\audio_test_reponse"

    tests = [
        ("2octobree .aac", "date"),
        ("truesiliena.aac", "adresse"),
        ("2 novembre .aac", "date"),
        ("11 septembre.aac", "date"),
        ("hon.aac", "job"),
        ("truenajar.aac", "job"),
        ("dahen.aac", "job"),
        ("91131139.aac", "phone"),
    ]

    for fichier, type_q in tests:
        chemin = os.path.join(dossier, fichier)
        print(f"\n--- {fichier} (type={type_q}) ---")
        try:
            resultat = transcrire_reponse_exacte(chemin, type_q)
            print(f"  Texte brut Whisper : {resultat.texte_brut!r}")
            print(f"  Valeur normalisée  : {resultat.valeur_normalisee}")
            print(f"  Confiance          : {resultat.score_confiance}")
        except FileNotFoundError as e:
            print(f"  Erreur : {e}")
