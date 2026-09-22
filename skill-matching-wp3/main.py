import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn

from cv_parser import build_profile_from_cv

app = FastAPI(title="WP3 - Skill Matching Engine API")


@app.get("/")
def home():
    return {"message": "WP3 Skill Matching Engine API est operationnel"}


EXTENSIONS_AUTORISEES = {".pdf", ".docx"}


@app.post("/api/v1/parse-cv")
async def parser_cv(candidat_id: str, fichier: UploadFile = File(...)):
    """
    Recoit un fichier CV envoye par le navigateur (PDF ou DOCX),
    l'enregistre temporairement, extrait le profil, puis supprime le fichier temporaire.
    """
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
        profil = build_profile_from_cv(chemin_temporaire, candidat_id)
    finally:
        os.remove(chemin_temporaire)

    return {"status": "success", "profil": profil}


@app.post("/api/v1/match")
def match_candidat_offres(candidat_id: str):
    return {
        "status": "success",
        "candidat_id": candidat_id,
        "matches": [
            {
                "offre_id": "OFFRE_101",
                "titre": "Technicien Agricole",
                "score_global": 85.5,
                "detail_scores": {
                    "hard_skills": 90,
                    "experience": 80,
                    "soft_skills": 85,
                    "localisation": 80,
                },
            }
        ],
    }


@app.get("/api/v1/roadmap/{candidat_id}/{offre_id}")
def obtenir_roadmap_formation(candidat_id: str, offre_id: str):
    return {
        "candidat_id": candidat_id,
        "offre_id": offre_id,
        "gaps_detectes": ["Irrigation automatique", "Gestion des sols"],
        "roadmap_recommandee": [
            {"module": "Formation Irrigation Nivelee", "duree": "3 jours", "prestataire": "WP1 Catalog"}
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)