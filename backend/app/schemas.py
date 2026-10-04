import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import CompanySize


class EmployerSignup(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    sector: str = Field(min_length=1, max_length=120)
    company_size: CompanySize

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(character.islower() for character in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(character.isupper() for character in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain a digit")
        return value


class EmployerLogin(BaseModel):
    email: EmailStr
    password: str


class EmployerUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=160)
    sector: str | None = Field(default=None, min_length=1, max_length=120)
    company_size: CompanySize | None = None


class CandidateSignup(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    preferred_language: str = "fr"
    onboarding_path: str = "cv_upload"
    governorate_code: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(character.islower() for character in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(character.isupper() for character in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain a digit")
        return value


class CandidateLogin(BaseModel):
    email: EmailStr
    password: str


class CandidateProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    onboarding_path: str
    preferred_language: str | None
    literacy_level: str | None
    governorate_code: str | None
    education_level: str | None
    years_experience: int | None
    summary: str | None
    available_from: str | None
    consent_version: str | None
    consent_given_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CandidateUpdate(BaseModel):
    onboarding_path: str | None = None
    preferred_language: str | None = None
    literacy_level: str | None = None
    governorate_code: str | None = None
    education_level: str | None = None
    years_experience: int | None = None
    summary: str | None = None
    available_from: str | None = None
    consent_version: str | None = None


class EmployerProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    email: EmailStr
    sector: str
    company_size: CompanySize
    created_at: datetime
    verified: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"