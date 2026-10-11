from typing import Any

from fastapi import FastAPI
from mahara_data.db.models.candidates import Candidate

from . import auth, config, db
from .routers import assistant, cv, health, me, photo, profile, reference
from .services import profile as profile_service


def register_employee_routes(app: FastAPI, settings: Any, root_get_db: Any) -> Any:
    def get_employee_settings():
        return config.Settings(
            database_url=settings.database_url,
            google_client_id=settings.google_client_id,
            google_client_secret=settings.google_client_secret,
            jwt_secret=settings.jwt_secret,
            api_base_url=settings.api_base_url,
            frontend_url=settings.frontend_url,
            cors_origins=",".join(settings.cors_origin_list),
            app_env=settings.app_env,
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
        )

    app.dependency_overrides[db.get_db] = root_get_db
    app.dependency_overrides[auth.get_settings] = get_employee_settings
    for router in (health.router, me.router, profile.router, reference.router, cv.router, photo.router, assistant.router):
        app.include_router(router, prefix="/api/v1")

    def get_candidate_profile(session: Any, user_id: Any):
        candidate = session.query(Candidate).filter(Candidate.user_id == user_id).first()
        if candidate is None:
            return None
        profile_data = profile_service.get_profile(session, user_id)
        return (candidate.id, profile_data.model_dump(mode="json")) if profile_data else None

    return get_candidate_profile

