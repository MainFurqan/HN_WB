from fastapi import APIRouter
from ..services.policy import aggregate as aggregate_service

router = APIRouter()


@router.get("/aggregate")
def aggregate(country: str = "PK"):
    return aggregate_service(country)
