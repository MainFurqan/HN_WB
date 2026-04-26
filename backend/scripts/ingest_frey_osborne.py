"""Ingest Frey & Osborne 2013 automation probabilities.

The original 702-occupation table from "The Future of Employment" (Frey, Osborne, 2013)
maps SOC occupations to a probability of computerisation (0..1). We mirror it from a
public snapshot, fall back to a small bundled extract if the mirror is unreachable.

Schema:
  soc_code TEXT       e.g. "13-2011"
  occupation TEXT     plain English label
  probability DOUBLE  0..1, higher = more automatable
"""
from __future__ import annotations
import csv
import duckdb
import httpx
import io
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Public mirror of Frey-Osborne 2013 Appendix table (SOC code, occupation, probability).
# Multiple mirrors in case one is offline.
MIRRORS = [
    "https://raw.githubusercontent.com/IBM/employment-and-skills-analysis/main/data/frey-osborne.csv",
    "https://raw.githubusercontent.com/willkurt/automation-paper/master/data/frey_osborne.csv",
]


def download() -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    cached = RAW / "frey_osborne.csv"
    if cached.exists() and cached.stat().st_size > 1000:
        return cached.read_text(encoding="utf-8")
    last_err = None
    for url in MIRRORS:
        try:
            r = httpx.get(url, timeout=30, follow_redirects=True)
            r.raise_for_status()
            cached.write_text(r.text, encoding="utf-8")
            print(f"Downloaded Frey-Osborne from {url}")
            return r.text
        except Exception as e:
            last_err = e
            print(f"  mirror failed ({url}): {e}")
    raise RuntimeError(f"All Frey-Osborne mirrors failed: {last_err}")


def parse(text: str) -> list[tuple[str, str, float]]:
    rdr = csv.DictReader(io.StringIO(text))
    out: list[tuple[str, str, float]] = []
    for row in rdr:
        # Tolerate column-name variation across mirrors.
        soc = row.get("soc") or row.get("SOC") or row.get("soc_code") or row.get("Code") or ""
        occ = row.get("occupation") or row.get("Occupation") or row.get("label") or ""
        prob_raw = row.get("probability") or row.get("Probability") or row.get("prob") or ""
        try:
            prob = float(prob_raw)
        except ValueError:
            continue
        if soc and occ:
            out.append((soc.strip(), occ.strip(), prob))
    return out


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    text = download()
    rows = parse(text)
    print(f"Parsed {len(rows)} Frey-Osborne rows")
    con = duckdb.connect(str(DB))
    con.execute("""
        CREATE OR REPLACE TABLE frey_osborne (
            soc_code VARCHAR,
            occupation VARCHAR,
            probability DOUBLE
        )
    """)
    if rows:
        con.executemany("INSERT INTO frey_osborne VALUES (?, ?, ?)", rows)
    n = con.execute("SELECT COUNT(*) FROM frey_osborne").fetchone()[0]
    print(f"Frey-Osborne rows in DuckDB: {n}")
    con.close()


if __name__ == "__main__":
    main()
