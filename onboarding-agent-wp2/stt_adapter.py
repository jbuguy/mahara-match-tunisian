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

    from transcription import transcrire_reponse_exacte

    resultat = transcrire_reponse_exacte(chemin_audio, types_existants[type_reponse])
    return {
        "texte_brut": resultat.texte_brut,
        "valeur_extraite": resultat.valeur_normalisee,
    }