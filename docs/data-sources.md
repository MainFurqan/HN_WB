# Data sources & honesty notes

UNMAPPED is grounded on real, publicly-published economic data. This document
lists every dataset we use, where it came from, what its limits are, and how
it is incorporated.

## Live API ingestion

| Dataset | Endpoint | Vintage |
|---|---|---|
| **ESCO Skills + Occupations** | `https://ec.europa.eu/esco/api/search` (no auth) | v1.2.0 |

Crawled via seed-term search at build time. ~1500 unique skills + ~411 occupations cached locally in DuckDB. License: ESCO is published under EU Open Data terms.

## Snapshot extracts (bundled CSVs in `backend/data/seed/`)

We bundle real-value extracts from these sources because (a) live bulk endpoints
were unstable during the build window or (b) the dataset is small enough that
a snapshot is more reliable than a runtime fetch. Each CSV ships with a
companion `*.source.yaml` documenting source URL, citation, retrieval
methodology, and known limitations.

| Dataset | File | Source | License |
|---|---|---|---|
| **World Bank WDI** (employment shares, NEET, broadband, informal share, GDP growth, all for PAK + GHA, 2019–2024) | `wdi_seed.csv` | databank.worldbank.org/source/world-development-indicators | CC BY 4.0 |
| **ILOSTAT mean monthly earnings by ISIC4 sector** (PAK 2021, GHA 2017) | `ilostat_wages_seed.csv` | ilostat.ilo.org indicator EAR_4MTH_SEX_ECO_CUR_NB_A | ILOSTAT Open Data terms |
| **Wittgenstein Centre WCDE-V3** (educational attainment 15-29, SSP2, 2020-2035, PAK + GHA) | `wittgenstein_seed.csv` | dataexplorer.wittgensteincentre.org/wcde-v3 | Open Data |
| **Frey & Osborne 2013** (60 representative occupations from the original 702-row appendix) | `frey_osborne_seed.csv` | Frey & Osborne, *The Future of Employment* (2013), Oxford Martin School | Academic, publicly published |

When the live WDI API is reachable, `backend/scripts/ingest_wdi.py` upserts
fresh values on top of the seed (the API tends to return null for the most
recent 1-2 years; the seed preserves continuity).

## Why we surface signals visibly

The brief grades on whether at least two econometric signals are surfaced to
the user (not buried in an algorithm). Every opportunity in the youth view
shows two:

1. **Wage range** — derived from ILOSTAT monthly earnings for the matched
   ISIC4 sector, banded ±25% around the mean to reflect honest uncertainty.
2. **Sector growth** — five-year trend in WDI sector-employment-share for the
   matched ISIC4 cluster.

Source labels (`ILOSTAT`, `WDI · NV.SRV.EMPL.ZS`) are visible in the UI.

## What we don't know — explicit limits

- **Frey-Osborne is from 2013** and trained on US labour-market task structure.
  We discount it by digital-infrastructure gap (ITU broadband) but cannot
  capture informal-economy network effects that dominate LMIC labour markets.
  For production, consider supplementing with Webb (2020) AI exposure or
  OECD Lassébie & Quintini (2022) task-level indices.
- **ESCO is EU-grounded.** We use it as the portable taxonomy because no
  comparable Pakistan- or Ghana-specific occupational ontology exists at the
  same coverage. Local nuance is approximated.
- **ISCO ↔ ISIC4 crosswalk** is a dominant-association mapping by ISCO major
  group (1-digit). Production needs the full ILO crosswalk matrix.
- **SOC ↔ ISCO mapping** for Frey-Osborne lookup uses keyword overlap on
  occupation labels. Production needs the BLS SOC-to-ISCO crosswalk.
- **Skill-level co-occurrence** (used for "adjacent skills" recommendations)
  uses label-token overlap, not the ESCO `skillSkillRelations` graph.
- **Wittgenstein bundled snapshot** reflects the published SSP2 distribution
  for the cohort and years we use; live programmatic retrieval from the
  Wittgenstein dashboard is interactive and was not wired for the prototype.

These limits are surfaced to every user inside the **"What we don't know"**
panel on the AI Readiness Lens result.

## Data refresh cadence (production proposal)

| Dataset | Refresh | Owner |
|---|---|---|
| ESCO | quarterly | EU Commission release cycle |
| WDI | monthly (auto-update via API) | World Bank |
| ILOSTAT | annual (when ILO publishes) | ILO |
| Wittgenstein | every 5 years (release of new WCDE version) | Wittgenstein Centre |
| Frey-Osborne | static (2013 paper) — supplement with newer indices | n/a |
