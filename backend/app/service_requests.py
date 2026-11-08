"""Authenticated service requests and eligible post-completion reviews."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.dependencies import get_current_user
from app.models import (
    EmployerNotification,
    ProfessionalProfile,
    ProfessionalProfileVisibility,
    ServiceListing,
    ServiceListingStatus,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceReview,
    User,
)
from app.schemas import (
    NotificationResponse,
    PublicServiceReviewsResponse,
    ServiceRequestCreate,
    ServiceRequestResponse,
    ServiceRequestStatusUpdate,
    ServiceReviewCreate,
    ServiceReviewResponse,
)

router = APIRouter(tags=["service requests"])


@router.get("/service-requests/notifications", response_model=list[NotificationResponse])
def service_request_notifications(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[NotificationResponse]:
    rows = session.scalars(
        select(EmployerNotification)
        .where(EmployerNotification.user_id == user.id, EmployerNotification.notification_type == "service_request")
        .order_by(EmployerNotification.created_at.desc())
        .limit(100)
    )
    return [NotificationResponse(id=item.id, notification_type=item.notification_type, title=item.title, body=item.body, resource_type=item.resource_type, resource_id=item.resource_id, read_at=item.read_at, created_at=item.created_at) for item in rows]


def _response(request: ServiceRequest, service: ServiceListing) -> ServiceRequestResponse:
    return ServiceRequestResponse(
        id=request.id,
        service_id=request.service_id,
        service_title=service.title,
        requester_user_id=request.requester_user_id,
        provider_user_id=request.provider_user_id,
        description=request.description,
        location=request.location,
        preferred_date=request.preferred_date,
        budget=request.budget,
        attachments=request.attachments,
        agreed_scope=request.agreed_scope,
        report_reason=request.report_reason,
        status=request.status.value,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _participant_request(request_id: str, user_id: str, session: Session) -> tuple[ServiceRequest, ServiceListing]:
    row = session.execute(
        select(ServiceRequest, ServiceListing)
        .join(ServiceListing, ServiceListing.id == ServiceRequest.service_id)
        .where(ServiceRequest.id == request_id)
    ).first()
    if row is None or user_id not in {row[0].requester_user_id, row[0].provider_user_id}:
        raise HTTPException(status_code=404, detail="Service request not found.")
    return row[0], row[1]


@router.post("/services/{service_id}/requests", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
def create_service_request(
    service_id: str,
    payload: ServiceRequestCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceRequestResponse:
    service = session.scalar(
        select(ServiceListing)
        .join(ProfessionalProfile, ProfessionalProfile.user_id == ServiceListing.owner_user_id)
        .where(
            ServiceListing.id == service_id,
            ServiceListing.status == ServiceListingStatus.PUBLISHED,
            ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC,
            ProfessionalProfile.accepting_requests.is_(True),
        )
    )
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found or not accepting requests.")
    if service.owner_user_id == user.id:
        raise HTTPException(status_code=409, detail="You cannot request your own service.")
    request = ServiceRequest(
        service_id=service.id,
        requester_user_id=user.id,
        provider_user_id=service.owner_user_id,
        **payload.model_dump(),
    )
    session.add(request)
    session.flush()
    session.add(EmployerNotification(
        user_id=service.owner_user_id,
        notification_type="service_request",
        title="Nouvelle demande de service",
        body="Vous avez reçu une nouvelle demande de service.",
        resource_type="service_request",
        resource_id=request.id,
    ))
    record_audit_event(session, action="service_request.created", actor=user, resource_type="service_request", resource_id=request.id)
    session.commit()
    session.refresh(request)
    return _response(request, service)


@router.get("/service-requests/me", response_model=list[ServiceRequestResponse])
def my_service_requests(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[ServiceRequestResponse]:
    rows = session.execute(
        select(ServiceRequest, ServiceListing)
        .join(ServiceListing, ServiceListing.id == ServiceRequest.service_id)
        .where((ServiceRequest.requester_user_id == user.id) | (ServiceRequest.provider_user_id == user.id))
        .order_by(ServiceRequest.created_at.desc())
    )
    return [_response(request, service) for request, service in rows]


@router.get("/service-requests/{request_id}", response_model=ServiceRequestResponse)
def get_service_request(request_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ServiceRequestResponse:
    request, service = _participant_request(request_id, user.id, session)
    return _response(request, service)


@router.patch("/service-requests/{request_id}/status", response_model=ServiceRequestResponse)
def update_service_request_status(
    request_id: str,
    payload: ServiceRequestStatusUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceRequestResponse:
    request, service = _participant_request(request_id, user.id, session)
    desired = ServiceRequestStatus(payload.status)
    provider = user.id == request.provider_user_id
    if provider:
        allowed = {
            ServiceRequestStatus.REQUESTED: {ServiceRequestStatus.ACCEPTED, ServiceRequestStatus.DECLINED, ServiceRequestStatus.CANCELLED},
            ServiceRequestStatus.ACCEPTED: {ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.CANCELLED},
            ServiceRequestStatus.IN_PROGRESS: {ServiceRequestStatus.COMPLETION_REQUESTED, ServiceRequestStatus.CANCELLED, ServiceRequestStatus.DISPUTED},
            ServiceRequestStatus.COMPLETION_REQUESTED: {ServiceRequestStatus.DISPUTED},
        }
    else:
        allowed = {
            ServiceRequestStatus.REQUESTED: {ServiceRequestStatus.CANCELLED},
            ServiceRequestStatus.ACCEPTED: {ServiceRequestStatus.CANCELLED},
            ServiceRequestStatus.IN_PROGRESS: {ServiceRequestStatus.CANCELLED, ServiceRequestStatus.DISPUTED},
            ServiceRequestStatus.COMPLETION_REQUESTED: {ServiceRequestStatus.COMPLETED, ServiceRequestStatus.DISPUTED},
        }
    if desired not in allowed.get(request.status, set()):
        raise HTTPException(status_code=409, detail=f"This service request cannot move from {request.status.value} to {desired.value}.")
    if payload.agreed_scope is not None:
        if not provider or desired not in {ServiceRequestStatus.ACCEPTED, ServiceRequestStatus.IN_PROGRESS}:
            raise HTTPException(status_code=403, detail="Only the provider can set the agreed scope while accepting or starting work.")
        request.agreed_scope = payload.agreed_scope.strip() or None
    if desired == ServiceRequestStatus.DISPUTED:
        request.report_reason = payload.report_reason.strip() if payload.report_reason else None
    request.status = desired
    request.updated_at = datetime.now(timezone.utc)
    record_audit_event(session, action="service_request.status_updated", actor=user, resource_type="service_request", resource_id=request.id, details={"to": desired.value})
    session.commit()
    session.refresh(request)
    return _response(request, service)


@router.post("/service-requests/{request_id}/review", response_model=ServiceReviewResponse, status_code=status.HTTP_201_CREATED)
def create_service_review(
    request_id: str,
    payload: ServiceReviewCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ServiceReviewResponse:
    request = session.get(ServiceRequest, request_id)
    if request is None or request.requester_user_id != user.id:
        raise HTTPException(status_code=404, detail="Completed service request not found.")
    if request.status != ServiceRequestStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="A review is only allowed after the requester confirms completion.")
    review = ServiceReview(
        service_request_id=request.id,
        reviewer_user_id=user.id,
        provider_user_id=request.provider_user_id,
        rating=payload.rating,
        comment=payload.comment.strip() if payload.comment else None,
    )
    session.add(review)
    record_audit_event(session, action="service.review.created", actor=user, resource_type="service_review", resource_id=request.id)
    try:
        session.commit()
    except Exception as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="A review has already been submitted for this completed request.") from error
    session.refresh(review)
    return ServiceReviewResponse.model_validate(review)


@router.get("/professionals/{provider_user_id}/reviews", response_model=PublicServiceReviewsResponse)
def professional_service_reviews(provider_user_id: str, session: Session = Depends(get_session)) -> PublicServiceReviewsResponse:
    profile = session.scalar(select(ProfessionalProfile).where(ProfessionalProfile.user_id == provider_user_id, ProfessionalProfile.visibility == ProfessionalProfileVisibility.PUBLIC))
    if profile is None:
        raise HTTPException(status_code=404, detail="Professional profile not found.")
    rows = list(session.scalars(select(ServiceReview).where(ServiceReview.provider_user_id == provider_user_id).order_by(ServiceReview.created_at.desc())))
    average = session.scalar(select(func.avg(ServiceReview.rating)).where(ServiceReview.provider_user_id == provider_user_id))
    return PublicServiceReviewsResponse(items=[ServiceReviewResponse.model_validate(item) for item in rows], average_rating=float(average) if average is not None else None, total=len(rows))
