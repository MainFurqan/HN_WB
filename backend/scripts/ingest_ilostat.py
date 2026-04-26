"""Ingest ILOSTAT mean nominal monthly earnings of employees by economic activity.

Indicator: EAR_4MTH_SEX_ECO_CUR_NB_A (mean monthly earnings in local currency,
disaggregated by sex and economic activity ISIC4).

Bulk CSV download (no auth). Filter to PAK + GHA, latest year per sector.
"""
from __future__ import annotations
import duckdb
import httpx
from pathlib import Path
import gzip
import io
import csv

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

ILOSTAT_BULK_URL = (
    "https://www.ilo.org/ilostat-files/WEB_bulk_download/indicator/"
    "EAR_4MTH_SEX_ECO_CUR_NB_A.csv.gz"
)
COUNTRIES = {"PAK", "GHA"}


def download() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / "ilostat_earnings.csv.gz"
    if target.exists() and target.stat().st_size > 100_000:
        return target
    print(f"Downloading ILOSTAT earnings bulk...")
    with httpx.stream("GET", ILOSTAT_BULK_URL, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    print(f"Saved to {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return target


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    gz_path = download()

    rows = []
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            ref = row.get("ref_area") or row.get("country")
            if ref not in COUNTRIES:
                continue
            try:
                year = int(row.get("time", "0"))
                value = float(row.get("obs_value", "") or 0)
            except (ValueError, TypeError):
                continue
            rows.append({
                "country": ref,
                "sex": row.get("sex"),
                "isic4": row.get("classif1"),
                "currency": row.get("classif2"),
                "year": year,
                "earnings": value,
            })
    print(f"Filtered ILOSTAT rows for PAK+GHA: {len(rows)}")

    con = duckdb.connect(str(DB))
    con.execute("""
        CREATE OR REPLACE TABLE ilostat_earnings (
            country VARCHAR,
            sex VARCHAR,
            isic4 VARCHAR,
            currency VARCHAR,
            year INTEGER,
            earnings DOUBLE
        )
    """)
    if rows:
        con.executemany(
            "INSERT INTO ilostat_earnings VALUES (?, ?, ?, ?, ?, ?)",
            [(r["country"], r["sex"], r["isic4"], r["currency"], r["year"], r["earnings"]) for r in rows],
        )
    print("Latest-year sample (PAK):")
    for r in con.execute("""
        SELECT isic4, sex, currency, year, earnings FROM ilostat_earnings
        WHERE country='PAK' AND sex='SEX_T'
        ORDER BY year DESC LIMIT 5
    """).fetchall():
        print(f"  {r}")
    con.close()


if __name__ == "__main__":
    main()
