WP3 - Skill Matching Engine API
 0.1.0 
OAS 3.1
/openapi.json
CV → profil au format WP1 → offres → matching → roadmap.

1 · Parser le CV (format WP1)


POST
/api/v1/parse-cv
Parser Cv


CV (PDF ou DOCX) -> profil au format WP1, sans donnees personnelles.

Parameters
Cancel
Reset
Name	Description
candidat_id *
string
(query)
demo
governorate_code
string | (string | null)
(query)
emo
Request body

multipart/form-data
fichier *
string
cv_exemple.docx
Execute
Clear
Responses
Curl

curl -X 'POST' \
  'http://localhost:8000/api/v1/parse-cv?candidat_id=demo&governorate_code=emo' \
  -H 'accept: */*' \
  -H 'Content-Type: multipart/form-data' \
  -F 'fichier=@cv_exemple.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document'
Request URL
http://localhost:8000/api/v1/parse-cv?candidat_id=demo&governorate_code=emo
Server response
Code	Details
200	
Response body
Download
{
  "status": "success",
  "candidat_id": "demo",
  "profil": {
    "schema_version": "1.0",
    "candidate_id": null,
    "onboarding_path": "cv_upload",
    "literacy_level": "literate",
    "preferred_language": "fr",
    "location": {
      "governorate_code": "emo"
    },
    "mobility": {
      "radius_km": 0,
      "governorates": []
    },
    "years_experience": 5,
    "skills": [
      {
        "label_raw": "Python",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Django",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "SQL",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Docker",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "AWS",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Git",
        "skill_type": "hard",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Communication",
        "skill_type": "soft",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Autonomie",
        "skill_type": "soft",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      },
      {
        "label_raw": "Leadership",
        "skill_type": "soft",
        "level": 2,
        "source": "cv",
        "confidence": 0.6
      }
    ],
    "summary": "Developpeur backend avec 5 ans d'experience dans la conception d'applications web et le deploiement cloud. Passionne par les architectures scalables et le travail en equipe.",
    "source_document_ids": [
      "b5c4a791-d2ca-432c-93e0-bb2b27970d82"
    ]
  }
}
Response headers
 content-length: 1304 
 content-type: application/json 
 date: Wed,30 Sep 2026 20:20:09 GMT 
 server: uvicorn 
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
No links
2 · Lire les offres


GET
/api/v1/offres
Lister Offres


Lit les offres dans data/offres_exemple.json.

Parameters
Cancel
No parameters

Execute
Clear
Responses
Curl

curl -X 'GET' \
  'http://localhost:8000/api/v1/offres' \
  -H 'accept: */*'
Request URL
http://localhost:8000/api/v1/offres
Server response
Code	Details
200	
Response body
Download
[
  {
    "job_offer_id": "offre-backend",
    "min_years_experience": 3,
    "location": {
      "governorate_code": "TN-71"
    },
    "skills": [
      {
        "label_raw": "Python",
        "requirement": "required",
        "min_level": 3
      },
      {
        "label_raw": "Django",
        "requirement": "required",
        "min_level": 3
      },
      {
        "label_raw": "SQL",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "Kubernetes",
        "requirement": "preferred",
        "min_level": 2
      }
    ]
  },
  {
    "job_offer_id": "offre-devops",
    "min_years_experience": 4,
    "location": {
      "governorate_code": "TN-71"
    },
    "skills": [
      {
        "label_raw": "Docker",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "AWS",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "Git",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "Kubernetes",
        "requirement": "required",
        "min_level": 3
      }
    ]
  },
  {
    "job_offer_id": "offre-backend-tunis",
    "min_years_experience": 2,
    "location": {
      "governorate_code": "TN-11"
    },
    "skills": [
      {
        "label_raw": "Python",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "SQL",
        "requirement": "required",
        "min_level": 2
      },
      {
        "label_raw": "Communication",
        "requirement": "preferred",
        "min_level": 2
      }
    ]
  },
  {
    "job_offer_id": "offre-agricole",
    "min_years_experience": 2,
    "location": {
      "governorate_code": "TN-51"
    },
    "skills": [
      {
        "label_raw": "Irrigation",
        "requirement": "required",
        "min_level": 2
      }
    ]
  }
]
Response headers
 content-length: 1196 
 content-type: application/json 
 date: Wed,30 Sep 2026 20:20:19 GMT 
 server: uvicorn 
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
3 · Matching (scores)


POST
/api/v1/match
Match Candidat Offres


Score du candidat pour chaque offre, classe du meilleur au moins bon, avec le detail et les gaps.

Parameters
Cancel
Name	Description
candidat_id *
string
(query)
demo
Execute
Clear
Responses
Curl

curl -X 'POST' \
  'http://localhost:8000/api/v1/match?candidat_id=demo' \
  -H 'accept: */*' \
  -d ''
Request URL
http://localhost:8000/api/v1/match?candidat_id=demo
Server response
Code	Details
200	
Response body
Download
{
  "subject_id": null,
  "subject_type": "candidate",
  "items": [
    {
      "candidate_id": null,
      "job_offer_id": "offre-backend-tunis",
      "score_global": 85,
      "breakdown": {
        "hard_skills": 100,
        "experience": 100,
        "soft_skills": 100,
        "location": 0
      },
      "weights": {
        "hard_skills": 0.5,
        "experience": 0.2,
        "soft_skills": 0.15,
        "location": 0.15
      },
      "gaps": [],
      "model_version": "wp3-hybrid-0.1",
      "computed_at": "2026-09-30T20:20:36.047373+00:00"
    },
    {
      "candidate_id": null,
      "job_offer_id": "offre-devops",
      "score_global": 72.5,
      "breakdown": {
        "hard_skills": 75,
        "experience": 100,
        "soft_skills": 100,
        "location": 0
      },
      "weights": {
        "hard_skills": 0.5,
        "experience": 0.2,
        "soft_skills": 0.15,
        "location": 0.15
      },
      "gaps": [
        {
          "gap_type": "missing",
          "requirement": "required",
          "required_level": 3,
          "label_raw": "Kubernetes"
        }
      ],
      "model_version": "wp3-hybrid-0.1",
      "computed_at": "2026-09-30T20:20:36.047021+00:00"
    },
    {
      "candidate_id": null,
      "job_offer_id": "offre-backend",
      "score_global": 68.3,
      "breakdown": {
        "hard_skills": 66.7,
        "experience": 100,
        "soft_skills": 100,
        "location": 0
      },
      "weights": {
        "hard_skills": 0.5,
        "experience": 0.2,
        "soft_skills": 0.15,
        "location": 0.15
      },
      "gaps": [
        {
          "gap_type": "insufficient_level",
          "requirement": "required",
          "required_level": 3,
          "label_raw": "Python",
          "current_level": 2
        },
        {
          "gap_type": "insufficient_level",
          "requirement": "required",
          "required_level": 3,
          "label_raw": "Django",
          "current_level": 2
        },
        {
          "gap_type": "missing",
          "requirement": "preferred",
          "required_level": 2,
          "label_raw": "Kubernetes"
        }
      ],
      "model_version": "wp3-hybrid-0.1",
      "computed_at": "2026-09-30T20:20:36.046655+00:00"
    },
    {
      "candidate_id": null,
      "job_offer_id": "offre-agricole",
      "score_global": 35,
      "breakdown": {
        "hard_skills": 0,
        "experience": 100,
        "soft_skills": 100,
        "location": 0
      },
      "weights": {
        "hard_skills": 0.5,
        "experience": 0.2,
        "soft_skills": 0.15,
        "location": 0.15
      },
      "gaps": [
        {
          "gap_type": "missing",
          "requirement": "required",
          "required_level": 2,
          "label_raw": "Irrigation"
        }
      ],
      "model_version": "wp3-hybrid-0.1",
      "computed_at": "2026-09-30T20:20:36.047644+00:00"
    }
  ],
  "generated_at": "2026-09-30T20:20:36.047671+00:00"
}
Response headers
 content-length: 1956 
 content-type: application/json 
 date: Wed,30 Sep 2026 20:20:35 GMT 
 server: uvicorn 
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
No links
4 · Roadmap (compétences manquantes)


GET
/api/v1/roadmap/{candidat_id}/{offre_id}
Obtenir Roadmap


Competences a acquerir (obligatoires d'abord) pour viser cette offre.

Parameters
Cancel
Name	Description
candidat_id *
string
(path)
demo
offre_id *
string
(path)
offre-devops
Execute
Clear
Responses
Curl

curl -X 'GET' \
  'http://localhost:8000/api/v1/roadmap/demo/offre-devops' \
  -H 'accept: */*'
Request URL
http://localhost:8000/api/v1/roadmap/demo/offre-devops
Server response
Code	Details
200	
Response body
Download
{
  "candidate_id": null,
  "target_job_offer_id": "offre-devops",
  "status": "active",
  "progress_pct": 0,
  "steps": [
    {
      "position": 1,
      "status": "todo",
      "label_raw": "Kubernetes"
    }
  ],
  "model_version": "wp3-roadmap-0.1"
}
Response headers
 content-length: 193 
 content-type: application/json 
 date: Wed,30 Sep 2026 20:23:00 GMT 
 server: uvicorn 
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
No links

Schemas
Body_parser_cv_api_v1_parse_cv_postExpand allobject
HTTPValidationErrorExpand allobject
ValidationErrorExpand allobject

## Lancer le front-end

Terminal 1 (environnement virtuel Python actif, depuis `skill-matching-wp3`) :

```powershell
python main.py
```

Terminal 2 :

```powershell
cd frontend
npm install
npm run dev
```

Ouvrez ensuite http://localhost:5173.

## Lancement rapide

Depuis PowerShell, à la racine de `skill-matching-wp3`, démarrez le backend et le frontend dans deux nouvelles fenêtres avec :

```powershell
.\start.ps1
```

Arrêtez les processus lancés par ce script avec :

```powershell
.\stop.ps1
```

Si PowerShell bloque l’exécution des scripts, autorisez-les uniquement pour la session courante, puis relancez `start.ps1` :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start.ps1
```

Cette autorisation disparaît à la fermeture de la fenêtre PowerShell. Le frontend est disponible sur http://localhost:5173 et la documentation de l’API sur http://localhost:8000/docs.