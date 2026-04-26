from functools import lru_cache
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from .config import settings


class LaborMarket(BaseModel):
    wage_source: str
    wage_table: str
    sector_classification: str
    informal_share_indicator: str | None = None


class Education(BaseModel):
    taxonomy: str
    credential_map_csv: str | None = None


class AutomationCalibration(BaseModel):
    base_model: str = "frey_osborne"
    routine_task_indicator: str | None = None
    digital_infra_indicator: str | None = None
    discount_weight: float = 0.5


class UI(BaseModel):
    languages: list[str]
    default_language: str
    low_bandwidth_mode: bool = True


class CountryPack(BaseModel):
    country_code: str = Field(..., description="ISO-3166 alpha-2")
    country_name: str
    region: str
    labor_market: LaborMarket
    education: Education
    automation: AutomationCalibration
    opportunity_types: list[str]
    ui: UI


@lru_cache(maxsize=16)
def load_pack(code: str) -> CountryPack:
    path: Path = settings.packs_dir / f"{code.upper()}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Country Pack not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CountryPack(**data)


def list_packs() -> list[str]:
    return sorted(p.stem for p in settings.packs_dir.glob("*.yaml"))
