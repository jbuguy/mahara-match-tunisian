from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, me, profile, reference

settings = get_settings()

app = FastAPI(title="Mahara WP6 Employee Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(reference.router, prefix="/api/v1")
