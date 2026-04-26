"""Opportunity Match — surface real labour-market signals tied to user skills.

For a user's confirmed skills + ISCO hint, return a ranked list of 5-8
reachable opportunities. Each opportunity carries TWO visible econometric
signals:
  1. Wage range (ISCO-major-group earnings anchor, country-specific)
  2. Sector employment growth (WDI five-year trend)

Match score uses substring overlap on multi-word skill labels (not single
tokens, which produced spurious "process data" -> "dairy processing" hits).

The wage tier table is per ISCO 1-digit major group (Managers, Professionals,
Technicians, etc.) with country-specific PKR / GHS anchors — much more
realistic than the flat ILOSTAT TOTAL-sector mean.
"""
from __future__ import annotations
import re
from typing import Any
from ..db import conn
from ..country_pack import load_pack


COUNTRY_ISO2_TO_3 = {"PK": "PAK", "GH": "GHA"}

# ISCO major group -> dominant ISIC4 sector(s) (for the WDI growth signal).
ISCO_TO_ISIC4: dict[str, list[str]] = {
    "1": ["M", "K"],
    "2": ["P", "M", "Q", "J"],
    "3": ["M", "J", "Q"],
    "4": ["O", "G", "K"],
    "5": ["G", "I", "S"],
    "6": ["A"],
    "7": ["C", "F"],
    "8": ["C", "H"],
    "9": ["F", "G", "T"],
}


# Heuristic occupation-label -> ISCO major group classifier. Used because the
# ESCO REST search response doesn't include the ISCO group directly. Keys are
# regex patterns matched against the lowercased preferredLabel.
ISCO_MAJOR_HINTS: list[tuple[str, str]] = [
    (r"\b(chief|director|head|manager|supervisor)\b", "1"),
    (r"\b(developer|engineer|scientist|architect|analyst|consultant|researcher|teacher|lecturer|professor|physician|nurse practitioner|lawyer|accountant)\b", "2"),
    (r"\b(technician|associate|specialist|administrator|programmer|designer|nurse|paralegal)\b", "3"),
    (r"\b(clerk|secretary|receptionist|assistant|cashier)\b", "4"),
    (r"\b(seller|salesperson|server|waiter|waitress|cook|hairdresser|cleaner|guard|carer)\b", "5"),
    (r"\b(farmer|fisher|herder|forester|gardener)\b", "6"),
    (r"\b(carpenter|electrician|plumber|welder|tailor|baker|mechanic|painter|mason|installer|repairer|repair)\b", "7"),
    (r"\b(driver|operator|machinist|assembler|conductor)\b", "8"),
    (r"\b(labourer|laborer|porter|loader|street vendor|domestic worker|messenger|helper)\b", "9"),
]


def _isco_major_from_label(label: str, db_isco_field: str = "") -> str:
    if db_isco_field:
        head = db_isco_field.strip()[:1]
        if head.isdigit():
            return head
    lo = (label or "").lower()
    for pattern, major in ISCO_MAJOR_HINTS:
        if re.search(pattern, lo):
            return major
    return "3"  # neutral default — technician-tier


def _wage_band(country_iso3: str, isco_major: str) -> tuple[float, float, float, str] | None:
    with conn() as c:
        row = c.execute(
            """
            SELECT p25, p50, p75, currency FROM isco_wage_tiers
            WHERE country = ? AND isco_major = ?
            """,
            [country_iso3, isco_major],
        ).fetchone()
    if not row:
        return None
    return float(row[0]), float(row[1]), float(row[2]), row[3]


def _sector_growth(country_iso3: str, isco_major: str) -> tuple[float, str] | None:
    sectors = ISCO_TO_ISIC4.get(isco_major, [])
    indicator = "NV.SRV.EMPL.ZS"
    sector_label = "Services"
    if "A" in sectors:
        indicator, sector_label = "NV.AGR.EMPL.ZS", "Agriculture"
    elif any(s in sectors for s in ("C", "F", "B", "D", "E")):
        indicator, sector_label = "NV.IND.EMPL.ZS", "Industry"
    with conn() as c:
        rows = c.execute(
            "SELECT year, value FROM wdi WHERE country=? AND indicator=? ORDER BY year DESC LIMIT 5",
            [country_iso3, indicator],
        ).fetchall()
    if len(rows) < 2:
        return None
    latest = rows[0][1]
    earlier = rows[-1][1]
    if earlier in (None, 0):
        return None
    pct = ((latest - earlier) / earlier) * 100.0
    return pct, sector_label


_STOPWORDS = {
    "and", "the", "a", "an", "of", "in", "on", "to", "for", "with", "by", "or",
    "data", "system", "skill", "skills", "service", "services", "device", "devices",
}


def _multi_word_phrases(label: str) -> list[str]:
    """Return 2+ word phrases (lowercase) from a skill label, dropping stop tokens."""
    parts = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", label or "") if w.lower() not in _STOPWORDS]
    if len(parts) < 2:
        return []
    phrases = []
    for i in range(len(parts) - 1):
        phrases.append(f"{parts[i]} {parts[i+1]}")
    return phrases


def match(skill_uris: list[str], isco_cluster: str | None, country: str) -> list[dict]:
    pack = load_pack(country)
    iso3 = COUNTRY_ISO2_TO_3.get(country.upper(), country.upper())

    if not skill_uris:
        return []

    placeholders = ",".join("?" * len(skill_uris))
    with conn() as c:
        skill_rows = c.execute(
            f"SELECT preferredLabel FROM esco_skills WHERE conceptUri IN ({placeholders})",
            skill_uris,
        ).fetchall()
        skill_labels = [r[0] for r in skill_rows if r[0]]

    if not skill_labels:
        return []

    # Build phrase list (2-word phrases > single tokens) — much higher precision.
    phrases: set[str] = set()
    single_tokens: set[str] = set()
    for lbl in skill_labels:
        for ph in _multi_word_phrases(lbl):
            phrases.add(ph)
        for w in re.findall(r"[a-zA-Z]{5,}", lbl.lower()):
            if w not in _STOPWORDS:
                single_tokens.add(w)

    # Score occupations: phrase hits weighted x4, single-token hits x1.
    candidates: list[dict[str, Any]] = []
    with conn() as c:
        rows = c.execute(
            """
            SELECT conceptUri, preferredLabel, COALESCE(description,'') AS description,
                   COALESCE(iscoGroup,'') AS isco
            FROM esco_occupations
            """
        ).fetchall()
    for uri, label, desc, isco_db in rows:
        text = f"{label} {desc}".lower()
        phrase_hits = sum(1 for p in phrases if p in text)
        token_hits = sum(1 for t in single_tokens if t in text)
        score = phrase_hits * 4 + token_hits
        if score < 2:  # minimum bar — kills "dairy processing" matching "process data"
            continue
        candidates.append({
            "esco_uri": uri,
            "title": label,
            "description": desc,
            "isco_db": isco_db,
            "score": score,
            "phrase_hits": phrase_hits,
        })

    # Sort by score desc; require at least 1 phrase hit OR strong single-token signal.
    candidates.sort(key=lambda c: (c["phrase_hits"], c["score"]), reverse=True)

    # Use ISCO hint from skills extraction if available (more reliable than per-occupation guess).
    hint_major = (isco_cluster or "").strip()[:1] if isco_cluster else ""

    out: list[dict] = []
    seen_titles: set[str] = set()
    for cand in candidates:
        title = cand["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)

        major = _isco_major_from_label(title, cand["isco_db"])
        wage = _wage_band(iso3, major)
        growth = _sector_growth(iso3, major)
        match_score = min(1.0, cand["score"] / max(1.0, len(phrases) * 4.0 + len(single_tokens)))

        # Opportunity-type heuristic
        op_type = "formal_wage"
        lo = title.lower()
        if any(k in lo for k in ("vendor", "trader", "self-employed", "freelance")):
            op_type = "self_employment"
        if any(k in lo for k in ("driver", "delivery", "rider")):
            op_type = "gig"
        if op_type not in pack.opportunity_types:
            op_type = pack.opportunity_types[0]

        out.append({
            "esco_uri": cand["esco_uri"],
            "title": title,
            "isco_code": major,
            "type": op_type,
            "match_score": round(match_score, 3),
            "wage_low": round(wage[0]) if wage else None,
            "wage_p50": round(wage[1]) if wage else None,
            "wage_high": round(wage[2]) if wage else None,
            "wage_currency": wage[3] if wage else None,
            "wage_basis": "ISCO major group anchor" if wage else None,
            "sector_growth_pct": round(growth[0], 2) if growth else None,
            "sector_label": growth[1] if growth else None,
            "why_match": _why_match(title, skill_labels, cand["phrase_hits"]),
        })
        if len(out) >= 8:
            break
    return out


def _why_match(occupation_title: str, skill_labels: list[str], phrase_hits: int) -> str:
    occ_lower = (occupation_title or "").lower()
    matched = [
        s for s in skill_labels
        if any(p in occ_lower for p in _multi_word_phrases(s))
    ]
    if matched:
        return f"Strong overlap with: {', '.join(matched[:3])}."
    if phrase_hits == 0:
        return "Partial keyword overlap only — review the full job description before applying."
    return "Multi-word skill match against this occupation's profile."
