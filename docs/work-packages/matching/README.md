# WP3 — Skill Matching Engine

API FastAPI qui parse un CV, persiste le profil localement, classe les offres
d'exemple et calcule une roadmap à partir des compétences manquantes.

## Installation Windows

Depuis la racine du dépôt :

```powershell
Set-Location .\skill-matching-wp3
py -3.11 -m venv .\venv-wp3
.\venv-wp3\Scripts\python.exe -m pip install -r .\requirements-wp3-minimal.txt
.\venv-wp3\Scripts\python.exe -m pip install -e ..\data-layer-wp1
```

L'installation editable utilise le `data-layer-wp1` de ce dépôt. Le fichier
`requirements-wp3-minimal.txt` ne contient pas de hashes et n'installe pas les
dépendances lourdes d'embedding (`torch`, `sentence-transformers`, `chromadb`).

## Démarrage

Le port par défaut reste **8000**, compatible avec `start.ps1` et le proxy Vite.
Pour isoler WP3 sur **8001**, dans PowerShell :

```powershell
$env:PORT = "8001"
.\venv-wp3\Scripts\python.exe .\main.py
```

Sans la variable `PORT`, `main.py` écoute sur 8000. La documentation Swagger est
disponible à `http://127.0.0.1:8001/docs` si le port 8001 est sélectionné.

Les profils sont conservés dans `data/wp3.sqlite3` et survivent au redémarrage.
Ce fichier local est ignoré par Git.

## Tests

```powershell
.\venv-wp3\Scripts\python.exe -m pytest -q
```

Les tests couvrent le parsing de CV, le scoring, les gaps, le stockage SQLite,
les contrats WP1 et les routes API.

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/v1/parse-cv?candidat_id=...&governorate_code=...` | Envoie le fichier multipart `fichier` (PDF ou DOCX), extrait et persiste le profil. |
| `GET` | `/api/v1/offres` | Retourne les offres avec des `job_offer_id` UUID stables. |
| `POST` | `/api/v1/match?candidat_id=...` | Classe les offres; `candidat_id` accepte la clé textuelle d'origine ou son UUID. |
| `GET` | `/api/v1/roadmap/{candidat_id}/{offre_id}` | Route historique conservée; accepte les clés texte ou UUID. |
| `POST` | `/api/v1/roadmap` | Calcule la même roadmap depuis un corps JSON avec `candidate_id` et `job_offer_id`. |

Les sorties de matching et de roadmap utilisent des UUID pour les identifiants.
Les clés historiques telles que `auto-cand-1` et `offre-backend` restent
acceptées en entrée. Les identifiants textuels sont convertis de façon stable
avec UUID5.

## Exemples HTTP exécutés sur le port 8001

Lancer d'abord le serveur comme décrit ci-dessus, puis exécuter depuis
`skill-matching-wp3` :

```powershell
$base = "http://127.0.0.1:8001"
curl.exe -sS -X POST "$base/api/v1/parse-cv?candidat_id=readme-demo&governorate_code=TN-71" -F "fichier=@.\data\cv_exemple.docx"
curl.exe -sS "$base/api/v1/offres"
curl.exe -sS -X POST "$base/api/v1/match?candidat_id=readme-demo"
curl.exe -sS "$base/api/v1/roadmap/readme-demo/offre-backend"
$roadmapBody = @{ candidate_id = "readme-demo"; job_offer_id = "offre-backend" } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post -Uri "$base/api/v1/roadmap" -ContentType "application/json" -Body $roadmapBody
```

Résultats observés lors de l'exécution de ces commandes : l'upload du DOCX
répond `200`, le parsing trouve 5 années d'expérience et 9 compétences, `/offres`
retourne 4 offres, `/match` répond `200` avec 4 résultats triés et des identifiants
UUID (`subject_id=3590ff66-c1d6-5aac-ba1c-d0b9b5016217`), et les routes GET et
POST de roadmap répondent `200` avec le même contenu (`target_job_offer_id`
`3f6556c5-699a-5735-9823-378a8498c081`, 3 étapes).

## Codes de compétences

`skill_codes.json` est le mapping éditable de libellés anglais, français et
arabes normalisés vers `skill_code`. WP1 fournit des exemples de codes mais pas
un catalogue de taxonomie à importer dans ce dépôt : `SK-0101` (Python) et
`SK-0103` (PHP) sont repris des tests d'intégration WP1; les autres codes
`SK-9xxx` sont des codes locaux provisoires, pas la preuve qu'ils existent dans
une base WP1 déployée.

Pour un libellé inconnu, le code est `UNMAPPED:<libellé normalisé>` (raccourci
avec un suffixe déterministe si nécessaire pour respecter la limite de 32
caractères WP1). Les gaps et étapes de roadmap suivent le schéma WP1; le texte
`label_raw` reste dans l'offre ou le profil source, car WP1 interdit ce champ
dans `SkillGapItem` et `RoadmapStep`.
