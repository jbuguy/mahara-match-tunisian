import importlib


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

    transcription = _transcription_module()
    resultat = transcription.transcrire_reponse_exacte(chemin_audio, types_existants[type_reponse])
    return {
        "texte_brut": resultat.texte_brut,
        "valeur_extraite": resultat.valeur_normalisee,
    }