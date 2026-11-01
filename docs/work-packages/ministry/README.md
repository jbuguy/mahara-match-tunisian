# Module « Admin & Ministère » (WP5)

Ce module gouverne le référentiel national des compétences et des métiers, arbitre
les suggestions remontées par les pipelines des autres modules, ingère les données
du marché du travail fournies par le Ministère et sert des indicateurs agrégés.

- Backend : `back/app/features/ministry/` (routeurs → services → repositories)
- Frontend : `front/src/pages/MinistryPage.tsx`
- Toutes les routes `/api/v1/admin/*` exigent le rôle `ministry_admin`.

> `openapi.json` dans ce dossier date d'avant la réorganisation. La liste réelle des
> routes est dans `back/app/features/ministry/routers/`.

## Worker d'ingestion du flux officiel

`back/app/features/ministry/worker.py` est un **processus séparé** de l'API. Il :

1. réclame un par un les traitements « actualisation officielle » mis en file par
   `POST /api/v1/admin/market/refresh` (plusieurs workers peuvent tourner en
   parallèle : la réservation utilise `FOR UPDATE SKIP LOCKED`) ;
2. télécharge le flux JSON configuré (10 Mo et 5 000 lignes au maximum) et l'ingère
   comme un dépôt de jeu de données ; en cas d'échec, le traitement passe en
   `failed` avec le motif dans son rapport (`GET /api/v1/admin/ingestion/jobs/{job_id}`) ;
3. toutes les 10 minutes, supprime les fichiers déposés dont la prévisualisation a
   expiré sans confirmation.

### Lancer le worker

Depuis le dossier `back/`, avec le même `.env` que l'API :

```bash
cd back
python -m app.features.ministry.worker
```

Le worker a besoin de `DATABASE_URL` (PostgreSQL) comme l'API, et du stockage
privé (`S3_*`) pour le nettoyage des dépôts expirés.

### Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `MINISTRY_MARKET_FEED_URL` | *(vide)* | URL absolue HTTP(S) du flux officiel. Il doit renvoyer un objet `MarketDatasetSubmission` (`dataset` + `records`) dont l'origine est `official`. HTTPS obligatoire si `ENVIRONMENT=production`. Paramètre `since` ajouté si l'actualisation en fournit un. |
| `MINISTRY_MARKET_FEED_TOKEN` | *(vide)* | Jeton facultatif, envoyé en `Authorization: Bearer <jeton>`. |
| `MINISTRY_MARKET_WORKER_POLL_SECONDS` | `3.0` | Pause du worker quand aucun traitement n'est en file. Doit être strictement positif, sinon le worker refuse de démarrer. |
| `MINISTRY_MARKET_FEED_TIMEOUT_SECONDS` | `30.0` | Délai maximal d'une requête vers le flux. |

**Sans `MINISTRY_MARKET_FEED_URL`** : l'API refuse l'actualisation
(`POST /admin/market/refresh` → 503 « Official market feed is not configured »),
donc aucun traitement n'est mis en file ; le worker démarre, journalise
« official feed disabled » et ne fait que le nettoyage des dépôts expirés.
