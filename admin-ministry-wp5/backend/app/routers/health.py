from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])

MODULE_NAME = "wp5-admin-ministry"


class LivenessOut(BaseModel):
    status: str
    module: str


@router.get("", response_model=LivenessOut, summary="Liveness probe")
def liveness() -> LivenessOut:
    """Answers as long as the process is up. No dependency is checked here."""
    return LivenessOut(status="ok", module=MODULE_NAME)