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
    packs_dir: Path = _REPO_ROOT / "packs"
    default_country_pack: str = "PK"


settings = Settings()
