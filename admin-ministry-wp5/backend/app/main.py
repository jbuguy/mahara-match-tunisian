import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from mahara_data.schemas.common import ApiError

from .config import get_settings
from .errors import install_error_handlers
from .metrics import METRICS
from .routers import analytics,health, ingestion, market, monitoring, occupations, suggestions, taxonomy
settings = get_settings()

TAGS = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {
        "name": "admin-taxonomy",
        "description": "Governance of the national skills referential: create, edit, "
        "validate and retire entries. Nothing enters circulation without validation.",
    },
    {
        "name": "admin-suggestions",
        "description": "Review inbox. Unknown labels found by the WP2 and WP4 pipelines "
        "wait here for one of three verdicts: approve, merge as a synonym, or reject.",
    },
    {
        "name": "admin-occupations",
        "description": "Occupation referential, aligned with ISCO-08, and the required "
        "skills that feed WP3's gap detection.",
    },
    {
        "name": "admin-monitoring",
        "description": "Technical health and referential quality indicators.",
    },
        {
        "name": "admin-market",
        "description": "Ministry data exchange: deposits of labour-market datasets "
        "(official, informal or study) and their ingestion reports.",
    },
        {
        "name": "admin-ingestion",
        "description": "Ingestion runs: volumes, rejected rows and the pipeline version "
        "that produced each result.",
    },
        {
        "name": "admin-analytics",
        "description": "Skill-gap cartography for the ministry, aggregated under a "
        "k-anonymity threshold of 10.",
    },
]

COMMON_ERRORS = {
    404: {"model": ApiError, "description": "The resource does not exist"},
    409: {"model": ApiError, "description": "Conflicts with the current state"},
    422: {"model": ApiError, "description": "The payload does not match the contract"},
}

app = FastAPI(
    title="Mahara Match - WP5 Admin & Ministry API",
    version="0.1.0",
    description=(
        "WP5 owns the governance of the shared referential: skills, occupations, and the "
        "review of labels proposed by the ingestion pipelines. Entities and schemas come "
        "from WP1's `mahara_data` package; WP5 owns the lifecycle, not the model.\n\n"
        "Every error follows WP1's `ApiError` contract."
    ),
    openapi_tags=TAGS,
)

install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _route_label(request: Request) -> str:
    """The matched route template, so ids never become separate counters."""
    route = request.scope.get("route")
    return f"{request.method} {getattr(route, 'path', request.url.path)}"


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # A crash is still traffic, and the one worth seeing on the dashboard.
        METRICS.record(_route_label(request), 500, (time.perf_counter() - start) * 1000)
        raise
    METRICS.record(_route_label(request), response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """An API has no homepage, but a human landing here wants the documentation."""
    return RedirectResponse(url="/docs")


app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(taxonomy.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)
app.include_router(suggestions.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)
app.include_router(occupations.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)
app.include_router(monitoring.router, prefix=settings.api_prefix)
app.include_router(market.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)
app.include_router(ingestion.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)
app.include_router(analytics.router, prefix=settings.api_prefix, responses=COMMON_ERRORS)