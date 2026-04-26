<div align="center">

# UNMAPPED

**Open infrastructure for the world's 600 million unmapped young people.**

Closes the distance between a young person's real skills and real economic opportunity in low- and middle-income countries — without hardcoding any country, language, or labour-market assumption.

[**Live demo →**](https://main.d338e8u1ypke1f.amplifyapp.com) &nbsp;·&nbsp; [Technical walkthrough](docs/technical.md) 

Built for **Hack-Nation 2026 — World Bank Challenge 05**.

![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20Next.js%2016%20%7C%20DuckDB-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-prototype-orange)

</div>

---

## Story

> Meet Amara. She's 22, lives outside Accra, runs a phone repair shop she started at 17, and taught herself basic Python from YouTube on a shared phone. By any reasonable measure, Amara has skills.
>
> But to the formal economy, she is **unmapped**. No employer in her city knows she exists. No training program has assessed what she already knows.
>
> UNMAPPED maps her in 90 seconds — into a portable, ESCO-grounded Skills Passport, an LMIC-calibrated AI-readiness assessment, and a list of real opportunities with real wages and real sector growth. And it does this without writing a single line of country-specific code.

---

## How the protocol works

Every country-specific behaviour — language, labour data source, automation calibration, opportunity types, default RTL handling — is driven by a single YAML file we call a **Country Pack**.

Two ship today:

| Pack | Country | UI languages | Automation discount | Wage currency |
|---|---|---|---|---|
| [`packs/PK.yaml`](packs/PK.yaml) | 🇵🇰 Pakistan (urban informal + rural ag) | Urdu (default, RTL) · English | 0.60 | PKR |
| [`packs/GH.yaml`](packs/GH.yaml) | 🇬🇭 Ghana (Sub-Saharan urban informal) | English (default) · Twi | 0.55 | GHS |

Adding country 51 is a pull request — write the YAML, validate against [`packs/schema.json`](packs/schema.json), drop it in. **No code change. No rebuild.**

> **The demo moment**: open the [live URL](https://main.d338e8u1ypke1f.amplifyapp.com), walk the Amara flow in Pakistan's Urdu RTL UI, then click `→ 🇬🇭 Ghana` in the header. Same binary. Different language. Different wages. Different LMIC calibration. That's the protocol.

---

## What it does — three modules behind one API

### 1. Skills Signal Engine
Free-text profile (or CV upload) → ESCO-grounded portable **Skills Passport** with QR code, JSON-LD format, distinct verbatim evidence quotes per skill, Hard/Soft/Knowledge categorisation. Zero URI hallucination via shortlist-first LLM grounding.

→ deep dive: [`backend/app/services/skills_engine.py`](backend/app/services/skills_engine.py)

### 2. AI Readiness & Displacement Risk Lens
Frey-Osborne 2013 base probability calibrated to LMIC reality with a transparent linear discount on digital infrastructure (ITU broadband). Adjacent-skill resilience pathways. Wittgenstein WCDE-V3 SSP2 cohort projections 2020–2035. **Every formula is shown in the UI** — no black box.

→ deep dive: [`backend/app/services/readiness.py`](backend/app/services/readiness.py)

### 3. Opportunity Match + Econometric Dashboard
Real ESCO occupations matched on multi-word phrase overlap, classified into ISCO major groups, joined to **realistic wages by ISCO tier** (not flat sector mean) and **WDI 5-year sector growth**. Two visible econometric signals per opportunity. Honest `why_match` — admits when a match is weak.

Dual interface: youth view at [`/youth`](frontend/src/app/youth/page.tsx) + policymaker aggregate at [`/policy`](frontend/src/app/policy/page.tsx).

→ deep dive: [`backend/app/services/opportunities.py`](backend/app/services/opportunities.py)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 16 + React 19 + Tailwind 4                   │
│  i18n (en/ur/tw) with RTL  ·  CV upload  ·  PWA-friendly         │
└─────────────────────────────┬────────────────────────────────────┘
                              │ JSON over HTTPS
┌─────────────────────────────┴────────────────────────────────────┐
│  Backend — FastAPI on Python 3.11 (AWS App Runner)               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐       │
│  │ Skills     │ │ Readiness  │ │ Opportunity│ │ Policy   │       │
│  │ Signal     │ │ Lens       │ │ Match      │ │ aggregate│       │
│  │ Engine     │ │ (det. py)  │ │ (det. py)  │ │ (det. py)│       │
│  │ (LLM-grnd) │ │            │ │            │ │          │       │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬─────┘       │
│        └──────── Country Pack loader ──────────────┘              │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────┴────────────────────────────────────┐
│  DuckDB — single-file analytical DB (baked into Docker image)    │
│  esco_skills (2,510)        wittgenstein (40)                    │
│  esco_occupations (734)     frey_osborne (60)                    │
│  wdi (64)                   isco_wage_tiers (18)                 │
│  ilostat_earnings (34)                                           │
└──────────────────────────────────────────────────────────────────┘
```

Backend deployed on **AWS App Runner** (containerised FastAPI, image in ECR). Frontend on **AWS Amplify** (CI from GitHub `main`). Both auto-deploy on push.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Best-in-class for data work; auto-OpenAPI docs |
| Database | DuckDB | One file, joins 7 datasets in milliseconds, zero ops |
| Frontend | Next.js 16 + React 19 + Tailwind 4 | SSR + client interactivity, modern type-safe stack |
| LLM | OpenAI `gpt-4o-mini` | Cheap, fast, only used for the one hard task (free-text → ESCO URIs) |
| CV parsing | `pypdf` + `python-docx` | Auto-fills profile from uploaded resumes |
| Data sources | ESCO (live API), Frey-Osborne 2013, ILOSTAT, World Bank WDI, Wittgenstein WCDE-V3 | All citations in [`docs/data-sources.md`](docs/data-sources.md) |
| Deployment | AWS App Runner + AWS Amplify + ECR | Stateless container + static-SSR frontend, GitHub-driven CI |

---

## Quick start

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env at the REPO ROOT with: OPENAI_API_KEY=sk-...
python scripts/ingest_seed.py     # bundled real-value seeds → DuckDB (~10 sec)
python scripts/ingest_esco.py     # live ESCO API crawl → DuckDB (~3 min)
uvicorn app.main:app --reload     # runs on http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                       # runs on http://localhost:3000
```

Full step-by-step including AWS deployment in [`SETUP.md`](SETUP.md).

---

## Repo map

```
HN_WB/
├── packs/                      ← THE PROTOCOL — country YAML + JSON Schema
│   ├── PK.yaml                 Pakistan
│   ├── GH.yaml                 Ghana
│   └── schema.json
│
├── backend/                    FastAPI + DuckDB
│   ├── app/
│   │   ├── routers/            HTTP endpoints
│   │   ├── services/           module logic (skills_engine, readiness, opportunities, policy, cv_parser, passport)
│   │   ├── country_pack.py     YAML loader + Pydantic validator
│   │   ├── db.py / llm.py / config.py
│   │   └── main.py
│   ├── data/seed/              real-value snapshots + citation YAMLs
│   ├── scripts/                ingestion
│   ├── Dockerfile              builds from REPO ROOT (so packs/ is included)
│   └── requirements.txt
│
├── frontend/                   Next.js 16 + Tailwind 4
│   └── src/
│       ├── app/
│       │   ├── page.tsx        landing
│       │   ├── youth/page.tsx  the main flow
│       │   └── policy/page.tsx policymaker dashboard
│       └── lib/                api client, i18n, storage
│
└── docs/
    ├── technical.md            full technical walkthrough for judges
    ├── pitch.md                spoken pitch + decision log + judge Q&A prep
    ├── strategy.md             build plan + production roadmap
    └── data-sources.md         every dataset, source URL, vintage, license, limits
```

---

## Honest about scope

This is a 24-hour hackathon prototype. The brief grades on honesty about limits, so:

**What ships and works end-to-end:**
- Three modules with real data — Skills Signal Engine (ESCO-grounded), AI Readiness Lens (LMIC-calibrated Frey-Osborne + Wittgenstein), Opportunity Match (ILOSTAT wages by ISCO tier + WDI sector growth)
- Two Country Packs (PK + GH) driving language, taxonomy, automation calibration, opportunity types from YAML alone
- Live language flip including Urdu/RTL for Pakistan
- "What we don't know" panel surfacing model limits on every result
- CV upload auto-filling the structured profile form
- Disk-cached LLM responses for demo resilience

**What is *not* built — and we say so to judges:**
- Voice input
- W3C Verifiable Credential signing of the Skills Passport (it's JSON-LD with VC-compatible namespaces, but unsigned)
- Authentication / institutional API keys
- Full live-API ingestion (most data is bundled real-value snapshot, citations in [`docs/data-sources.md`](docs/data-sources.md))
- Automated tests (pytest backend + Playwright frontend)
- Structured observability (logs, OpenTelemetry, OpenAI cost dashboard)

The full production roadmap is in [`docs/strategy.md`](docs/strategy.md).

---

## Why this matters

> "Youth unemployment in low- and middle-income countries represents one of the defining structural failures of our time — with over 600 million young people holding real, unrecognised skills that broken credentialing systems and absent matching infrastructure render economically invisible."  
> — *World Bank Challenge 05 brief*

The countries that build open skills infrastructure today determine whether the coming decade becomes one of shared economic mobility — or one in which the most capable generation in history is also the most structurally excluded.

We chose **protocol, not product** because that's how open infrastructure scales. Country Packs are pull requests. We're closing the distance.

---

## License

[MIT](LICENSE) — open infrastructure means open licensing.

---

<div align="center">

Made for the judges and for Amara.

[**Open the live demo →**](https://main.d338e8u1ypke1f.amplifyapp.com)

</div>
