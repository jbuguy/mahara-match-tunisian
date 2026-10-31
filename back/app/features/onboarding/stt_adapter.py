import importlib
import asyncio

from app.services.speech.speech_service import get_speech_service


def _transcription_module():
    module_name = f"{__package__}.transcription" if __package__ else "transcription"
    return importlib.import_module(module_name)


def initialiser_moteur_stt():
    return _transcription_module()


def transcrire_et_extraire(chemin_audio, type_reponse):
    types_existants = {
        "métier": "job",
        "job": "job",
        "date": "date",
        "gouvernorat": "adresse",
        "adresse": "adresse",
        "téléphone": "phone",
        "telephone": "phone",
        "phone": "phone",
        "texte libre": "",
        "texte_libre": "",
    }
    if type_reponse not in types_existants:
        raise ValueError(f"Type de réponse non pris en charge : {type_reponse}")

    result = asyncio.run(get_speech_service().provider.transcribe(chemin_audio, "ar-TN"))
    if not result["success"]:
        return {"texte_brut": "", "valeur_extraite": None}
    transcription = _transcription_module()
    extraction = getattr(transcription, f"extraire_{'gouvernorat' if types_existants[type_reponse] == 'adresse' else types_existants[type_reponse]}", None)
    if types_existants[type_reponse] == "job":
        extraction = transcription.extraire_metier
    elif types_existants[type_reponse] == "adresse":
        extraction = transcription.extraire_gouvernorat
    elif types_existants[type_reponse] == "date":
        extraction = transcription.extraire_date
    elif types_existants[type_reponse] == "phone":
        extraction = transcription.extraire_telephone
    else:
        extraction = lambda text: text
    extracted = extraction(result["text"])
    value = extracted if isinstance(extracted, str) else extracted.valeur_normalisee
    return {
        "texte_brut": result["text"],
        "valeur_extraite": value,
    }
