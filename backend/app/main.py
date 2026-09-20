from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import Employer
from .schemas import EmployerLogin, EmployerProfile, EmployerSignup, EmployerUpdate, Token
from .security import create_access_token, get_current_employer, hash_password, verify_password


app = FastAPI(title="Mahara Match Employer API", version="0.1.0")


@app.post("/employers/signup", response_model=EmployerProfile, status_code=status.HTTP_201_CREATED)
def signup(payload: EmployerSignup, db: Annotated[Session, Depends(get_db)]) -> Employer:
    email = payload.email.lower()
    employer = Employer(
        company_name=payload.company_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
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