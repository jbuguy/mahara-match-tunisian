from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import health,suggestions,taxonomy

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

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(taxonomy.router, prefix=settings.api_prefix)
app.include_router(suggestions.router, prefix=settings.api_prefix)