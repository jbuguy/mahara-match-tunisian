import os
import whisper
from pydub import AudioSegment

# 1. Utiliser le modèle 'small' (beaucoup plus robuste que 'base' pour les mots courts)
model = None


def obtenir_modele():
    global model
    if model is None:
        print("Chargement du modèle Whisper 'small'...")
        model = whisper.load_model("small")
        print("Modèle 'small' prêt !")
    return model

def preparer_audio_court(chemin_audio: str) -> str:
    """
    Ajoute 0.5s de silence avant et après l'audio s'il est très court.
    Cela empêche Whisper d'halluciner sur des mots de 1 seconde.
    """
    audio = AudioSegment.from_file(chemin_audio)
    
    # Si l'audio fait moins de 2,5 secondes, on le rembourre de silence
    if len(audio) < 2500:
        silence = AudioSegment.silent(duration=500) # 500ms
        audio_rembourre = silence + audio + silence
        
        base, _extension = os.path.splitext(chemin_audio)
        chemin_temp = base + "_padded.wav"
        audio_rembourre.export(chemin_temp, format="wav")
        return chemin_temp
    
    return chemin_audio

def transcrire_reponse_exacte(chemin_audio: str, type_reponse: str = "") -> str:
    if not os.path.exists(chemin_audio):
        return f"Fichier introuvable : {chemin_audio}"

    # Étape A : Préparation de l'audio court
    chemin_final = preparer_audio_court(chemin_audio)

    # Étape B : Prompts de contexte adaptés selon la question
    prompts_contexte = {
        "job": "Candidat répond à la question métier en dialecte tunisien ou français : fleha, فلاحة, électricien, agriculture, maçon, khadma.",
        "date": "Candidat répond à la question date : 2 octobre, 15 mai, janvier, date, aujourd'hui.",
        "adresse": "Candidat répond à la question lieu : Siliana, سليانة, Tunis, Bizerte, gouvernorat.",
        "phone": "Candidat donne son numéro de téléphone : 22113344, 98123456, numéro."
    }
    
    prompt_selectionne = prompts_contexte.get(type_reponse, "Réponse courte en dialecte tunisien derja ou français.")

    # Étape C : Transcription stricte (temperature=0.0)
    try:
        resultat = obtenir_modele().transcribe(
            chemin_final,
            initial_prompt=prompt_selectionne,
            temperature=0.0,
            condition_on_previous_text=False,
            fp16=False,
        )
    finally:
        if chemin_final != chemin_audio and os.path.exists(chemin_final):
            os.remove(chemin_final)

    return resultat["text"].strip()