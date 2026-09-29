import json
import os
import uuid

from cv_parser import build_profile_from_cv
from cv_adapter import adapter_profil_vers_contrat
from scoring import classer_offres, generer_roadmap

# ---- Test 1 : ton vrai CV contre deux offres (comparaison par nom) ----
brut = build_profile_from_cv("data/cv_exemple.docx", "cand_demo")
profil = adapter_profil_vers_contrat(brut, governorate_code="TN-71")

offres = [
    {
        "job_offer_id": "offre-backend",
        "min_years_experience": 3,
        "location": {"governorate_code": "TN-71"},
        "skills": [
            {"label_raw": "Python", "requirement": "required", "min_level": 3},
            {"label_raw": "Django", "requirement": "required", "min_level": 3},
            {"label_raw": "SQL", "requirement": "required", "min_level": 2},
            {"label_raw": "Kubernetes", "requirement": "preferred", "min_level": 2},
            {"label_raw": "Communication", "requirement": "preferred", "min_level": 2},
        ],
    },
    {
        "job_offer_id": "offre-agricole",
        "min_years_experience": 2,
        "location": {"governorate_code": "TN-51"},
        "skills": [
            {"label_raw": "Irrigation", "requirement": "required", "min_level": 2},
            {"label_raw": "Gestion des sols", "requirement": "required", "min_level": 2},
        ],
    },
]

resultat = classer_offres(profil, offres)
print("=== TEST 1 : classement ===")
for m in resultat["items"]:
    print(m["job_offer_id"], "->", m["score_global"], m["breakdown"])
    print("   gaps:", m["gaps"])

assert resultat["items"][0]["job_offer_id"] == "offre-backend", "le backend doit etre premier"
print("\nRoadmap pour l'offre backend :")
print(json.dumps(generer_roadmap(profil, offres[0]), indent=2, ensure_ascii=False))

# ---- Test 2 : exemples du WP1 (avec skill_code), valides par le contrat ----
print("\n=== TEST 2 : exemples WP1 + validation du contrat ===")
from mahara_data.schemas.matching import MatchResult, RankedMatches, Roadmap

dossier = os.path.join(os.path.dirname(__file__), "..", "data-layer-wp1", "contracts", "examples")
with open(os.path.join(dossier, "candidate_profile.cv_upload.json"), encoding="utf-8") as f:
    profil_wp1 = json.load(f)
with open(os.path.join(dossier, "job_offer.json"), encoding="utf-8") as f:
    offre_wp1 = json.load(f)

profil_wp1["candidate_id"] = str(uuid.uuid4())
offre_wp1["job_offer_id"] = str(uuid.uuid4())

res2 = classer_offres(profil_wp1, [offre_wp1])
MatchResult(**res2["items"][0])
RankedMatches(**res2)
print("Score :", res2["items"][0]["score_global"])
print("MatchResult et RankedMatches valides selon le contrat WP1")

roadmap = generer_roadmap(profil_wp1, offre_wp1)
if roadmap:
    Roadmap(**roadmap)
    print("Roadmap valide selon le contrat WP1")
else:
    print("Aucun gap : pas de roadmap necessaire")