"""Ingest Wittgenstein Centre 2025-2035 educational attainment projections.

We use the SSP2 (medium) scenario, age 15-29 (youth), both sexes, attainment shares.
Wittgenstein offers CSV downloads from their data explorer.

Indicator: educational attainment distribution by country, age, sex, year (2020, 2025, 2030, 2035).
Schema in DuckDB:
  country VARCHAR (ISO3)
  scenario VARCHAR  e.g. SSP2
  year INTEGER
  age VARCHAR       e.g. "15-29"
  sex VARCHAR       e.g. "Both"
  edu_level VARCHAR e.g. "No Education", "Primary", "Lower Secondary", "Upper Secondary", "Post Secondary"
  share_pct DOUBLE
"""
from __future__ import annotations
import duckdb
import httpx
from pathlib import Path
import csv
import io

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Wittgenstein public CSV export — SSP2 attainment by age/sex/country.
# Best-effort; we try a few known endpoints and fall back to a curated extract for PAK + GHA
# stored alongside this script if download fails.
WITTGENSTEIN_URLS = [
    "https://dataexplorer.wittgensteincentre.org/wcde-v3/data/csv/wcde-v3-data-ssp2-pak-gha.csv",
]

FALLBACK = Path(__file__).parent / "wittgenstein_pk_gh_fallback.csv"


def download() -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    cached = RAW / "wittgenstein_pk_gh.csv"
    if cached.exists() and cached.stat().st_size > 1000:
        return cached.read_text(encoding="utf-8")
    for url in WITTGENSTEIN_URLS:
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            r.raise_for_status()
            cached.write_text(r.text, encoding="utf-8")
            print(f"Downloaded Wittgenstein from {url}")
            return r.text
        except Exception as e:
            print(f"  Wittgenstein url failed ({url}): {e}")
    if FALLBACK.exists():
        print(f"Using fallback CSV {FALLBACK}")
        return FALLBACK.read_text(encoding="utf-8")
    raise RuntimeError("Wittgenstein download failed and no fallback CSV present.")


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    text = download()
    rdr = csv.DictReader(io.StringIO(text))
    rows = []
    for row in rdr:
        try:
            rows.append((
                row.get("country") or row.get("ISO3"),
                row.get("scenario") or "SSP2",
                int(row.get("year") or 0),
                row.get("age") or "15-29",
                row.get("sex") or "Both",
                row.get("edu_level") or row.get("education"),
                float(row.get("share_pct") or row.get("value") or 0),
            ))
        except (ValueError, TypeError):
            continue
    print(f"Parsed Wittgenstein rows: {len(rows)}")

    con = duckdb.connect(str(DB))
    con.execute("""
        CREATE OR REPLACE TABLE wittgenstein (
            country VARCHAR,
            scenario VARCHAR,
            year INTEGER,
            age VARCHAR,
            sex VARCHAR,
            edu_level VARCHAR,
            share_pct DOUBLE
        )
    """)
    if rows:
        con.executemany(
            "INSERT INTO wittgenstein VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    n = con.execute("SELECT COUNT(*) FROM wittgenstein").fetchone()[0]
    print(f"Wittgenstein rows in DuckDB: {n}")
    con.close()


if __name__ == "__main__":
    main()
