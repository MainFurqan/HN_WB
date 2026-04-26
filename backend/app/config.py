from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of backend/, so the same defaults work whether the
# server runs from repo root or from backend/.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[_REPO_ROOT / ".env", _BACKEND_DIR / ".env"],
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model_fast: str = "gpt-4o-mini"
    openai_model_heavy: str = "gpt-4o"

    duckdb_path: Path = _BACKEND_DIR / "data" / "unmapped.duckdb"
    # Override-able via PACKS_DIR env var. Default falls back to whichever of
    # these exists first: backend/packs/ (Docker), repo-root/packs/ (dev).
    packs_dir: Path = _REPO_ROOT / "packs"
    default_country_pack: str = "PK"


def _resolve_packs_dir(s: Settings) -> Settings:
    """Pick whichever packs_dir actually exists on disk so dev + Docker both work."""
    if s.packs_dir.exists():
        return s
    candidates = [_BACKEND_DIR / "packs", _REPO_ROOT / "packs"]
    for c in candidates:
        if c.exists():
            s.packs_dir = c
            break
    return s


settings = _resolve_packs_dir(Settings())
