import json
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import BadZipFile

from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, UploadFile, File, HTTPException
from pypdf.errors import PdfReadError
import uvicorn

from cv_parser import build_profile_from_cv
from cv_adapter import adapter_profil_vers_contrat
from id_utils import canonical_id
from profile_store import SQLiteProfileStore
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
FICHIER_PROFILS = Path(__file__).resolve().parent / "data" / "wp3.sqlite3"


def charger_offres():
    with open(FICHIER_OFFRES, encoding="utf-8") as f:
        return json.load(f)


def offres_avec_ids_uuid():
    """Expose stable UUIDs while retaining legacy keys for route lookup."""
    return [
        {**offre, "job_offer_id": canonical_id(str(offre["job_offer_id"]))}
        for offre in charger_offres()
    ]


def create_app(database_path: str | Path | None = None) -> FastAPI:
    profile_store = SQLiteProfileStore(database_path or FICHIER_PROFILS)
    api = FastAPI(
        title="WP3 - Skill Matching Engine API",
        description="CV → profil au format WP1 → offres → matching → roadmap.",
        openapi_tags=[{"name": t} for t in (TAG_1, TAG_2, TAG_3, TAG_4)],
    )

    def profil_du_candidat(candidat_id: str):
        profil = profile_store.get(candidat_id)
        if profil is None:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun profil pour '{candidat_id}'. Fais d'abord l'etape 1 : POST /api/v1/parse-cv",
            )
        return profil

    @api.get("/", include_in_schema=False)
    def home():
        return {"message": "WP3 Skill Matching Engine API est operationnel"}

    # ---------- 1 · Parser le CV ----------

    @api.post("/api/v1/parse-cv", tags=[TAG_1])
    async def parser_cv(
        candidat_id: str,
        governorate_code: str | None = None,
        fichier: UploadFile = File(...),
    ):
        """CV (PDF ou DOCX) -> profil au format WP1, sans donnees personnelles."""
        filename = fichier.filename or ""
        extension = os.path.splitext(filename)[1].lower()
        if extension not in EXTENSIONS_AUTORISEES:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporte : {extension}. Utilise un .pdf ou .docx",
            )

        chemin_temporaire = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                chemin_temporaire = tmp.name
                shutil.copyfileobj(fichier.file, tmp)
            profil_brut = build_profile_from_cv(chemin_temporaire, candidat_id)
        except (BadZipFile, PackageNotFoundError, PdfReadError, OSError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail="Le fichier CV est illisible ou corrompu.",
            ) from exc
        finally:
            if chemin_temporaire and os.path.exists(chemin_temporaire):
                os.remove(chemin_temporaire)

        profil = adapter_profil_vers_contrat(profil_brut, governorate_code)
        profil = profile_store.save(candidat_id, profil)
        return {"status": "success", "candidat_id": candidat_id, "profil": profil}

    # ---------- 2 · Lire les offres ----------

    @api.get("/api/v1/offres", tags=[TAG_2])
    def lister_offres():
        """Lit les offres d'exemple et expose des identifiants UUID stables."""
        return offres_avec_ids_uuid()

    # ---------- 3 · Matching ----------

    @api.post("/api/v1/match", tags=[TAG_3])
    def match_candidat_offres(candidat_id: str):
        """Score les offres du candidat et les classe avec le detail et les gaps."""
        return classer_offres(profil_du_candidat(candidat_id), offres_avec_ids_uuid())

    # ---------- 4 · Roadmap ----------

    @api.get("/api/v1/roadmap/{candidat_id}/{offre_id}", tags=[TAG_4])
    def obtenir_roadmap(candidat_id: str, offre_id: str):
        """Competences a acquerir (obligatoires d'abord) pour viser cette offre."""
        offre_id_uuid = canonical_id(offre_id)
        offre = next(
            (
                {**item, "job_offer_id": canonical_id(str(item["job_offer_id"]))}
                for item in charger_offres()
                if canonical_id(str(item["job_offer_id"])) == offre_id_uuid
            ),
            None,
        )
        if offre is None:
            raise HTTPException(status_code=404, detail=f"Offre inconnue : {offre_id}")
        roadmap = generer_roadmap(profil_du_candidat(candidat_id), offre)
        if roadmap is None:
            return {"status": "no_gap", "message": "Le candidat couvre deja toutes les competences de l'offre"}
        return roadmap

    api.state.profile_store = profile_store
    return api


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)