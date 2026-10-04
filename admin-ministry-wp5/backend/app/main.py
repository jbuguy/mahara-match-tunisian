import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .metrics import METRICS
from .routers import health, monitoring, occupations, suggestions, taxonomy

settings = get_settings()

app = FastAPI(
    title="Mahara Match - WP5 Admin & Ministry API",
    version="0.1.0",
)

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


app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(taxonomy.router, prefix=settings.api_prefix)
app.include_router(suggestions.router, prefix=settings.api_prefix)
app.include_router(occupations.router, prefix=settings.api_prefix)
app.include_router(monitoring.router, prefix=settings.api_prefix)