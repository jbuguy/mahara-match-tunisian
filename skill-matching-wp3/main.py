import json
import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn

from cv_parser import build_profile_from_cv
from cv_adapter import adapter_profil_vers_contrat
from scoring import classer_offres, generer_roadmap

TAG_1 = "1 · Parser le CV (format WP1)"
TAG_2 = "2 · Lire les offres"
TAG_3 = "3 · Matching (scores)"
TAG_4 = "4 · Roadmap (compétences manquantes)"

app = FastAPI(
    title="WP3 - Skill Matching Engine API",
    description="CV → profil au format WP1 → offres → matching → roadmap.",
    openapi_tags=[{"name": t} for t in (TAG_1, TAG_2, TAG_3, TAG_4)],
)

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
FICHIER_OFFRES = os.path.join(os.path.dirname(__file__), "data", "offres_exemple.json")

# Profils gardes en memoire (perdus si le serveur redemarre). Plus tard : base WP1.
PROFILS = {}


def charger_offres():
    with open(FICHIER_OFFRES, encoding="utf-8") as f:
        return json.load(f)


def profil_du_candidat(candidat_id: str):
    profil = PROFILS.get(candidat_id)
    if profil is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun profil pour '{candidat_id}'. Fais d'abord l'etape 1 : POST /api/v1/parse-cv",
        )
    return profil


@app.get("/", include_in_schema=False)
def home():
    return {"message": "WP3 Skill Matching Engine API est operationnel"}


# ---------- 1 · Parser le CV ----------

@app.post("/api/v1/parse-cv", tags=[TAG_1])
async def parser_cv(
    candidat_id: str,
    governorate_code: str | None = None,
    fichier: UploadFile = File(...),
):
    """CV (PDF ou DOCX) -> profil au format WP1, sans donnees personnelles."""
    extension = os.path.splitext(fichier.filename)[1].lower()
    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte : {extension}. Utilise un .pdf ou .docx",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        shutil.copyfileobj(fichier.file, tmp)
        chemin_temporaire = tmp.name

    try:
        profil_brut = build_profile_from_cv(chemin_temporaire, candidat_id)
    finally:
        os.remove(chemin_temporaire)

    profil = adapter_profil_vers_contrat(profil_brut, governorate_code)
    PROFILS[candidat_id] = profil
    return {"status": "success", "candidat_id": candidat_id, "profil": profil}


# ---------- 2 · Lire les offres ----------

@app.get("/api/v1/offres", tags=[TAG_2])
def lister_offres():
    """Lit les offres dans data/offres_exemple.json."""
    return charger_offres()


# ---------- 3 · Matching ----------

@app.post("/api/v1/match", tags=[TAG_3])
def match_candidat_offres(candidat_id: str):
    """Score du candidat pour chaque offre, classe du meilleur au moins bon, avec le detail et les gaps."""
    return classer_offres(profil_du_candidat(candidat_id), charger_offres())


# ---------- 4 · Roadmap ----------

@app.get("/api/v1/roadmap/{candidat_id}/{offre_id}", tags=[TAG_4])
def obtenir_roadmap(candidat_id: str, offre_id: str):
    """Competences a acquerir (obligatoires d'abord) pour viser cette offre."""
    offre = next((o for o in charger_offres() if o["job_offer_id"] == offre_id), None)
    if offre is None:
        raise HTTPException(status_code=404, detail=f"Offre inconnue : {offre_id}")
    roadmap = generer_roadmap(profil_du_candidat(candidat_id), offre)
    if roadmap is None:
        return {"status": "no_gap", "message": "Le candidat couvre deja toutes les competences de l'offre"}
    return roadmap


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)