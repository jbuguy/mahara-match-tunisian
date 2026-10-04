import uuid

NIVEAU_PAR_DEFAUT = 2      # intermediaire, le CV ne donne pas le niveau
CONFIANCE_PAR_DEFAUT = 0.6  # extraction texte libre = moins sur


def _skills(liste, skill_type):
    return [
        {
            "label_raw": nom[:200],
            "skill_type": skill_type,
            "level": NIVEAU_PAR_DEFAUT,
            "source": "cv",
            "confidence": CONFIANCE_PAR_DEFAUT,
        }
        for nom in liste
    ]


def adapter_profil_vers_contrat(profil_brut, governorate_code=None, source_document_id=None):
    """Transforme la sortie de build_profile_from_cv() au format WP1 (sans PII).

    source_document_id : identifiant du CV stocke par WP1. Tant que le stockage
    n'existe pas, on genere un UUID temporaire.
    """
    return {
        "schema_version": "1.0",
        "candidate_id": None,
        "onboarding_path": "cv_upload",
        "literacy_level": "literate",
        "preferred_language": "fr",
        "location": {"governorate_code": governorate_code},
        "mobility": {"radius_km": profil_brut.get("mobilite_km") or 0, "governorates": []},
        "years_experience": profil_brut["experience_annees"],
        "skills": _skills(profil_brut["hard_skills"], "hard")
                + _skills(profil_brut["soft_skills"], "soft"),
        "summary": profil_brut["profil_resume"] or None,
        "source_document_ids": [source_document_id or str(uuid.uuid4())],
    }