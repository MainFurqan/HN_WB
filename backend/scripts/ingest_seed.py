"""Load bundled seed CSVs into DuckDB.

Used as a fallback when upstream APIs are unreachable, AND as the canonical
loader for sources that don't expose stable bulk endpoints (Frey-Osborne,
Wittgenstein). Live ingestion scripts (ingest_wdi.py, ingest_ilostat.py)
will OVERWRITE these tables with live data when they succeed.

All seed values cite their original source in <name>.source.yaml alongside
the CSV.
"""
from __future__ import annotations
import duckdb
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
SEED = Path(__file__).resolve().parents[1] / "data" / "seed"


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))

    # Frey-Osborne
    fo = SEED / "frey_osborne_seed.csv"
    con.execute(f"""
        CREATE OR REPLACE TABLE frey_osborne AS
        SELECT soc_code, occupation, probability
        FROM read_csv_auto('{fo.as_posix()}', header=true)
    """)
    n = con.execute("SELECT COUNT(*) FROM frey_osborne").fetchone()[0]
    print(f"frey_osborne: {n} rows")

    # ILOSTAT wages
    il = SEED / "ilostat_wages_seed.csv"
    con.execute(f"""
        CREATE OR REPLACE TABLE ilostat_earnings AS
        SELECT country, sex, isic4, isic4_label, currency, year, earnings
        FROM read_csv_auto('{il.as_posix()}', header=true)
    """)
    n = con.execute("SELECT COUNT(*) FROM ilostat_earnings").fetchone()[0]
    print(f"ilostat_earnings: {n} rows")

    # Wittgenstein
    wc = SEED / "wittgenstein_seed.csv"
    con.execute(f"""
        CREATE OR REPLACE TABLE wittgenstein AS
        SELECT country, scenario, year, age, sex, edu_level, share_pct
        FROM read_csv_auto('{wc.as_posix()}', header=true)
    """)
    n = con.execute("SELECT COUNT(*) FROM wittgenstein").fetchone()[0]
    print(f"wittgenstein: {n} rows")

    # WDI
    wd = SEED / "wdi_seed.csv"
    con.execute(f"""
        CREATE OR REPLACE TABLE wdi AS
        SELECT country, indicator, indicator_label, year, value
        FROM read_csv_auto('{wd.as_posix()}', header=true)
    """)
    n = con.execute("SELECT COUNT(*) FROM wdi").fetchone()[0]
    print(f"wdi: {n} rows")

    # ISCO wage tiers (anchors per ISCO major group, country-specific)
    iw = SEED / "isco_wage_tiers.csv"
    con.execute(f"""
        CREATE OR REPLACE TABLE isco_wage_tiers AS
        SELECT country, CAST(isco_major AS VARCHAR) AS isco_major, isco_label, p25, p50, p75, currency
        FROM read_csv_auto('{iw.as_posix()}', header=true)
    """)
    n = con.execute("SELECT COUNT(*) FROM isco_wage_tiers").fetchone()[0]
    print(f"isco_wage_tiers: {n} rows")

    # Show health summary
    print("\nDuckDB health:")
    for tbl in ["frey_osborne", "ilostat_earnings", "wittgenstein", "wdi"]:
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n}")

    con.close()
    print("Seed load complete.")


if __name__ == "__main__":
    main()
