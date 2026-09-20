from fastapi import FastAPI
import uvicorn

app = FastAPI(title="WP3 - Skill Matching Engine API")

@app.get("/")
def home():
    return {"message": "WP3 Skill Matching Engine API est operationnel"}

# SCRUM-40 : Endpoint de Match et Scoring
@app.post("/api/v1/match")
def match_candidat_offres(candidat_id: str):
    """
    Retourne la liste des offres triees par score decroissant.
    """
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
                    "localisation": 80
                }
            }
        ]
    }

# SCRUM-16 / SCRUM-29 : Endpoint Roadmap de Formation
@app.get("/api/v1/roadmap/{candidat_id}/{offre_id}")
def obtenir_roadmap_formation(candidat_id: str, offre_id: str):
    """
    Retourne la detection des gaps et les modules de formation conseilles.
    """
    return {
        "candidat_id": candidat_id,
        "offre_id": offre_id,
        "gaps_detectes": ["Irrigation automatique", "Gestion des sols"],
        "roadmap_recommandee": [
            {"module": "Formation Irrigation Nivelee", "duree": "3 jours", "prestataire": "WP1 Catalog"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)