"""Skills Signal Engine — turns informal/free-text descriptions into ESCO-grounded skills."""
from __future__ import annotations
import re
from typing import Any
from ..db import conn
from ..llm import chat_json
from ..config import settings


SYSTEM_PROMPT = """You are an expert occupational analyst skilled in the ESCO \
(European Skills, Competences, Qualifications and Occupations) taxonomy.

Given a young person's structured profile (sections labelled ABOUT, EDUCATION, \
WORK / EXPERIENCE, SELF-TAUGHT, TOOLS / TECH, ASPIRATIONS), identify which \
ESCO skills from a SHORTLIST best describe what the person ACTUALLY does or \
has demonstrably learned.

PROCESS:
1. Read the entire profile carefully. Note the dominant occupation/domain \
and the specific tools, technologies, languages, and tasks mentioned.
2. For EACH specific tool/tech/task mentioned (e.g. "Python", "PyTorch", \
"machine learning", "deploying on AWS", "phone repair", "tailoring"), find \
a matching ESCO skill on the shortlist if one exists.
3. Include each strong match. Reject vague/coincidental matches.

HARD RULES:
- ONLY pick ESCO skill URIs from the provided shortlist. Never invent URIs.
- Pair each pick with a DIFFERENT verbatim evidence quote from the profile. \
Do not reuse the same quote across multiple skills.
- Categorise each pick as exactly one of: "hard", "soft", "knowledge".
- Confidence: 0.85-0.95 when the profile names the exact skill/tool. \
0.65-0.80 when the skill is clearly inferred from a specific task. \
Below 0.55: reject instead of including.
- Aim for 6-12 strong skills when the profile is detailed (multiple tools, \
clear work history). Return fewer ONLY if the profile is sparse.
- A profile that mentions Python, PyTorch, machine learning, neural networks, \
LLMs, AWS, etc. should yield 8-12 skills, not 3-4. Cover the user's actual \
tech stack with separate ESCO skills where they exist on the shortlist.
- A profile that mentions phone repair, tailoring, farming, etc. should \
likewise yield distinct skills for each domain task.

OUTPUT JSON (illustrative shape — produce real values for a real profile):
{
  "skills": [
    {
      "esco_uri": "<URI from shortlist>",
      "label": "<exact preferredLabel from shortlist>",
      "category": "hard|soft|knowledge",
      "confidence": <0.55 to 0.99>,
      "evidence_quote": "<distinct verbatim phrase from the profile>"
    }
  ],
  "isco_hint": "<ISCO-08 4-digit unit group code matching the dominant occupation>"
}"""


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower()) if len(t) > 3]


_STOPWORDS = {
    "about", "education", "experience", "work", "self", "taught", "tools", "tech",
    "aspirations", "language", "english", "urdu", "with", "from", "have", "been",
    "year", "years", "month", "months", "live", "lives", "speak", "speaks",
    "the", "and", "that", "this", "these", "those", "would", "could", "should",
    "very", "much", "more", "less", "some", "many", "lots", "totally", "really",
    "since", "until", "after", "before", "during", "while", "when", "where",
    "doing", "done", "make", "made", "take", "taken", "give", "given",
}


def shortlist_from_duckdb(description: str, limit: int = 60) -> list[dict[str, Any]]:
    """Score ESCO skills by keyword + multi-word-phrase overlap with the profile."""
    text_lower = description.lower()
    tokens = [t for t in _tokenize(description) if t not in _STOPWORDS]
    if not tokens:
        return []

    # Build 2-word phrases from the profile (excluding stop words).
    cleaned_words = [t for t in re.findall(r"[a-zA-Z]{4,}", text_lower) if t not in _STOPWORDS]
    phrases: list[str] = []
    for i in range(len(cleaned_words) - 1):
        ph = f"{cleaned_words[i]} {cleaned_words[i+1]}"
        if ph not in phrases:
            phrases.append(ph)

    score_terms: list[str] = []
    params: list[Any] = []
    # Multi-word phrase hits weighted x6, single-token hits x1 on label, x0.5 on description.
    for ph in phrases[:25]:
        score_terms.append(
            "(CASE WHEN INSTR(LOWER(preferredLabel), ?) > 0 THEN 8 "
            "WHEN INSTR(LOWER(description), ?) > 0 THEN 4 ELSE 0 END)"
        )
        params.extend([ph, ph])
    for tok in tokens[:25]:
        score_terms.append(
            "(CASE WHEN INSTR(LOWER(preferredLabel), ?) > 0 THEN 2 "
            "WHEN INSTR(LOWER(description), ?) > 0 THEN 1 ELSE 0 END)"
        )
        params.extend([tok, tok])

    score_sql = " + ".join(score_terms) if score_terms else "0"
    sql = f"""
        SELECT
            conceptUri AS esco_uri,
            preferredLabel AS label,
            COALESCE(description, '') AS description,
            ({score_sql}) AS score
        FROM esco_skills
        WHERE ({score_sql}) >= 2
        ORDER BY score DESC
        LIMIT {int(limit)}
    """
    with conn() as c:
        rows = c.execute(sql, params + params).fetchdf()
    return rows.to_dict(orient="records")


def extract_skills(description: str, country: str = "PK", language: str = "en") -> dict:
    shortlist = shortlist_from_duckdb(description, limit=40)
    if not shortlist:
        return {"skills": [], "isco_hint": None, "shortlist_size": 0}

    # Rank by score descending; top matches get presented first (stronger signal to LLM).
    shortlist_lines = "\n".join(
        f"- [score {int(r['score']):>2}] {r['esco_uri']} | {r['label']} -- {r['description'][:140]}"
        for r in shortlist
    )
    user_prompt = (
        f"USER PROFILE:\n{description}\n\n"
        f"COUNTRY CONTEXT: {country}\n"
        f"PROFILE LANGUAGE: {language}\n\n"
        f"ESCO SHORTLIST (sorted by pre-screening relevance score, highest first). "
        f"Pick ONLY from these {len(shortlist)} URIs. The top-scoring items are most "
        f"likely strong matches — examine them first:\n"
        f"{shortlist_lines}\n"
    )

    result = chat_json(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=settings.openai_model_fast,
        temperature=0.2,
    )

    skills = result.get("skills") or []
    seen_uris: set[str] = set()
    quote_counts: dict[str, int] = {}
    cleaned = []
    for s in skills:
        uri = s.get("esco_uri")
        if not uri or uri in seen_uris:
            continue
        quote = (s.get("evidence_quote") or "").strip()
        quote_lc = quote.lower()
        if quote_lc:
            if quote_counts.get(quote_lc, 0) >= 2:
                continue  # at most 2 skills per identical quote
            quote_counts[quote_lc] = quote_counts.get(quote_lc, 0) + 1

        cat = s.get("category", "hard")
        if cat not in ("hard", "soft", "knowledge"):
            cat = "hard"
        s["category"] = cat

        try:
            conf = float(s.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0
        # Floor sketchy 0/null confidences to 0.55 — the LLM was told never to emit < 0.55.
        if conf < 0.5:
            conf = 0.55
        if conf > 0.99:
            conf = 0.99
        s["confidence"] = round(conf, 2)

        seen_uris.add(uri)
        cleaned.append(s)

    result["skills"] = cleaned
    result["shortlist_size"] = len(shortlist)
    return result
