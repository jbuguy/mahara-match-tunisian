import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_jwks_client
from app.config import get_settings
from app.db import get_engine
from app.routers import cv, health, me, photo, profile, reference

logger = logging.getLogger(__name__)
settings = get_settings()

WARM_CONNECTIONS = 3  # the pages make up to 3 requests at once


def warm_up() -> None:
    """Open a few database connections and fetch the login keys now, so the first clicks aren't slow.

    Each new connection to Supabase costs about a second; the pool keeps them for the next requests.
    """
    try:
        connections = [get_engine().connect() for _ in range(WARM_CONNECTIONS)]
        for connection in connections:
            connection.close()
        get_jwks_client().get_jwk_set()
    except Exception as exc:  # the app still works, just slower on the first requests
        logger.warning("warm-up skipped: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=warm_up, daemon=True).start()
    yield


app = FastAPI(title="Mahara WP6 Employee Module", lifespan=lifespan)

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
app.include_router(photo.router, prefix="/api/v1")
app.include_router(cv.router, prefix="/api/v1")
app.include_router(reference.router, prefix="/api/v1")
