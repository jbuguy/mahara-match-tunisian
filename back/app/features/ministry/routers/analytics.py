from datetime import date, timedelta
import csv
from io import BytesIO, StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ....database import get_db
from ....models import User
from ....security import require_roles
from mahara_data.db.models.platform import AuditLog
from ..schemas import LabourMarketOverview, SkillGapMap
from ..services import analytics as service

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_roles("ministry_admin"))],
)


def _safe_csv_cell(value):
    """Prevent text cells from being interpreted as spreadsheet formulas."""
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@", "\t", "\r"}:
        return "'" + value
    return value


@router.get("/skill-gaps", response_model=SkillGapMap)
def skill_gaps(
    db: Annotated[Session, Depends(get_db)],
    period_start: date | None = None,
    period_end: date | None = None,
    governorate_code: Annotated[str | None, Query(max_length=8)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> SkillGapMap:
    """Skill-gap cartography served to the ministry. The k threshold always applies."""
    end = period_end or date.today()
    start = period_start or end - timedelta(days=365)

    cells, suppressed = service.skill_gap_map(
        db,
        period_start=start,
        period_end=end,
        governorate_code=governorate_code,
        limit=limit,
    )
    return SkillGapMap(
        period_start=start,
        period_end=end,
        k_anonymity=service.K_ANONYMITY,
        cells_suppressed=suppressed,
        cells=cells,
    )


@router.get("/labour-market", response_model=LabourMarketOverview)
def labour_market(
    db: Annotated[Session, Depends(get_db)],
    period_start: date | None = None,
    period_end: date | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> LabourMarketOverview:
    """Published job demand and privacy-protected jobseeker supply aggregates."""
    end = period_end or date.today()
    start = period_start or end - timedelta(days=90)
    if start > end:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="period_start must be on or before period_end")
    governorates, occupations, suppressed, previous_start, previous_end = service.labour_market_overview(
        db, period_start=start, period_end=end, limit=limit
    )
    return LabourMarketOverview(
        period_start=start,
        period_end=end,
        comparison_period_start=previous_start,
        comparison_period_end=previous_end,
        definition_version=service.TENSION_DEFINITION_VERSION,
        k_anonymity=service.K_ANONYMITY,
        cells_suppressed=suppressed,
        demand_by_governorate=governorates,
        occupations_under_tension=occupations,
    )


@router.get("/labour-market/export.csv", include_in_schema=True)
def export_labour_market_csv(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
    period_start: date | None = None,
    period_end: date | None = None,
) -> StreamingResponse:
    """Export only the same aggregate and k-protected cells shown by the API."""
    end = period_end or date.today()
    start = period_start or end - timedelta(days=90)
    if start > end:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="period_start must be on or before period_end")
    governorates, occupations, suppressed, previous_start, previous_end = service.labour_market_overview(
        db, period_start=start, period_end=end, limit=20
    )
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["period_start", "period_end", "comparison_period_start", "comparison_period_end", "definition_version", "cells_suppressed", "row_type", "code", "name", "governorate_code", "demand_positions", "published_offers", "candidate_supply", "demand_supply_ratio", "demand_change_percent"])
    for item in governorates:
        writer.writerow([_safe_csv_cell(value) for value in [start, end, previous_start, previous_end, service.TENSION_DEFINITION_VERSION, suppressed, "governorate", item.governorate_code, item.governorate_name, item.governorate_code, item.demand_positions, item.published_offers, "", "", ""]])
    for item in occupations:
        writer.writerow([_safe_csv_cell(value) for value in [start, end, previous_start, previous_end, service.TENSION_DEFINITION_VERSION, suppressed, "occupation", item.occupation_code, item.occupation_title, item.governorate_code or "", item.demand_positions, item.published_offers, item.candidate_supply, item.demand_supply_ratio, item.demand_change_percent]])
    db.add(AuditLog(
        actor_user_id=admin.id,
        action="ministry.labour_market_exported",
        entity_type="labour_market_report",
        entity_id=f"{start}:{end}",
        payload={"format": "csv", "cells_suppressed": suppressed, "definition_version": service.TENSION_DEFINITION_VERSION},
    ))
    db.commit()
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="mahara-labour-market-{start}-{end}.csv"'},
    )


@router.get("/labour-market/export.pdf")
def export_labour_market_pdf(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_roles("ministry_admin"))],
    period_start: date | None = None,
    period_end: date | None = None,
):
    """PDF report rendered from the same privacy-protected aggregates as the API."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from fastapi import HTTPException

    end = period_end or date.today()
    start = period_start or end - timedelta(days=90)
    if start > end:
        raise HTTPException(status_code=422, detail="period_start must be on or before period_end")
    governorates, occupations, suppressed, previous_start, previous_end = service.labour_market_overview(
        db, period_start=start, period_end=end, limit=100
    )
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Mahara Match — Regional labour-market report", styles["Title"]),
        Paragraph(f"Period: {start} to {end} · Comparison: {previous_start} to {previous_end}", styles["Normal"]),
        Paragraph(f"Definition: {service.TENSION_DEFINITION_VERSION} · Privacy threshold k={service.K_ANONYMITY} · Suppressed cells: {suppressed}", styles["Normal"]),
        Spacer(1, 7 * mm),
        Paragraph("Demand by governorate", styles["Heading2"]),
    ]
    governorate_rows = [["Governorate", "Demand positions", "Published offers"]]
    governorate_rows.extend([[item.governorate_name, str(item.demand_positions), str(item.published_offers)] for item in governorates])
    tension_rows = [["Occupation", "Governorate", "Positions", "Supply", "Ratio", "Change"]]
    tension_rows.extend([
        [item.occupation_title, item.governorate_name, str(item.demand_positions), str(item.candidate_supply),
         f"{item.demand_supply_ratio:.3f}", f"{item.demand_change_percent:.1f}%" if item.demand_change_percent is not None else "—"]
        for item in occupations
    ])
    governorate_table = Table(governorate_rows, repeatRows=1, hAlign="LEFT")
    tension_table = Table(tension_rows, repeatRows=1, hAlign="LEFT")
    story.extend([governorate_table, Spacer(1, 5 * mm),
                  Paragraph("Occupations under tension", styles["Heading2"]), tension_table])
    for table in (governorate_table, tension_table):
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#164B3B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5CE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F2")]),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm)
    document.build(story)
    db.add(AuditLog(actor_user_id=admin.id, action="ministry.labour_market_exported",
        entity_type="labour_market_report", entity_id=f"{start}:{end}",
        payload={"format": "pdf", "cells_suppressed": suppressed,
                 "definition_version": service.TENSION_DEFINITION_VERSION}))
    db.commit()
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="mahara-labour-market-{start}-{end}.pdf"'})
