from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Governorate, Municipality


router = APIRouter(prefix="/locations", tags=["locations"])


def validate_location(
    database: Session,
    governorate_code: str | None,
    municipality_code: str | None = None,
) -> None:
    if governorate_code is None:
        return
    if database.get(Governorate, governorate_code) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid governorate.")
    if municipality_code is None:
        return
    municipality = database.get(Municipality, municipality_code)
    if municipality is None or municipality.governorate_code != governorate_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Municipality does not belong to the governorate.",
        )


@router.get("/governorates")
def list_governorates(response: Response, database: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=86400"
    rows = database.scalars(select(Governorate).order_by(Governorate.name_fr)).all()
    return [
        {
            "code": row.code,
            "name_fr": row.name_fr,
            "name_ar": row.name_ar,
            "latitude": row.latitude,
            "longitude": row.longitude,
        }
        for row in rows
    ]


@router.get("/governorates/{code}/municipalities")
def list_municipalities(code: str, response: Response, database: Session = Depends(get_session)):
    governorate = database.get(Governorate, code)
    if governorate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Governorate not found.")
    response.headers["Cache-Control"] = "public, max-age=86400"
    rows = database.scalars(
        select(Municipality)
        .where(Municipality.governorate_code == code)
        .order_by(Municipality.sort_order, Municipality.name_fr)
    ).all()
    return [
        {
            "code": row.code,
            "governorate_code": row.governorate_code,
            "name_fr": row.name_fr,
            "name_ar": row.name_ar,
            "delegation_name_fr": row.delegation_name_fr,
            "sort_order": row.sort_order,
        }
        for row in rows
    ]
