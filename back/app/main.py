import importlib
import importlib.util
import time
from contextlib import asynccontextmanager
from typing import Any, Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared_llm import LLMSettings, OpenAICompatibleClient

from .applications import create_application_router
from .offers import create_offer_router
from .config import get_settings
from .database import get_db
from .google_auth import router as google_auth_router
from .features.onboarding.router import create_onboarding_router
from .features.matching.router import create_matching_router
from .features.employer.voice import create_employer_voice_router
from .features.ministry.routers import analytics as ministry_analytics
from .features.ministry.routers import ingestion as ministry_ingestion
from .features.ministry.routers import market as ministry_market
from .features.ministry.routers import monitoring as ministry_monitoring
from .features.ministry.routers import occupations as ministry_occupations
from .features.ministry.routers import suggestions as ministry_suggestions
from .features.ministry.routers import taxonomy as ministry_taxonomy
from .features.ministry.metrics import METRICS as MINISTRY_METRICS
from .models import (
    AuthIdentity,
    AuthProvider,
    Candidate,
    Employer,
    EmployerDraftSession,
    User,
    ensure_user_has_role,
    get_or_create_candidate_for_user,
    get_or_create_user,
)
from .schemas import (
    CandidateLogin,
    CandidateProfile,
    CandidateSignup,
    CandidateUpdate,
    EmployerLogin,
    EmployerProfile,
    EmployerSignup,
    EmployerUpdate,
    Token,
)
from .security import (
    create_access_token,
    create_user_access_token,
    get_current_employer,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from .features.employee.integration import register_employee_routes

from app.features.employer import create_employer_agent_router


settings = get_settings()
llm_client = OpenAICompatibleClient(
    LLMSettings(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        embedding_model=settings.llm_embedding_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await llm_client.close()


app = FastAPI(
    title="Mahara Match Platform API",
    version=settings.app_version,
    description="Production-oriented API shell for Mahara Match, with module-specific services behind a single platform surface.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?"
        if settings.app_env == "development"
        else None
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_platform_request_metrics(request: Request, call_next):
    started = time.perf_counter()
    route = request.scope.get("route")
    label = f"{request.method} {getattr(route, 'path', request.url.path)}"
    try:
        response = await call_next(request)
    except Exception:
        MINISTRY_METRICS.record(label, 500, (time.perf_counter() - started) * 1000)
        raise
    MINISTRY_METRICS.record(label, response.status_code, (time.perf_counter() - started) * 1000)
    return response
app.include_router(
    create_employer_agent_router(
        get_db,
        get_current_employer,
        EmployerDraftSession,
        llm_client=llm_client,
    )
)
app.include_router(google_auth_router)
# The existing OAuth client starts its flow under /api/v1; retain that route while
# the platform's canonical callback remains /auth/google/callback.
app.include_router(google_auth_router, prefix="/api/v1", include_in_schema=False)
app.include_router(create_application_router(get_db, get_current_user, get_current_employer))
app.include_router(create_offer_router(get_db, get_current_user))
app.include_router(create_onboarding_router(get_db, get_current_user))
read_candidate_profile = register_employee_routes(app, settings, get_db)
app.include_router(create_employer_voice_router())
app.include_router(create_matching_router(get_db, get_current_user, read_candidate_profile, llm_client=llm_client))
for ministry_router in (
    ministry_taxonomy.router,
    ministry_suggestions.router,
    ministry_occupations.router,
    ministry_market.router,
    ministry_ingestion.router,
    ministry_analytics.router,
    ministry_monitoring.router,
):
    app.include_router(ministry_router, prefix="/api/v1")


def check_shared_contracts() -> str:
    required_modules = ("mahara_data", "shared_llm")
    for module_name in required_modules:
        if importlib.util.find_spec(module_name) is None:
            return "error"
    return "ok"


def build_contract_catalog() -> dict[str, object]:
    try:
        from mahara_data.schemas import PUBLISHED_CONTRACTS

        contract_names = list(PUBLISHED_CONTRACTS.keys())
        return {
            "source": "shared",
            "version": "latest",
            "contracts": contract_names,
        }
    except Exception:
        return {"source": "shared", "version": "unavailable", "contracts": []}


def detect_module_status(module_code: str) -> str:
    return "registered" if module_code in {"data", "onboarding", "matching", "employer", "employee", "ministry"} else "not_configured"


def build_module_registry() -> list[dict[str, object]]:
    shared_status = "ok" if check_shared_contracts() == "ok" else "not_configured"
    shared_contracts_list = build_contract_catalog().get("contracts", [])
    return [
        {
            "code": "data",
            "name": "Data layer",
            "owner": "platform",
            "description": "Canonical PostgreSQL schema and shared JSON contracts",
            "status": detect_module_status("data"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
        {
            "code": "onboarding",
            "name": "Candidate onboarding",
            "owner": "platform",
            "description": "Guided voice intake and candidate profile draft",
            "status": detect_module_status("onboarding"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
        {
            "code": "matching",
            "name": "Skill matching",
            "owner": "platform",
            "description": "Candidate-to-offer ranking and skill-gap roadmaps",
            "status": detect_module_status("matching"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
        {
            "code": "employer",
            "name": "Employer module",
            "owner": "platform",
            "description": "Employer onboarding, job posting, and hiring workflows",
            "status": detect_module_status("employer"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
        {
            "code": "employee",
            "name": "Employee module",
            "owner": "platform",
            "description": "Candidate profile, applications, and roadmap journey",
            "status": detect_module_status("employee"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
        {
            "code": "ministry",
            "name": "Admin & Ministry",
            "owner": "platform",
            "description": "Governance of skills, occupations, market data and ministry analytics",
            "status": detect_module_status("ministry"),
            "shared_contracts": shared_status,
            "contracts": shared_contracts_list,
            "contract_count": len(shared_contracts_list),
        },
    ]


@app.get("/health")
def get_health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "version": settings.app_version,
    }


@app.get("/api/v1/me/roles")
def get_my_roles(current: Annotated[User, Depends(get_current_user)]) -> dict[str, list[str]]:
    """Expose the signed-in user's effective platform roles for role-aware navigation."""
    return {"roles": sorted({str(role).strip().lower() for role in current.roles})}


@app.get("/ready")
def get_readiness(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "error"

    shared_contracts_status = check_shared_contracts()
    status_value = "ready" if database_status == "ok" and shared_contracts_status == "ok" else "degraded"
    return {
        "status": status_value,
        "service": settings.app_name,
        "checks": {
            "database": database_status,
            "shared_contracts": shared_contracts_status,
        },
    }


@app.get("/platform/modules")
def get_platform_modules() -> dict[str, object]:
    return {
        "platform": settings.app_name,
        "environment": settings.environment,
        "modules": build_module_registry(),
    }


@app.get("/platform/contracts")
def get_platform_contracts() -> dict[str, object]:
    return build_contract_catalog()


@app.post("/platform/contracts/job-offer/validate")
def validate_job_offer_contract(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.offer import NormalizedJobOffer
    from pydantic import ValidationError

    try:
        offer = NormalizedJobOffer.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "job_offer", "error": str(exc)}) from exc

    return {
        "module": "employer",
        "contract": "job_offer",
        "source": "shared",
        "valid": True,
        "status": "validated",
        "offer": offer.model_dump(mode="json"),
    }


@app.post("/platform/contracts/candidate-profile/validate")
def validate_candidate_profile_contract(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.profile import CandidateProfile
    from pydantic import ValidationError

    try:
        profile = CandidateProfile.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "candidate_profile", "error": str(exc)}) from exc

    return {
        "module": "employee",
        "contract": "candidate_profile",
        "source": "shared",
        "valid": True,
        "status": "validated",
        "profile": profile.model_dump(mode="json"),
    }


@app.post("/platform/contracts/onboarding/validate")
def validate_onboarding_profile_contract(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.profile import CandidateProfile
    from pydantic import ValidationError

    try:
        profile = CandidateProfile.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "candidate_profile", "error": str(exc)}) from exc

    return {
        "module": "onboarding",
        "contract": "candidate_profile",
        "source": "shared",
        "valid": True,
        "status": "validated",
        "profile": profile.model_dump(mode="json"),
    }


@app.post("/employers/signup", response_model=EmployerProfile, status_code=status.HTTP_201_CREATED)
def signup(payload: EmployerSignup, db: Annotated[Session, Depends(get_db)]) -> Employer:
    email = payload.email.lower()
    user = get_or_create_user(db, email, roles=["employer"], email_verified=False)
    password_hash = hash_password(payload.password)
    AuthIdentity.link_user(
        db,
        user,
        provider=AuthProvider.PASSWORD,
        provider_user_id=f"email:{email}",
        email=email,
        email_verified=False,
        password_hash=password_hash,
    )

    employer = Employer(
        user_id=user.id,
        company_name=payload.company_name.strip(),
        email=email,
        password_hash=password_hash,
        sector=payload.sector.strip(),
        company_size=payload.company_size,
        verified=False,
    )
    db.add(employer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An employer with this email already exists") from None
    db.refresh(employer)
    return employer


@app.post("/employers/login", response_model=Token)
def login(payload: EmployerLogin, db: Annotated[Session, Depends(get_db)]) -> Token:
    employer = db.query(Employer).filter(Employer.email == payload.email.lower()).first()
    if employer is None or not verify_password(payload.password, employer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return Token(access_token=create_access_token(employer.id))


@app.post("/candidates/signup", response_model=CandidateProfile, status_code=status.HTTP_201_CREATED)
def candidate_signup(payload: CandidateSignup, db: Annotated[Session, Depends(get_db)]) -> Candidate:
    email = payload.email.lower()
    user = get_or_create_user(db, email, roles=["candidate"], email_verified=False)
    password_hash = hash_password(payload.password)
    AuthIdentity.link_user(
        db,
        user,
        provider=AuthProvider.PASSWORD,
        provider_user_id=f"email:{email}",
        email=email,
        email_verified=False,
        password_hash=password_hash,
    )

    candidate = get_or_create_candidate_for_user(db, user, onboarding_path=payload.onboarding_path or "cv_upload")
    user.preferred_language = (payload.preferred_language or "fr").strip() or "fr"
    candidate.governorate_code = payload.governorate_code.strip() if payload.governorate_code else None
    db.commit()
    db.refresh(candidate)
    return candidate


@app.post("/candidates/login", response_model=Token)
def candidate_login(payload: CandidateLogin, db: Annotated[Session, Depends(get_db)]) -> Token:
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    identity = (
        db.query(AuthIdentity)
        .filter(AuthIdentity.user_id == user.id, AuthIdentity.provider == AuthProvider.PASSWORD)
        .first()
    )
    if identity is None or identity.password_hash is None or not verify_password(payload.password, identity.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return Token(access_token=create_user_access_token(user))


@app.get("/candidates/me", response_model=CandidateProfile)
def get_candidate_profile(current: Annotated[User, Depends(require_roles("candidate"))], db: Annotated[Session, Depends(get_db)]) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.user_id == current.id).first()
    if candidate is None:
        candidate = get_or_create_candidate_for_user(db, current)
    return candidate


@app.patch("/candidates/me", response_model=CandidateProfile)
def update_candidate_profile(
    payload: CandidateUpdate,
    current: Annotated[User, Depends(require_roles("candidate"))],
    db: Annotated[Session, Depends(get_db)],
) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.user_id == current.id).first()
    if candidate is None:
        candidate = get_or_create_candidate_for_user(db, current)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(candidate)
    return candidate


@app.get("/employers/me", response_model=EmployerProfile)
def get_profile(current: Annotated[Employer, Depends(get_current_employer)]) -> Employer:
    return current


@app.patch("/employers/me", response_model=EmployerProfile)
def update_profile(
    payload: EmployerUpdate,
    current: Annotated[Employer, Depends(get_current_employer)],
    db: Annotated[Session, Depends(get_db)],
) -> Employer:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(current)
    return current
