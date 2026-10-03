# Intégration des modules

Un tableau pour que l'intégration (Wassim) sache comment lancer et brancher chaque module.
**Chaque équipe ajoute ou corrige SA ligne, et seulement la sienne.**

| Module | Port par défaut | Commande de lancement | Endpoints principaux | JSON produit | JSON consommé | Prérequis | Statut / limites |
|---|---|---|---|---|---|---|---|
| WP2 onboarding | 8000 (proposé : 8002) | `uvicorn app.api:app --port 8002` (dossier onboarding-agent-wp2) | POST /api/v1/sessions, POST /api/v1/sessions/{id}/reponse, GET .../offre, GET .../recap-audio | métier, date, gouvernorat, téléphone, offre écrite, récap audio | aucun | ffmpeg, Node, modèle Whisper (téléchargé au premier lancement) | Publication vers WP4 non branchée; CSV provisoire |
| WP3 matching | 8000 (variable PORT, proposé : 8003) | `PORT=8003 python main.py` (dossier skill-matching-wp3) | POST /api/v1/match, GET et POST /api/v1/roadmap, GET /api/v1/skills, POST /api/v1/parse-cv | RankedMatches, Roadmap (contrat WP1) | profil (CV), offres | Python, pip install -r requirements-wp3-minimal.txt | Codes SK-9xxx provisoires; embeddings à faire |
| WP4 employeur | | | | | | | |
| WP5 admin | | | | | | | |
| WP6 employé | | | | | | | |

## Règles
- Ports proposés : WP2 8002, WP3 8003, WP4 8004, WP5 8005, WP6 8006.
- Ne mettez aucun secret ici.
- Mettez à jour votre ligne quand votre module change.