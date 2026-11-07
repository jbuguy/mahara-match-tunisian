"""Professional profiles, service listings, and public marketplace discovery."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.dependencies import get_current_user
from app.models import (
    ProfessionalProfile,
    ProfessionalProfileVisibility,
    ServiceListing,
    ServiceListingStatus,
    User,
)
from app.schemas import (
    ProfessionalProfileFields,
    ProfessionalProfileResponse,
    PublicProfessionalProfileResponse,
    PublicProfessionalSearchPage,
    PublicServiceListingResponse,
    PublicServiceSearchPage,
    ServiceListingCreate,
    ServiceListingResponse,
    ServiceListingStatusUpdate,
)

router = APIRouter()


def _service_response(listing: ServiceListing) -> ServiceListingResponse:
    return ServiceListingResponse.model_validate(listing)


def _public_service(listing: ServiceListing) -> PublicServiceListingResponse:
    return PublicServiceListingResponse.model_validate(listing)


def _public_profile(
    profile: ProfessionalProfile,
    services: list[ServiceListing],
) -> PublicProfessionalProfileResponse:
    return PublicProfessionalProfileResponse(
        id=profile.user_id,
        display_name=profile.display_name,
        headline=profile.headline,
        introduction=profile.introduction,
        photo_url=profile.photo_url,
        location=profile.location,
        languages=profile.languages,
        skills=profile.skills,
        years_experience=profile.years_experience,
        available=profile.available,
        accepting_requests=profile.accepting_requests,
        availability=profile.availability,
        services=[_public_service(item) for item in services],
    )


@router.get("/me/professional-profile", response_model=ProfessionalProfileResponse)
def get_my_professional_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProfessionalProfileResponse:
    profile = session.get(ProfessionalProfile, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Professional profile not found.")
    return ProfessionalProfileResponse.model_validate(profile)


@router.put("/me/professional-profile", response_model=ProfessionalProfileResponse)
def save_my_professional_profile(
    request: ProfessionalProfileFields,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProfessionalProfileResponse:
    profile = session.get(ProfessionalProfile, user.id)
    values = request.model_dump()
    if profile is None:
        profile = ProfessionalProfile(user_id=user.id, **values)
        session.add(profile)
        action = "professional.profile.created"
    else:
        for key, value in values.items():
            setattr(profile, key, value)
        action = "professional.profile.updated"
    record_audit_event(session, action=action, actor=user, resource_type="professional_profile", resource_id=user.id)
    session.commit()
    session.refresh(profile)
    return ProfessionalProfileResponse.model_validate(profile)


@router.get("/me/services", response_model=list[ServiceListingResponse])
def my_services(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ServiceListingResponse]:
    return [
        _service_response(item)
        for item in session.scalars(
            select(ServiceListing)
            .where(ServiceListing.owner_user_id == user.id)
            .order_by(ServiceListing.created_at.desc(), ServiceListing.id)
        )
    ]


@router.post("/me/services", response_model=ServiceListingResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    request: ServiceListingCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceListingResponse:
    profile = session.get(ProfessionalProfile, user.id)
    if profile is None:
        raise HTTPException(status_code=409, detail="Create a professional profile before publishing a service.")
    listing = ServiceListing(owner_user_id=user.id, **request.model_dump())
    session.add(listing)
    session.flush()
    record_audit_event(session, action="professional.service.created", actor=user, resource_type="service_listing", resource_id=listing.id)
    session.commit()
    session.refresh(listing)
    return _service_response(listing)


@router.put("/me/services/{listing_id}", response_model=ServiceListingResponse)
def update_service(
    listing_id: str,
    request: ServiceListingCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceListingResponse:
    listing = session.scalar(
        select(ServiceListing).where(
            ServiceListing.id == listing_id,
            ServiceListing.owner_user_id == user.id,
        )
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Service listing not found.")
    if listing.status == ServiceListingStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived service listings cannot be edited.")
    for key, value in request.model_dump().items():
        setattr(listing, key, value)
    listing.updated_at = datetime.now(timezone.utc)
    record_audit_event(session, action="professional.service.updated", actor=user, resource_type="service_listing", resource_id=listing.id)
    session.commit()
    session.refresh(listing)
    return _service_response(listing)


@router.patch("/me/services/{listing_id}/status", response_model=ServiceListingResponse)
def update_service_status(
    listing_id: str,
    request: ServiceListingStatusUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceListingResponse:
    listing = session.scalar(
        select(ServiceListing).where(
            ServiceListing.id == listing_id,
            ServiceListing.owner_user_id == user.id,
        )
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Service listing not found.")
    transitions = {
        ServiceListingStatus.DRAFT: {ServiceListingStatus.PUBLISHED, ServiceListingStatus.ARCHIVED},
        ServiceListingStatus.PUBLISHED: {ServiceListingStatus.PAUSED, ServiceListingStatus.ARCHIVED},
        ServiceListingStatus.PAUSED: {ServiceListingStatus.PUBLISHED, ServiceListingStatus.ARCHIVED},
        ServiceListingStatus.ARCHIVED: set(),
    }
    if request.status not in transitions[listing.status]:
        raise HTTPException(status_code=409, detail=f"Cannot change a service from {listing.status.value} to {request.status.value}.")
    if request.status == ServiceListingStatus.PUBLISHED:
        profile = session.get(ProfessionalProfile, user.id)
        if profile is None or profile.visibility != ProfessionalProfileVisibility.PUBLIC:
            raise HTTPException(status_code=409, detail="Make your professional profile public before publishing a service.")
    previous = listing.status
    listing.status = request.status
    listing.updated_at = datetime.now(timezone.utc)
    record_audit_event(session, action="professional.service.status_updated", actor=user, resource_type="service_listing", resource_id=listing.id, details={"from": previous.value, "to": request.status.value})
    session.commit()
    session.refresh(listing)
    return _service_response(listing)


@router.get("/public/services", response_model=PublicServiceSearchPage, tags=["public discovery"])
def search_public_services(
    q: str | None = Query(default=None, min_length=1, max_length=160),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    location: str | None = Query(default=None, min_length=1, max_length=120),
    service_mode: str | None = Query(default=None, min_length=1, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PublicServiceSearchPage:
    filters = [
        ServiceListing.status == ServiceListingStatus.PUBLISHED,
        ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC,
    ]
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            ServiceListing.title.ilike(pattern)
            | ServiceListing.description.ilike(pattern)
            | ServiceListing.category.ilike(pattern)
            | cast(ServiceListing.skills, String).ilike(pattern)
        )
    if category:
        filters.append(ServiceListing.category.ilike(f"%{category.strip()}%"))
    if location:
        filters.append(ServiceListing.location.ilike(f"%{location.strip()}%"))
    if service_mode:
        filters.append(ServiceListing.service_mode == service_mode)
    base_query = select(ServiceListing).join(
        ProfessionalProfile, ProfessionalProfile.user_id == ServiceListing.owner_user_id
    ).where(*filters)
    total = session.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    listings = session.scalars(
        base_query.order_by(ServiceListing.created_at.desc(), ServiceListing.id)
        .offset(offset).limit(limit)
    )


@router.get("/public/services/{listing_id}", response_model=PublicServiceListingResponse, tags=["public discovery"])
def get_public_service(
    listing_id: str,
    session: Session = Depends(get_session),
) -> PublicServiceListingResponse:
    listing = session.scalar(
        select(ServiceListing)
        .join(ProfessionalProfile, ProfessionalProfile.user_id == ServiceListing.owner_user_id)
        .where(
            ServiceListing.id == listing_id,
            ServiceListing.status == ServiceListingStatus.PUBLISHED,
            ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC,
        )
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Service listing not found.")
    return _public_service(listing)
    return PublicServiceSearchPage(
        items=[_public_service(item) for item in listings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/public/professionals", response_model=PublicProfessionalSearchPage, tags=["public discovery"])
def search_public_professionals(
    q: str | None = Query(default=None, min_length=1, max_length=160),
    location: str | None = Query(default=None, min_length=1, max_length=120),
    skill: str | None = Query(default=None, min_length=1, max_length=60),
    available: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PublicProfessionalSearchPage:
    filters = [ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC]
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            ProfessionalProfile.display_name.ilike(pattern)
            | ProfessionalProfile.headline.ilike(pattern)
            | ProfessionalProfile.introduction.ilike(pattern)
            | cast(ProfessionalProfile.skills, String).ilike(pattern)
        )
    if location:
        filters.append(ProfessionalProfile.location.ilike(f"%{location.strip()}%"))
    if skill:
        filters.append(cast(ProfessionalProfile.skills, String).ilike(f"%{skill.strip()}%"))
    if available is not None:
        filters.append(ProfessionalProfile.available.is_(available))
    base_query = select(ProfessionalProfile).where(*filters)
    total = session.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    profiles = session.scalars(
        base_query.order_by(ProfessionalProfile.updated_at.desc(), ProfessionalProfile.user_id)
        .offset(offset).limit(limit)
    )
    return PublicProfessionalSearchPage(
        items=[
            PublicProfessionalProfileResponse(
                id=item.user_id,
                display_name=item.display_name,
                headline=item.headline,
                introduction=item.introduction,
                photo_url=item.photo_url,
                location=item.location,
                languages=item.languages,
                skills=item.skills,
                years_experience=item.years_experience,
                available=item.available,
                accepting_requests=item.accepting_requests,
                availability=item.availability,
                services=[],
            )
            for item in profiles
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/public/professionals/{user_id}", response_model=PublicProfessionalProfileResponse, tags=["public discovery"])
def get_public_professional(
    user_id: str,
    session: Session = Depends(get_session),
) -> PublicProfessionalProfileResponse:
    profile = session.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.user_id == user_id,
            ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Professional profile not found.")
    services = list(
        session.scalars(
            select(ServiceListing)
            .where(
                ServiceListing.owner_user_id == user_id,
                ServiceListing.status == ServiceListingStatus.PUBLISHED,
            )
            .order_by(ServiceListing.created_at.desc(), ServiceListing.id)
        )
    )
    return _public_profile(profile, services)
