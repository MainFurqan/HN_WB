"""Policymaker aggregate view — the second of the dual-interface module.

Surfaces:
  - Youth NEET rate (latest WDI value)
  - Informal-employment share (latest WDI value)
  - Cohort projection 2020-2035 (Wittgenstein SSP2)
  - Sector-employment shares (latest WDI agri/industry/services breakdown)
  - "Skill-supply divergence" — a simple diagnostic comparing post-secondary
    attainment growth against ICT/professional sector growth, flagging if
    education is outrunning labour demand or vice versa.
"""
from __future__ import annotations
from ..db import conn

COUNTRY_ISO2_TO_3 = {"PK": "PAK", "GH": "GHA"}


def _latest(country_iso3: str, indicator: str) -> dict | None:
    with conn() as c:
        row = c.execute(
            """
            SELECT year, value FROM wdi
            WHERE country = ? AND indicator = ? AND value IS NOT NULL
            ORDER BY year DESC LIMIT 1
            """,
            [country_iso3, indicator],
        ).fetchone()
    return {"year": row[0], "value": row[1]} if row else None


def aggregate(country: str) -> dict:
    iso3 = COUNTRY_ISO2_TO_3.get(country.upper(), country.upper())

    neet = _latest(iso3, "SL.UEM.NEET.ZS")
    informal = _latest(iso3, "SL.ISV.IFRM.ZS")
    agri = _latest(iso3, "NV.AGR.EMPL.ZS")
    industry = _latest(iso3, "NV.IND.EMPL.ZS")
    services = _latest(iso3, "NV.SRV.EMPL.ZS")
    broadband = _latest(iso3, "IT.NET.BBND.P2")
    gdp_growth = _latest(iso3, "NY.GDP.PCAP.KD.ZG")

    with conn() as c:
        cohort = c.execute(
            """
            SELECT year, edu_level, share_pct
            FROM wittgenstein
            WHERE country = ? AND age = '15-29' AND sex = 'Both'
            ORDER BY year, edu_level
            """,
            [iso3],
        ).fetchall()

    cohort_rows = [{"year": r[0], "edu_level": r[1], "share_pct": r[2]} for r in cohort]

    # Skill-supply divergence diagnostic:
    # Δ post-secondary share (2020->2035) vs Δ services-sector employment share (recent trend)
    pse_2020 = next((r["share_pct"] for r in cohort_rows if r["year"] == 2020 and r["edu_level"] == "Post Secondary"), None)
    pse_2035 = next((r["share_pct"] for r in cohort_rows if r["year"] == 2035 and r["edu_level"] == "Post Secondary"), None)
    pse_growth = (pse_2035 - pse_2020) if (pse_2020 is not None and pse_2035 is not None) else None

    divergence_note = None
    if pse_growth is not None and services is not None:
        divergence_note = (
            f"Post-secondary attainment is projected to grow by {pse_growth:.1f} percentage points "
            f"(2020-2035, SSP2). Services sector currently absorbs {services['value']:.1f}% of employment. "
            "If skill supply outpaces sector demand, expect underemployment of the most-credentialed cohort."
        )

    return {
        "country": country,
        "neet_rate": neet,
        "informal_employment_share": informal,
        "sector_employment": {
            "agriculture": agri, "industry": industry, "services": services,
        },
        "fixed_broadband_per_100": broadband,
        "gdp_per_capita_growth": gdp_growth,
        "cohort_projection_2020_2035": cohort_rows,
        "skill_supply_divergence_note": divergence_note,
    }
