"""Ingest World Bank WDI indicators we need.

We hit the JSON API directly (no auth, no bulk download).
Indicators:
  NV.AGR.EMPL.ZS  Employment in agriculture (% of employment)
  NV.IND.EMPL.ZS  Employment in industry (% of employment)
  NV.SRV.EMPL.ZS  Employment in services (% of employment)
  SL.UEM.NEET.ZS  Youth NEET, total (% of youth population)
  IT.NET.BBND.P2  Fixed broadband subscriptions (per 100 people)  [ITU proxy]
  SL.ISV.IFRM.ZS  Informal employment (% of total non-agri employment)
  NY.GDP.PCAP.KD.ZG  GDP per capita growth (annual %)

Countries: PAK, GHA. Range: 2015-2024.
"""
from __future__ import annotations
import duckdb
import httpx
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"

INDICATORS = [
    "NV.AGR.EMPL.ZS",
    "NV.IND.EMPL.ZS",
    "NV.SRV.EMPL.ZS",
    "SL.UEM.NEET.ZS",
    "IT.NET.BBND.P2",
    "SL.ISV.IFRM.ZS",
    "NY.GDP.PCAP.KD.ZG",
]
COUNTRIES = ["PAK", "GHA"]


def fetch(country: str, indicator: str, retries: int = 4) -> list[dict]:
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
    import time
    for attempt in range(retries):
        try:
            r = httpx.get(
                url,
                params={"format": "json", "date": "2015:2024", "per_page": 100},
                timeout=30,
            )
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            payload = r.json()
            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                return []
            return [
                {
                    "country": country,
                    "indicator": indicator,
                    "year": int(row["date"]),
                    "value": row["value"],
                }
                for row in payload[1]
                if row.get("value") is not None
            ]
        except (httpx.HTTPError, ValueError) as e:
            if attempt == retries - 1:
                print(f"  FAILED {country} {indicator}: {e}")
                return []
            time.sleep(2 ** attempt)
    return []


def main():
    """Live WDI ingest. UPSERT semantics: only adds rows on top of whatever's
    already in the table (typically loaded from seed first). Never wipes seed
    rows that the API returns null for (recent years are usually null)."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for c in COUNTRIES:
        for ind in INDICATORS:
            data = fetch(c, ind)
            print(f"  {c} {ind}: {len(data)} rows")
            rows.extend(data)
    con = duckdb.connect(str(DB))
    # Make sure the table exists with a label column matching the seed schema.
    con.execute("""
        CREATE TABLE IF NOT EXISTS wdi (
            country VARCHAR,
            indicator VARCHAR,
            indicator_label VARCHAR,
            year INTEGER,
            value DOUBLE
        )
    """)
    if rows:
        # Upsert: delete only the (country, indicator, year) cells we have new
        # values for; preserve seed rows for everything else.
        for r in rows:
            con.execute(
                "DELETE FROM wdi WHERE country=? AND indicator=? AND year=?",
                [r["country"], r["indicator"], r["year"]],
            )
        con.executemany(
            "INSERT INTO wdi (country, indicator, indicator_label, year, value) VALUES (?, ?, NULL, ?, ?)",
            [(r["country"], r["indicator"], r["year"], r["value"]) for r in rows],
        )
    n = con.execute("SELECT COUNT(*) FROM wdi").fetchone()[0]
    print(f"WDI rows in DuckDB: {n}")
    con.close()


if __name__ == "__main__":
    main()
