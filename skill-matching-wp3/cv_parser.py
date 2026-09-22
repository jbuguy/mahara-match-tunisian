import re
from pypdf import PdfReader
from docx import Document

# Titres de sections reconnus dans un CV (insensible a la casse).
# Si le CV de quelqu'un utilise d'autres titres (ex: "Skills" au lieu de
# "Competences techniques"), ajoute-les dans les listes correspondantes.
TITRES_SECTIONS = {
    "profil": ["profil", "resume", "a propos", "summary"],
    "hard_skills": ["competences techniques", "competences", "skills", "technical skills"],
    "soft_skills": ["competences relationnelles", "soft skills", "qualites"],
    "experience": ["experience professionnelle", "experience", "parcours professionnel"],
    "formation": ["formation", "education", "diplomes"],
}


def extract_text_from_pdf(chemin_fichier):
    """Extrait tout le texte brut d'un CV au format PDF."""
    texte = ""
    reader = PdfReader(chemin_fichier)
    for page in reader.pages:
        texte += (page.extract_text() or "") + "\n"
    return texte


def extract_text_from_docx(chemin_fichier):
    """Extrait tout le texte brut d'un CV au format DOCX, ligne par ligne."""
    document = Document(chemin_fichier)
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(chemin_fichier):
    """Detecte le format du fichier et extrait son texte."""
    if chemin_fichier.lower().endswith(".pdf"):
        return extract_text_from_pdf(chemin_fichier)
    elif chemin_fichier.lower().endswith(".docx"):
        return extract_text_from_docx(chemin_fichier)
    else:
        raise ValueError("Format non supporte : utilise un .pdf ou .docx")


def extract_nom(texte):
    """Le nom est presque toujours ecrit sur la toute premiere ligne du CV."""
    lignes = [l.strip() for l in texte.split("\n") if l.strip()]
    return lignes[0] if lignes else "Nom inconnu"


def _identifier_section(ligne, titres_connus):
    """Verifie si une ligne correspond a un titre de section connu."""
    ligne_clean = ligne.strip().lower().rstrip(":")
    for cle, titres in titres_connus.items():
        if ligne_clean in titres:
            return cle
    return None


def decouper_en_sections(texte):
    """
    Parcourt le CV ligne par ligne et regroupe le contenu sous chaque
    titre de section detecte (Profil, Competences techniques, etc).
    Retourne un dictionnaire {nom_section: texte_de_la_section}.
    """
    sections = {cle: [] for cle in TITRES_SECTIONS}
    section_courante = None

    for ligne in texte.split("\n"):
        ligne = ligne.strip()
        if not ligne:
            continue
        section_detectee = _identifier_section(ligne, TITRES_SECTIONS)
        if section_detectee:
            section_courante = section_detectee
            continue
        if section_courante:
            sections[section_courante].append(ligne)

    return {cle: "\n".join(lignes) for cle, lignes in sections.items()}


def extraire_liste_competences(texte_section):
    """
    Transforme le texte brut d'une section competences en liste propre.
    Gere les puces (·, -, *) et les virgules comme separateurs.
    """
    if not texte_section:
        return []
    texte_section = re.sub(r"^[\u00b7\-\*]\s*", "", texte_section, flags=re.MULTILINE)
    morceaux = re.split(r"[,\n]", texte_section)
    return [m.strip() for m in morceaux if m.strip()]


def extract_experience_years(texte):
    """Cherche un nombre d'annees d'experience explicitement mentionne dans le texte."""
    motifs = [
        r"(\d+)\s*(?:ans|an)\s*d[\'e]\s*exp[ee]rience",
        r"(\d+)\+?\s*years?\s*(?:of)?\s*experience",
        r"exp[ee]rience\s*:?\s*(\d+)\s*(?:ans|an|years?)",
    ]
    for motif in motifs:
        match = re.search(motif, texte, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def build_profile_from_cv(chemin_fichier, candidat_id):
    """
    Pipeline complet : lit le CV, le decoupe en sections, et extrait
    TOUT le contenu present (pas seulement des mots d'une liste fixe).
    """
    texte = extract_text(chemin_fichier)
    sections = decouper_en_sections(texte)

    return {
        "id": candidat_id,
        "nom": extract_nom(texte),
        "profil_resume": sections["profil"],
        "hard_skills": extraire_liste_competences(sections["hard_skills"]),
        "soft_skills": extraire_liste_competences(sections["soft_skills"]),
        "experience_annees": extract_experience_years(texte),
        "experience_detail": sections["experience"],
        "formation": sections["formation"],
        "localisation": None,
        "mobilite_km": 0,
    }


if __name__ == "__main__":
    profil = build_profile_from_cv("data/cv_exemple.docx", "cand_demo")
    print("Profil extrait automatiquement du CV :")
    for cle, valeur in profil.items():
        print(f"  {cle}: {valeur}")