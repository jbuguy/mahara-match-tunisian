import unicodedata
from datetime import datetime, timezone

WEIGHTS = {"hard_skills": 0.50, "experience": 0.20, "soft_skills": 0.15, "location": 0.15}
REQ_W = {"required": 1.0, "preferred": 0.5}
MODEL_VERSION = "wp3-hybrid-0.1"

# Tant que la taxonomie WP1 n'est pas remplie, on reconnait les soft skills courantes
SOFT_LABELS = {
    "communication", "autonomie", "leadership", "travail en equipe",
    "esprit d'equipe", "adaptabilite", "creativite", "rigueur", "organisation",
}


def normaliser(texte):
    """minuscules, sans accents, espaces propres : 'Développeur ' -> 'developpeur'"""
    texte = unicodedata.normalize("NFD", texte or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return " ".join(texte.lower().split())


def cle_competence(s):
    """Identifiant de comparaison : skill_code si present, sinon label normalise."""
    return s.get("skill_code") or normaliser(s.get("label_raw", ""))


def est_soft(s):
    code = s.get("skill_code") or ""
    return (
        s.get("skill_type") == "soft"
        or code.startswith("SK-05")
        or normaliser(s.get("label_raw", "")) in SOFT_LABELS
    )


def _niveaux_candidat(profil):
    return {cle_competence(s): s["level"] for s in profil.get("skills", [])}


def _score_competences(profil, offre, soft):
    cand = _niveaux_candidat(profil)
    total = obtenu = 0.0
    for s in offre.get("skills", []):
        if est_soft(s) != soft:
            continue
        poids = REQ_W[s["requirement"]]
        niveau_requis = s.get("min_level", 1)
        total += poids
        obtenu += poids * min(cand.get(cle_competence(s), 0) / niveau_requis, 1.0)
    return 100.0 if total == 0 else round(100 * obtenu / total, 1)


def score_experience(profil, offre):
    requis = offre.get("min_years_experience", 0)
    if requis == 0:
        return 100.0
    return round(100 * min(profil.get("years_experience", 0) / requis, 1.0), 1)


def score_localisation(profil, offre):
    gov_offre = offre.get("location", {}).get("governorate_code")
    gov_cand = (profil.get("location") or {}).get("governorate_code")
    if not gov_offre or not gov_cand:
        return 50.0                      # information manquante : score neutre
    if gov_cand == gov_offre:
        return 100.0
    if gov_offre in (profil.get("mobility") or {}).get("governorates", []):
        return 70.0
    return 0.0


def detecter_gaps(profil, offre):
    """Competences de l'offre absentes du profil ou de niveau insuffisant."""
    cand = _niveaux_candidat(profil)
    gaps = []
    for s in offre.get("skills", []):
        cle = cle_competence(s)
        requis = s.get("min_level", 1)
        niveau = cand.get(cle)
        if niveau is not None and niveau >= requis:
            continue
        gap = {
            "gap_type": "missing" if niveau is None else "insufficient_level",
            "requirement": s["requirement"],
            "required_level": requis,
        }
        if s.get("skill_code"):
            gap["skill_code"] = s["skill_code"]
        else:
            gap["label_raw"] = s.get("label_raw")   # taxonomie WP1 pas encore disponible
        if niveau is not None:
            gap["current_level"] = niveau
        gaps.append(gap)
    return gaps


def calculer_match(profil, offre):
    b = {
        "hard_skills": _score_competences(profil, offre, soft=False),
        "experience": score_experience(profil, offre),
        "soft_skills": _score_competences(profil, offre, soft=True),
        "location": score_localisation(profil, offre),
    }
    return {
        "candidate_id": profil.get("candidate_id"),
        "job_offer_id": offre.get("job_offer_id"),
        "score_global": round(sum(b[k] * WEIGHTS[k] for k in WEIGHTS), 1),
        "breakdown": b,
        "weights": WEIGHTS,
        "gaps": detecter_gaps(profil, offre),
        "model_version": MODEL_VERSION,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def classer_offres(profil, offres):
    """Calcule le match pour chaque offre et trie du meilleur au moins bon."""
    items = sorted(
        (calculer_match(profil, o) for o in offres),
        key=lambda m: m["score_global"],
        reverse=True,
    )
    return {
        "subject_id": profil.get("candidate_id"),
        "subject_type": "candidate",
        "items": items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generer_roadmap(profil, offre):
    """Roadmap ordonnee : competences obligatoires d'abord, manquantes avant niveau insuffisant."""
    gaps = detecter_gaps(profil, offre)
    if not gaps:
        return None
    gaps.sort(key=lambda g: (g["requirement"] != "required", g["gap_type"] != "missing"))
    steps = []
    for i, g in enumerate(gaps, start=1):
        step = {"position": i, "status": "todo"}
        step["skill_code" if "skill_code" in g else "label_raw"] = g.get("skill_code") or g.get("label_raw")
        steps.append(step)
    return {
        "candidate_id": profil.get("candidate_id"),
        "target_job_offer_id": offre.get("job_offer_id"),
        "status": "active",
        "progress_pct": 0,
        "steps": steps,
        "model_version": "wp3-roadmap-0.1",
    }