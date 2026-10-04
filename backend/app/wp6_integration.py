import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from .models import Candidate


def register_wp6_routes(app: FastAPI, settings: Any, root_get_db: Any) -> Any:
    repo_root = Path(__file__).resolve().parents[2]
    wp6_app_path = repo_root / "employee-module-wp6" / "backend" / "app"
    package_name = "mahara_wp6"

    if package_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            package_name,
            wp6_app_path / "__init__.py",
            submodule_search_locations=[str(wp6_app_path)],
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load the WP6 backend package")
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        spec.loader.exec_module(package)

    config = importlib.import_module(f"{package_name}.config")
    db = importlib.import_module(f"{package_name}.db")
    auth = importlib.import_module(f"{package_name}.auth")
    health_router = importlib.import_module(f"{package_name}.routers.health").router
    me_router = importlib.import_module(f"{package_name}.routers.me").router
    profile_router = importlib.import_module(f"{package_name}.routers.profile").router
    reference_router = importlib.import_module(f"{package_name}.routers.reference").router
    cv_router = importlib.import_module(f"{package_name}.routers.cv").router
    photo_router = importlib.import_module(f"{package_name}.routers.photo").router
    assistant_router = importlib.import_module(f"{package_name}.routers.assistant").router
    profile_service = importlib.import_module(f"{package_name}.services.profile")

    def get_wp6_settings():
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
    app.dependency_overrides[auth.get_settings] = get_wp6_settings
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(me_router, prefix="/api/v1")
    app.include_router(profile_router, prefix="/api/v1")
    app.include_router(reference_router, prefix="/api/v1")
    app.include_router(cv_router, prefix="/api/v1")
    app.include_router(photo_router, prefix="/api/v1")
    app.include_router(assistant_router, prefix="/api/v1")

    def get_candidate_profile(db: Any, user_id: Any):
        candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
        if candidate is None:
            return None

        profile = profile_service.get_profile(db, user_id)
        if profile is None:
            return None
        return candidate.id, profile.model_dump(mode="json")

    return get_candidate_profile