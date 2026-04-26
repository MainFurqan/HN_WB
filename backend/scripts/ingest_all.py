"""Ingest all upstream datasets into DuckDB.

Run once before starting the API. Each ingest_* function is idempotent —
it drops & recreates its table.

Sources:
  - ESCO skills + occupations (EU multilingual taxonomy)
  - ISCO-08 occupational codes (ILO)
  - Frey & Osborne 2013 automation probabilities (US occupations)
  - ILOSTAT wages by ISIC4 sector (PK + GH)
  - World Bank WDI sector growth + youth NEET (PK + GH)
  - Wittgenstein Centre education projections 2025-2035 (PK + GH)
  - ITU broadband penetration (PK + GH)
"""
import duckdb
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    print(f"Connected to {DB}")

    # TODO: implement each ingest step. Each script will:
    #   1. Download CSV/JSON to RAW if not present.
    #   2. CREATE OR REPLACE TABLE from CSV.
    #   3. Print row count.

    con.close()  # each script opens its own connection
    print("Running per-source ingestion scripts...")

    import subprocess
    import sys
    here = Path(__file__).parent
    for script in [
        "ingest_wdi.py",
        "ingest_frey_osborne.py",
        "ingest_esco.py",
        "ingest_ilostat.py",
        "ingest_wittgenstein.py",
    ]:
        print(f"\n=== {script} ===")
        result = subprocess.run([sys.executable, str(here / script)], capture_output=False)
        if result.returncode != 0:
            print(f"  WARNING: {script} exited with {result.returncode}")

    print("\nAll ingestion attempts complete.")


if __name__ == "__main__":
    main()
