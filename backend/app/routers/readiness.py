from fastapi import APIRouter
from pydantic import BaseModel
from ..services.readiness import assess as assess_service

router = APIRouter()


class ReadinessRequest(BaseModel):
    skill_uris: list[str]
    isco_cluster: str | None = None
    country: str = "PK"


@router.post("/")
def assess(req: ReadinessRequest):
    return assess_service(
        skill_uris=req.skill_uris,
        isco_cluster=req.isco_cluster,
        country=req.country,
    )
