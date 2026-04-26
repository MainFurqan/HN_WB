"""OpenAI client with on-disk response cache.

Cache rationale:
  - Live demo can't fail. If the API rate-limits, errors, or the network blips,
    we replay the most recent successful response for the same input.
  - Caching is keyed on a hash of (model, messages, response_format).
  - Cache also reduces redundant cost when iterating on the demo.
"""
from __future__ import annotations
from openai import OpenAI
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from .config import settings

_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "llm_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def _key(model: str, messages: list[dict], response_format: dict | None) -> str:
    payload = json.dumps(
        {"m": model, "msgs": messages, "rf": response_format},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _read_cache(key: str) -> str | None:
    p = _CACHE_DIR / f"{key}.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def _write_cache(key: str, value: str) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"{key}.txt").write_text(value, encoding="utf-8")


def chat(messages: list[dict], model: str | None = None, **kwargs) -> str:
    model = model or settings.openai_model_fast
    key = _key(model, messages, None)
    try:
        resp = client().chat.completions.create(model=model, messages=messages, **kwargs)
        text = resp.choices[0].message.content or ""
        _write_cache(key, text)
        return text
    except Exception:
        cached = _read_cache(key)
        if cached is not None:
            return cached
        raise


def chat_json(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    model = model or settings.openai_model_fast
    rf = {"type": "json_object"}
    key = _key(model, messages, rf)
    try:
        resp = client().chat.completions.create(
            model=model,
            messages=messages,
            response_format=rf,
            **kwargs,
        )
        text = resp.choices[0].message.content or "{}"
        _write_cache(key, text)
        return json.loads(text)
    except Exception:
        cached = _read_cache(key)
        if cached is not None:
            return json.loads(cached)
        raise
