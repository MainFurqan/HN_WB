from fastapi import APIRouter
from pydantic import BaseModel
from ..services.opportunities import match as match_service

router = APIRouter()


class MatchRequest(BaseModel):
    skill_uris: list[str]
    isco_cluster: str | None = None
    country: str = "PK"


@router.post("/match")
def match(req: MatchRequest):
    return match_service(
        skill_uris=req.skill_uris,
        isco_cluster=req.isco_cluster,
        country=req.country,
    )
