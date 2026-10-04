import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared_llm import LLMSettings, OpenAICompatibleClient

from .config import get_settings
from .database import Base, engine, get_db
from .google_auth import router as google_auth_router
from .wp2_integration import create_wp2_router
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
from .wp6_integration import register_wp6_routes

from employer_agent_wp4 import create_employer_agent_router


settings = get_settings()
llm_client = OpenAICompatibleClient(
    LLMSettings(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    create_employer_agent_router(
        get_db,
        get_current_employer,
        EmployerDraftSession,
        llm_client=llm_client,
    )
)
app.include_router(google_auth_router)
app.include_router(create_wp2_router(get_db, get_current_user))
register_wp6_routes(app, settings, get_db)


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
            "source": "wp1",
            "version": "latest",
            "contracts": contract_names,
        }
    except Exception:
        return {"source": "wp1", "version": "unavailable", "contracts": []}


def detect_module_status(module_code: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    module_paths = {
        "wp1": repo_root / "data-layer-wp1",
        "wp4": repo_root / "employer-agent-wp4",
        "wp2": repo_root / "onboarding-agent-wp2",
        "wp6": repo_root / "employee-module-wp6",
    }
    module_path = module_paths.get(module_code)
    if module_path and module_path.exists():
        return "registered"
    return "not_configured"


def build_module_registry() -> list[dict[str, object]]:
    shared_status = "ok" if check_shared_contracts() == "ok" else "not_configured"
    wp1_contracts = build_contract_catalog().get("contracts", [])
    return [
        {
            "code": "wp1",
            "name": "Data layer",
            "owner": "platform",
            "description": "Canonical PostgreSQL schema and shared JSON contracts",
            "status": detect_module_status("wp1"),
            "shared_contracts": shared_status,
            "contracts": wp1_contracts,
            "contract_count": len(wp1_contracts),
        },
        {
            "code": "wp2",
            "name": "Candidate onboarding",
            "owner": "platform",
            "description": "Guided voice intake and candidate profile draft",
            "status": detect_module_status("wp2"),
            "shared_contracts": shared_status,
            "contracts": wp1_contracts,
            "contract_count": len(wp1_contracts),
        },
        {
            "code": "wp4",
            "name": "Employer module",
            "owner": "platform",
            "description": "Employer onboarding, job posting, and hiring workflows",
            "status": detect_module_status("wp4"),
            "shared_contracts": shared_status,
            "contracts": wp1_contracts,
            "contract_count": len(wp1_contracts),
        },
        {
            "code": "wp6",
            "name": "Employee module",
            "owner": "platform",
            "description": "Candidate profile, applications, and roadmap journey",
            "status": detect_module_status("wp6"),
            "shared_contracts": shared_status,
            "contracts": wp1_contracts,
            "contract_count": len(wp1_contracts),
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


@app.post("/platform/integrations/wp4/validate-offer")
def validate_wp4_offer(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.offer import NormalizedJobOffer
    from pydantic import ValidationError

    try:
        offer = NormalizedJobOffer.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "job_offer", "error": str(exc)}) from exc

    return {
        "module": "wp4",
        "contract": "job_offer",
        "source": "wp1",
        "valid": True,
        "status": "validated",
        "offer": offer.model_dump(mode="json"),
    }


@app.post("/platform/integrations/wp6/validate-profile")
def validate_wp6_profile(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.profile import CandidateProfile
    from pydantic import ValidationError

    try:
        profile = CandidateProfile.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "candidate_profile", "error": str(exc)}) from exc

    return {
        "module": "wp6",
        "contract": "candidate_profile",
        "source": "wp1",
        "valid": True,
        "status": "validated",
        "profile": profile.model_dump(mode="json"),
    }


@app.post("/platform/integrations/wp2/onboard")
def validate_wp2_onboarding(payload: dict[str, Any]) -> dict[str, object]:
    from mahara_data.schemas.profile import CandidateProfile
    from pydantic import ValidationError

    try:
        profile = CandidateProfile.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"contract": "candidate_profile", "error": str(exc)}) from exc

    return {
        "module": "wp2",
        "contract": "candidate_profile",
        "source": "wp1",
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
    candidate.preferred_language = (payload.preferred_language or "fr").strip() or "fr"
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