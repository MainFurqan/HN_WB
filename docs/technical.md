# UNMAPPED — A technical walkthrough for judges

> Hi. Thanks for reading this. We wrote it the way we'd want one written for us — short, honest, with file paths so you can verify anything you doubt. The whole document is about 10 minutes long.

---

## What we built, in one paragraph

UNMAPPED is an open infrastructure layer that takes a young person's messy, real-world description of their work — phone repair, YouTube self-study, half-finished school, family business — and turns it into a portable, government-readable Skills Passport. It then tells them, calibrated to their actual country, how exposed their work is to AI/automation and which real opportunities their skills can reach. It does this without hardcoding any country, language, or labour assumption: every country-specific behaviour is driven by a single YAML file we call a **Country Pack**. Two ship today (Pakistan and Ghana). The third is a pull request away.

The brief asked for three modules: a Skills Signal Engine, an AI Readiness Lens, and an Opportunity Match — all country-agnostic, all grounded in real data, all honest about limits. We built all three.

---

## The thesis: protocol, not product

The single biggest decision we made was framing. Most teams will build "a skills app." We built a protocol with a reference implementation.

The difference matters because the brief grades on *localizability as a design feature, not a slide*. A product is something we own and you adopt. A protocol is something anyone can adopt without asking us. Three artefacts make the protocol:

1. **The Country Pack YAML schema** — see [`packs/schema.json`](../packs/schema.json) and the two implementations: [`packs/PK.yaml`](../packs/PK.yaml) and [`packs/GH.yaml`](../packs/GH.yaml).
2. **The Skills Passport JSON-LD context** — a portable, open-standard format any wallet, employer, or training provider can consume. See the document built in [`backend/app/services/passport.py`](../backend/app/services/passport.py).
3. **The reference implementation** — MIT-licensed FastAPI + Next.js, the thing you're looking at.

A government doesn't deploy our app. They publish a country pack, optionally fork the reference implementation, and run their own. That's how open infrastructure scales.

---

## What happens when one user goes through it

Let's follow Amara — the brief's persona — through the system. She lives near Accra, runs a phone repair shop, taught herself basic Python. She opens the live URL on her phone.

### Step 1: She lands on the home page

The page is at [`frontend/src/app/page.tsx`](../frontend/src/app/page.tsx). It's intentionally thin — a hero, two cards (youth and policymaker), a country chooser. She picks **Map my skills · Pakistan**. (We'll switch to Ghana mid-demo to prove the protocol works.)

The URL becomes `/youth?country=PK`. Now [`frontend/src/app/youth/page.tsx`](../frontend/src/app/youth/page.tsx) takes over.

### Step 2: The page loads in Urdu, right-to-left

Notice we didn't ask her language. The Country Pack told us. Look at [`packs/PK.yaml`](../packs/PK.yaml) — the `ui.default_language` field is `ur`. The frontend reads that on mount, applies `dir="rtl"`, and pulls Urdu strings from [`frontend/src/lib/i18n.ts`](../frontend/src/lib/i18n.ts).

There is a language pill in the header (English / اردو) so she can flip if she prefers — but the *default* is governed by her country, not by us.

### Step 3: She uploads her CV — or fills the form

At the top of the form is a card: **📄 Have a CV? Auto-fill from your resume.** She drops a PDF.

That goes to `POST /skills/parse-cv`, defined in [`backend/app/routers/skills.py`](../backend/app/routers/skills.py). The handler is short — it validates extension and size, then calls [`parse_cv_to_profile`](../backend/app/services/cv_parser.py).

That function uses `pypdf` (for PDF) or `python-docx` (for DOCX) to extract text, caps it at 18,000 chars, and asks GPT-4o-mini to map the text onto our six profile sections. The system prompt (visible in [`backend/app/services/cv_parser.py`](../backend/app/services/cv_parser.py)) explicitly tells the model: *use the user's own wording, never invent dates or employers, leave a section empty if the CV doesn't cover it*.

The response populates six labelled textareas: About you, Education, Work, Self-taught, Tools, Aspirations. Amara reviews. Edits if needed. Hits **Find my skills**.

### Step 4: The Skills Signal Engine grounds her on ESCO

The form sends a labelled text blob to `POST /skills/extract`, which lands in [`extract_skills`](../backend/app/services/skills_engine.py).

This is the most engineering-dense part of the system, and the place we worked hardest to prevent the model from making things up. The function does three things:

**1. Build a shortlist from DuckDB.** We pre-screen the ESCO catalogue (~2,500 skills, crawled live from the EU REST API at build time — see [`backend/scripts/ingest_esco.py`](../backend/scripts/ingest_esco.py)) by overlap with the user's text. Multi-word phrases score 4× higher than single tokens — the line that matters is in [`shortlist_from_duckdb`](../backend/app/services/skills_engine.py). This is the v2 fix that killed false positives like "process data" matching "dairy processing."

**2. Send the top 40 to GPT-4o-mini with a strict prompt.** The prompt is in the same file. It enforces six rules: pick only from the shortlist, cite a *different* verbatim quote per skill, categorise as hard / soft / knowledge, confidence between 0.55 and 0.99, return 6–12 skills (quality over quantity), reject vague matches.

**3. Post-process defensively.** Even with a strict prompt, the model occasionally misbehaves. We dedupe URIs, enforce distinct quotes (max 2 picks per identical quote), clamp confidence into the legal range, and force the category to one of three values. The post-processing is at the bottom of [`extract_skills`](../backend/app/services/skills_engine.py).

The model never sees the full ESCO taxonomy. It picks from a pre-screened list. Result: zero URI hallucination. Every ESCO URI we surface is a real concept at `http://data.europa.eu/esco/skill/<uuid>` that you can paste into a browser and verify.

### Step 5: She confirms what's actually hers

The confirm step is in [`frontend/src/app/youth/page.tsx`](../frontend/src/app/youth/page.tsx) (look for `ConfirmStep`). The candidates come back grouped into Hard / Soft / Knowledge. Each card shows the ESCO label, the verbatim evidence quote from her profile, the confidence percentage, and the full ESCO URI.

Everything starts **unchecked**. The brief says Amara should "own" the passport — pre-checking implies the AI decided. We default to off. She ticks what's actually hers.

### Step 6: She hits "See my readiness & opportunities" — and three things happen at once

The button fires three parallel API calls (see `runFinalize` in [`youth/page.tsx`](../frontend/src/app/youth/page.tsx)):

- `POST /skills/passport` — builds her JSON-LD passport with QR code
- `POST /readiness/` — the AI Readiness Lens
- `POST /opportunities/match` — the Opportunity Match

When all three return she sees a single result page with three sections.

---

## The AI Readiness Lens — calibrated honesty

The implementation is in [`backend/app/services/readiness.py`](../backend/app/services/readiness.py). It does *not* use an LLM. Everything is deterministic Python over DuckDB. We chose this deliberately — a Ministry of Labour can't deploy a black box.

### The base risk

We bundled 60 occupations from the **Frey-Osborne 2013** paper into [`backend/data/seed/frey_osborne_seed.csv`](../backend/data/seed/frey_osborne_seed.csv) (with provenance in the sibling `.source.yaml`). Given the user's ISCO cluster hint from Module 1, [`_frey_osborne_for_isco`](../backend/app/services/readiness.py) finds the closest matching occupations and returns the median probability. If we can't find a tight match we fall back to a neutral prior of 0.40 and we say so in the calibration notes.

### The LMIC calibration — the formula a judge can audit

This is the line that matters, in plain English:

> **calibrated_risk = base_risk × (1 − discount_weight × digital_infra_gap)**

Where `digital_infra_gap = max(0, 1 − country_broadband_per_100 / 30)`. The 30 anchors against US-equivalent fixed-broadband saturation. A country at 1.4/100 (Pakistan, real WDI value) has a gap of 0.95. The discount_weight comes from the Country Pack — Pakistan ships at 0.6, Ghana at 0.55. A government adopting UNMAPPED can tune that without code changes.

Concrete walkthrough for Amara in Pakistan:
- ISCO cluster `7422` → Frey-Osborne base 0.40
- Pakistan broadband 1.4/100 → digital_infra_gap = 0.95
- discount_weight = 0.6 → calibrated_risk = 0.40 × (1 − 0.6 × 0.95) = **0.17**

The full formula text is rendered in the UI's `calibration_notes` panel verbatim. No black box, no hidden adjustment.

### Skills classification + adjacent skills

We classify each skill the user confirmed as **durable / at-risk / mixed** by keyword match on its ESCO label. The keyword sets are at the top of [`readiness.py`](../backend/app/services/readiness.py). It's a heuristic — we say so in the limits panel — but it's transparent and a country pack can override it.

For her durable skills, we walk the ESCO label space to find adjacent skills via token overlap (see [`_adjacent_skills`](../backend/app/services/readiness.py)). The proper approach is the official ESCO `skillSkillRelations` endpoint; we documented that as a future improvement.

### Wittgenstein cohort projection

Pure data lookup. We pull SSP2 educational attainment for ages 15–29 in her country, years 2020 / 2025 / 2030 / 2035, from [`backend/data/seed/wittgenstein_seed.csv`](../backend/data/seed/wittgenstein_seed.csv). The frontend renders it as a stacked horizontal bar chart with five bands.

For Pakistan, post-secondary attainment grows from 9.9% (2020) to 15.7% (2035). Real Wittgenstein WCDE-V3 numbers, snapshotted into the repo with citation in the source YAML.

### The "What we don't know" panel

Three plain-language bullets, generated on every result. Frey-Osborne is from 2013. ESCO is EU-grounded. Adjacent-skills uses a heuristic, not the official graph. The brief grades on honesty about limits — most submissions hide gaps, ours surfaces them on the same card as the headline number.

---

## The Opportunity Match — real wages, real growth

Implementation in [`backend/app/services/opportunities.py`](../backend/app/services/opportunities.py). Also no LLM — deterministic SQL over DuckDB.

### Multi-word phrase scoring

Same v1 problem as the Skills Engine: single-token matching produced absurd results. "Process data" matched "dairy processing." We rewrote it to weight 2-word phrases 4× more than single tokens — see the loop building `phrases` and `single_tokens` in [`match`](../backend/app/services/opportunities.py). False positives gone.

### ISCO classifier from occupation labels

The ESCO REST API search response doesn't include the occupation's ISCO group directly — fetching it per occupation would be ~700 extra API calls. Instead we regex-classify the occupation's preferredLabel into one of nine ISCO 1-digit groups. The patterns are at the top of [`opportunities.py`](../backend/app/services/opportunities.py): `engineer / scientist / developer` → 2 (Professionals), `technician / specialist` → 3, `repairer / electrician / tailor` → 7 (Craft & trades), and so on.

It's a heuristic. We say so. The proper approach is the BLS ISCO/SOC crosswalk; that's on the production roadmap.

### ISCO-tier wages — the fix to the most embarrassing v1 bug

In v1 we used the flat ILOSTAT TOTAL-sector mean for every wage. An AI Engineer in Pakistan was showing PKR 18,225–30,375 per month — about 5× too low. The TOTAL mean is dominated by informal workers and crushes professional wages.

The fix: an ISCO-major-group wage anchor table per country with p25 / p50 / p75 values. See [`backend/data/seed/isco_wage_tiers.csv`](../backend/data/seed/isco_wage_tiers.csv). A Manager (ISCO 1) in Pakistan now sees PKR 180k–420k. A Professional (ISCO 2) sees 95k–260k. A Technician (ISCO 3) — like Amara, who classifies into ISCO 7 (Craft) — sees PKR 26k–58k. All realistic.

We render the **range, not a point estimate**, because within-major-group dispersion is large and we won't fake precision. We label the basis (`"ISCO major group anchor"`) so judges know where the number comes from.

### Sector growth from WDI

The second visible signal. We map ISCO major group → dominant ISIC4 sector (the `ISCO_TO_ISIC4` dict at the top of `opportunities.py`) → WDI indicator (NV.AGR.EMPL.ZS for agriculture, NV.IND.EMPL.ZS for industry, NV.SRV.EMPL.ZS for services). Then compute the 5-year trend from the cached WDI rows in DuckDB.

Each opportunity card displays the wage range AND the sector growth side-by-side, both with their source codes (`ILOSTAT`, `WDI · NV.SRV.EMPL.ZS`) so a judge can verify.

### Honest `why_match`

Three variants, generated by [`_why_match`](../backend/app/services/opportunities.py):

- Strong overlap → `"Strong overlap with: repair mobile devices, repair ICT devices."`
- Multi-word match without specific overlap → `"Multi-word skill match against this occupation's profile."`
- Weak overlap → `"Partial keyword overlap only — review the full job description before applying."`

When the match is weak, we say so on the card. We refuse to over-promise.

---

## The Country Pack — the YAML that drives everything

Open [`packs/PK.yaml`](../packs/PK.yaml) and read the whole thing. It's 25 lines.

It declares: the country code, region, labour-market data source, sector classification (ISIC4), education taxonomy (ISCED-2011), automation calibration parameters (base model, indicators to use, discount weight), opportunity types to surface, and UI configuration (available languages, default language, low-bandwidth mode).

Every part of the system reads from this file. The default language flips the UI to RTL. The discount weight is plugged directly into the readiness formula. The opportunity types filter what shows up on the match page. The wage table name routes the wage lookup.

[`packs/GH.yaml`](../packs/GH.yaml) is the same shape with different values. That's the entire surface for adding a new country: write a YAML, validate against [`packs/schema.json`](../packs/schema.json), drop it in. No code change.

The loader is in [`backend/app/country_pack.py`](../backend/app/country_pack.py). It uses Pydantic models to validate at runtime and `lru_cache` so the YAML is parsed once per process.

---

## Real data, real sources

Every numerical claim in the system traces back to a real published source. We snapshot the data into the repo because the live sources are inconsistent (the WDI API has 502 outages, the ILOSTAT bulk URLs were broken at submission time, ESCO's bulk download is gated behind JS). For each snapshot we ship a sibling `.source.yaml` documenting:

- Dataset name and indicator code
- Source URL and citation
- License
- Retrieval method
- Vintage (year of data)
- Known limits

See [`backend/data/seed/`](../backend/data/seed/) — every CSV has a `.source.yaml` next to it. The files are: Frey-Osborne 2013, ILOSTAT mean monthly earnings by ISIC4, ISCO-major-group wage tiers, Wittgenstein WCDE-V3 SSP2 attainment projections, and World Bank WDI indicators (NEET, broadband, sector employment, GDP growth, informal employment share).

ESCO is different — we don't snapshot it. We crawl the live EU REST API at Docker build time using ~100 LMIC-relevant seed terms (see [`backend/scripts/ingest_esco.py`](../backend/scripts/ingest_esco.py)). The crawl yields ~2,500 unique skills + ~730 occupations baked into the image. Cold start time stays under 5 seconds because the database is pre-populated.

---

## Architecture in one diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 16 + React 19 + Tailwind 4                  │
│  • i18n (en / ur / tw) with RTL                                 │
│  • CV upload, structured profile, confirm, result               │
│  • Server-rendered policy dashboard                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ JSON over HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend — FastAPI on Python 3.11                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────┐ │
│  │ Skills       │  │ AI Readiness │  │ Opportunity  │  │ Pol-│ │
│  │ Signal       │  │ Lens         │  │ Match        │  │ icy │ │
│  │ Engine       │  │ (det. python)│  │ (det. python)│  │     │ │
│  │ (LLM-grounded)│  │              │  │              │  │     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──┬──┘ │
│         │                  │                  │              │   │
│         └─────────  CountryPack loader  ─────┴──────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  DuckDB — single-file analytical DB                             │
│                                                                 │
│  Tables:                                                        │
│    esco_skills (2,510)        wittgenstein (40)                 │
│    esco_occupations (734)     frey_osborne (60)                 │
│    wdi (64)                   isco_wage_tiers (18)              │
│    ilostat_earnings (34)                                        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ pulls country-specific config
                              │
┌─────────────────────────────────────────────────────────────────┐
│  Country Packs — YAML files                                     │
│  packs/PK.yaml  ·  packs/GH.yaml  (validated by schema.json)    │
└─────────────────────────────────────────────────────────────────┘
```

Backend deployed on AWS App Runner (containerised FastAPI). Frontend deployed on AWS Amplify (Next.js). ECR for image storage. The Dockerfile ([`backend/Dockerfile`](../backend/Dockerfile)) builds from the repo root so the country packs are copied into the image, runs `ingest_seed.py` and `ingest_esco.py` at build time, and ships a fully populated database.

---

## What we deliberately didn't build, and why we say so

The brief explicitly grades on honesty about limits. Here's the full list:

- **Voice input.** Amara's reality includes shared phones and patchy bandwidth. Voice would help. We cut it for time.
- **W3C Verifiable Credential signing.** The Skills Passport is JSON-LD with the right namespaces (it's VC-compatible) but unsigned. Without signatures the claims aren't cryptographically verifiable across borders, which limits the "portable" promise.
- **Live multilingual extraction.** Our LLM call grounds against English ESCO labels. A profile in Urdu would currently get auto-translated by the model rather than scored against multilingual ESCO labels.
- **Full live ingestion.** We ship snapshots because the upstream APIs are unstable. Live ingestion is implemented in [`backend/scripts/`](../backend/scripts/) and runs in the Dockerfile, but most data is bundled.
- **Tests.** Zero pytest, zero Playwright. A production deployment needs schema-property tests for every Country Pack, contract tests for each endpoint, and a regression test that calibrated risk stays in [0,1] under any pack values.
- **Observability.** No structured logs, no OpenTelemetry, no OpenAI cost dashboard.
- **Authentication.** No accounts, no API keys for institutional callers (training providers, employers verifying a passport). The current prototype stores nothing server-side — profiles live in browser localStorage.
- **Per-occupation LMIC calibration.** Currently a single country-level discount weight. In reality the routine task share varies by occupation within a country; the proper approach uses ILO task indices.
- **ESCO `skillSkillRelations`.** Adjacent skills currently use token overlap. The official graph would be more accurate.

All of these are documented in the production roadmap inside [`docs/strategy.md`](./strategy.md).

---

## Why we think this is more than a hackathon prototype

Three things, briefly:

1. **The thesis is right.** "Open infrastructure with country packs as pull requests" is exactly what 600 million unmapped young people need. It scales. It doesn't depend on us being around in five years.

2. **The grounding is real.** Every ESCO URI is a real concept. Every wage number cites a source. Every formula is in the UI as plain text. A Ministry of Labour can audit every claim we make.

3. **The country swap actually works.** Open the live URL, change `country=PK` to `country=GH` in the URL, and the language flips, the wages switch currency, the calibration adjusts, the opportunities change. Same binary, different YAML. You can do that yourself in 10 seconds. That's the demo, and it's also the thesis.

---

## How to verify any claim in this document

Every code reference above is a relative path from this file. Open [`backend/app/services/readiness.py`](../backend/app/services/readiness.py), search for the formula, read it. Open [`packs/PK.yaml`](../packs/PK.yaml), change `discount_weight` from 0.6 to 0.3, hit refresh, watch the readiness number change. Open [`backend/data/seed/isco_wage_tiers.source.yaml`](../backend/data/seed/isco_wage_tiers.source.yaml) and read where the wages come from. Open `/docs#/default/health_health_get` on the live API and you'll see the OpenAPI spec we get for free from FastAPI.

We tried to build this so that nothing is hidden. Thanks for reading. If anything in here doesn't add up, find us — we'd rather defend it in person.
