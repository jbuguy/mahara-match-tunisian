# WP3 - Skill Matching Engine

Module de la Plateforme Intelligente d'Emploi (Tunisie) qui calcule la pertinence
entre un profil candidat et des offres d'emploi, détecte les compétences manquantes
(gaps) et génère une roadmap de formation.

**Responsables :** Siwar (1ère), Shayma (2ème)

## Rôle dans l'architecture

| | Détail |
|---|---|
| **Consomme** | WP2 (profils candidats JSON), WP1 (offres, taxonomie, formats) |
| **Alimente** | WP4 (candidats scorés), WP6 (offres triées et roadmaps) |
| **Contrats de données** | `data-layer-wp1/contracts/` (voir `MatchResult`, `RankedMatches`, `Roadmap`) |

## Structure

```
skill-matching-wp3/
├── main.py            # API FastAPI (endpoints)
├── cv_parser.py       # Lecture d'un CV (PDF/DOCX) -> dictionnaire brut
├── cv_adapter.py      # Brut -> profil au format du contrat WP1 (sans PII)
├── scoring.py         # Scores, gaps, classement, roadmap
├── test_adapter.py    # Vérifie parser + adaptateur + contrat WP1
├── test_scoring.py    # Vérifie scoring + contrat WP1
├── data/              # CV d'exemple (cv_exemple.docx)
└── requirements.txt
```

## Installation

Depuis le dossier `skill-matching-wp3` :

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ..\data-layer-wp1     # contrats WP1 (nécessaire pour les tests)
```

## Lancer l'API

```powershell
python main.py
```

Documentation interactive : http://localhost:8000/docs

## Endpoints

| Méthode | URL | Entrée | Sortie |
|---|---|---|---|
| GET | `/` | - | message de santé |
| POST | `/api/v1/parse-cv` | fichier `.pdf`/`.docx`, `candidat_id`, `governorate_code` (optionnel) | profil au format WP1 |
| POST | `/api/v1/match` | `{ "profil": {...}, "offres": [...] }` | offres classées, scores, gaps |
| POST | `/api/v1/roadmap` | `{ "profil": {...}, "offre": {...} }` | roadmap de formation |

Note : pour l'instant, les offres sont envoyées dans la requête. Elles viendront de
la base de données WP1 quand elle sera disponible.

## Formule de scoring

```
score_global = 0.50 x hard_skills
             + 0.20 x experience
             + 0.15 x soft_skills
             + 0.15 x localisation
```

Chaque critère est noté sur 100 :

- **Hard skills / soft skills** : pour chaque compétence de l'offre,
  `crédit = min(niveau_candidat / niveau_requis, 1)`. Moyenne pondérée : compétence
  obligatoire = poids 1, facultative = poids 0.5. Une compétence absente vaut 0.
  Si l'offre ne demande aucune compétence de la catégorie, le score est 100.
- **Expérience** : `min(années_candidat / années_requises, 1) x 100` (100 si aucune exigence).
- **Localisation** : 100 si même gouvernorat, 70 si le gouvernorat de l'offre est dans
  la mobilité du candidat, 0 sinon, 50 si l'information manque.

### Exemple

Profil : Python 2, Django 2, SQL 2, 5 ans d'expérience, TN-71.
Offre : Python 3 (oblig.), Django 3 (oblig.), SQL 2 (oblig.), Kubernetes 2 (facult.), 3 ans, TN-71.

```
hard_skills = (0.67 + 0.67 + 1 + 0) / 3.5 = 66.7
experience  = 100   |   soft_skills = 100   |   localisation = 100
score_global = 0.5x66.7 + 0.2x100 + 0.15x100 + 0.15x100 = 83.3
```

## Gaps et roadmap

- **Gap `missing`** : compétence de l'offre absente du profil.
- **Gap `insufficient_level`** : compétence présente mais niveau inférieur au niveau requis.
- **Roadmap** : un pas par gap, numérotés de 1 à n ; obligatoires d'abord, puis
  manquantes avant niveau insuffisant.

## Comparaison des compétences

Une compétence est identifiée par son `skill_code` (taxonomie WP1) si elle en a un,
sinon par son `label_raw` normalisé (minuscules, sans accents).

## Tests

Avec le venv activé :

```powershell
python test_adapter.py    # CV -> profil -> validation par CandidateProfile (WP1)
python test_scoring.py    # scoring -> validation par MatchResult, RankedMatches, Roadmap
```

Les tests ne sont pas utilisés par l'API : ils servent à vérifier que le module
respecte les contrats du WP1.

## Limites actuelles

- Taxonomie WP1 non disponible : les compétences du CV n'ont pas de `skill_code`
  (elles sont envoyées avec `label_raw`).
- Niveau de compétence par défaut = 2 et confiance = 0.6 (un CV ne donne pas le niveau).
- Pas de catalogue de formations : les étapes de roadmap n'ont pas de `training_course_id`.
- Pas de recherche sémantique : "JS" et "JavaScript" ne sont pas rapprochés.
- Le parser reconnaît les sections d'un CV par leurs titres (voir `TITRES_SECTIONS`
  dans `cv_parser.py`).

## Prochaines étapes

- [ ] Embeddings et recherche sémantique (dimension 768, RAG) - SCRUM-36, SCRUM-37
- [ ] Brancher la taxonomie WP1 (`skill_code`) dans l'adaptateur
- [ ] Brancher le catalogue de formations dans la roadmap
- [ ] Récupérer les offres depuis la base WP1
- [ ] Neutralisation des biais (genre, âge, origine) dans le scoring