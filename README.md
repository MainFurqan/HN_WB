# UNMAPPED

Open infrastructure layer that closes the distance between a young person's real skills and real economic opportunity in low- and middle-income countries.

Built for **Hack Nation 2026 — World Bank Challenge 05**.

## What it does

Three modules, one country-agnostic protocol:

1. **Skills Signal Engine** — turns informal skills + education into a portable, ESCO-grounded Skills Passport (JSON-LD + QR).
2. **AI Readiness & Displacement Risk Lens** — Frey-Osborne calibrated for LMIC task composition + Wittgenstein 2025–2035 cohort projections + adjacent-skill recommendations.
3. **Opportunity Match + Econometric Dashboard** — surfaces real ILOSTAT wage ranges and WDI sector growth per opportunity. Dual interface: youth view + policymaker aggregate view.

## The protocol, not the product

Every country-specific behaviour is driven by a [Country Pack](packs/) — a YAML file. We ship two:

- [`packs/PK.yaml`](packs/PK.yaml) — Pakistan (urban informal + rural agricultural mix, English/Urdu UI)
- [`packs/GH.yaml`](packs/GH.yaml) — Ghana (Sub-Saharan urban informal, English/Twi UI; this is where Amara lives)

Switching countries is a pack swap, not a code change.

## Stack

- Backend: Python 3.11, FastAPI, DuckDB
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4
- LLM: OpenAI `gpt-4o-mini` (skill extraction)
- Data: ESCO (live API crawl), Frey-Osborne 2013, ILOSTAT, World Bank WDI, Wittgenstein WCDE-V3 — see [docs/data-sources.md](docs/data-sources.md) for full citations, vintages, and licenses

## Honest about scope

This is a hackathon prototype. What ships:
- Three modules end-to-end with real data: Skills Signal Engine (ESCO-grounded), AI Readiness Lens (LMIC-calibrated Frey-Osborne + Wittgenstein cohort projection), Opportunity Match (ILOSTAT wages + WDI sector growth)
- Two Country Packs (PK + GH) driving language, taxonomy, automation calibration, and opportunity types from YAML
- Live language flip including Urdu/RTL for Pakistan, English for Ghana
- "What we don't know" panel surfacing model limits
- Disk-cached LLM responses for demo resilience

What is **not** built (be clear with judges):
- Voice input, W3C Verifiable Credential signing, PDF passport, authentication, full live-API ingestion (most data is bundled real-value snapshot), tests, observability. See [docs/strategy.md](docs/strategy.md) for the production roadmap.

## Quick start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -e .
python scripts/ingest_all.py    # downloads & loads all datasets into DuckDB
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Honest about limits

We ship a "what we don't know" panel on every score. Frey-Osborne was trained on US labor; we discount by ITU broadband and ILO routine-task share, but we cannot capture informal-economy network effects. ESCO is EU-grounded; Pakistan-specific occupational nuance is approximated. We name the gaps.

## License

MIT — open infrastructure means open infrastructure.
