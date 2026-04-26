"""Skills Passport — portable JSON-LD + QR.

The passport is a self-contained, signed-able JSON-LD document referencing real ESCO URIs.
It is the ONLY artefact the user owns. Portable across borders & sectors per the brief.
"""
from __future__ import annotations
import base64
import io
import json
import qrcode
from datetime import datetime, timezone
from typing import Any
from ..db import conn


def build_passport(
    confirmed_skill_uris: list[str],
    holder_name: str,
    country: str,
    education_level: str | None = None,
    isco_cluster: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-LD Skills Passport from confirmed ESCO URIs."""
    skills: list[dict] = []
    if confirmed_skill_uris:
        with conn() as c:
            placeholders = ",".join("?" * len(confirmed_skill_uris))
            rows = c.execute(
                f"""
                SELECT conceptUri, preferredLabel, description
                FROM esco_skills
                WHERE conceptUri IN ({placeholders})
                """,
                confirmed_skill_uris,
            ).fetchall()
        skills = [
            {
                "@id": r[0],
                "@type": "Skill",
                "skos:prefLabel": r[1],
                "skos:definition": r[2] or "",
            }
            for r in rows
        ]

    return {
        "@context": {
            "esco": "http://data.europa.eu/esco/model#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "isco": "http://data.europa.eu/esco/isco/",
            "unmapped": "https://unmapped.dev/v1/",
        },
        "@type": "unmapped:SkillsPassport",
        "version": "0.1.0",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "holder": {"name": holder_name, "country": country},
        "education_level": education_level,
        "isco_cluster": isco_cluster,
        "skills": skills,
    }


def passport_qr_png_b64(passport: dict, share_url: str) -> str:
    """Return a base64-encoded PNG QR code that links to the shareable passport URL."""
    img = qrcode.make(share_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def passport_to_json(passport: dict) -> str:
    return json.dumps(passport, indent=2, ensure_ascii=False)
