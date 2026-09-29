import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn

from cv_parser import build_profile_from_cv
from cv_adapter import adapter_profil_vers_contrat
from scoring import classer_offres, generer_roadmap

app = FastAPI(title="WP3 - Skill Matching Engine API")

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}


class MatchRequest(BaseModel):
    profil: dict          # profil candidat au format WP1
    offres: list[dict]    # offres au format WP1


class RoadmapRequest(BaseModel):
    profil: dict
    offre: dict


@app.get("/")
def home():
    return {"message": "WP3 Skill Matching Engine API est operationnel"}


@app.post("/api/v1/parse-cv")
async def parser_cv(
    candidat_id: str,
    governorate_code: str | None = None,
    fichier: UploadFile = File(...),
):
    """Recoit un CV (PDF ou DOCX) et renvoie le profil au format WP1 (sans PII)."""
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

    return {
        "status": "success",
        "profil": adapter_profil_vers_contrat(profil_brut, governorate_code),
    }


@app.post("/api/v1/match")
def match_candidat_offres(req: MatchRequest):
    """Classe les offres pour un candidat (meilleur score en premier), avec les gaps."""
    if not req.offres:
        raise HTTPException(status_code=400, detail="La liste d'offres est vide")
    return classer_offres(req.profil, req.offres)


@app.post("/api/v1/roadmap")
def obtenir_roadmap_formation(req: RoadmapRequest):
    """Genere la roadmap de formation pour combler les gaps d'une offre."""
    roadmap = generer_roadmap(req.profil, req.offre)
    if roadmap is None:
        return {"status": "no_gap", "message": "Le candidat couvre deja toutes les competences de l'offre"}
    return roadmap


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)