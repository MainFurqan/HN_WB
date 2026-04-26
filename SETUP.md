# UNMAPPED — Local setup

Two services run locally for the demo:
- **Backend** (FastAPI + DuckDB) on `http://127.0.0.1:8000`
- **Frontend** (Next.js 16 + Tailwind 4) on `http://localhost:3000`

## Prerequisites

- Python 3.11+ (Anaconda or system)
- Node.js 20+ and npm
- An OpenAI API key

## 1. Backend (Anaconda or venv)

```bash
# from repo root
cd backend

# Anaconda
conda create -n unmapped python=3.11 -y
conda activate unmapped
pip install -r requirements.txt

# OR plain venv
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# .venv\Scripts\activate          (Windows PowerShell / cmd)
# source .venv/bin/activate       (macOS / Linux)
pip install -r requirements.txt
```

Create the `.env` file at the **repo root** (not inside `backend/`):

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL_FAST=gpt-4o-mini
OPENAI_MODEL_HEAVY=gpt-4o
DEFAULT_COUNTRY_PACK=PK
```

Load the seed data and crawl ESCO (one-time, ~3 minutes on the ESCO crawl):

```bash
# from backend/
python scripts/ingest_seed.py     # loads bundled CSVs into DuckDB
python scripts/ingest_esco.py     # crawls ESCO REST API for ~2.5k skills + 730 occupations
```

Run the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify: open http://127.0.0.1:8000/health → `{"ok": true}`.

## 2. Frontend

```bash
# from repo root
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## 3. Walking the demo

- Landing → **Map my skills** (Pakistan)
- Either upload your CV (PDF / DOCX / TXT) at the top of the form, or fill the 6 sections manually
- **Find my skills** → confirm step (Hard / Soft / Knowledge categorised)
- **See my readiness & opportunities** → Skills Passport + AI Readiness Lens + Opportunities
- Top-right: switch language (`English / اردو` / `Twi`) or country (PK ↔ GH) — same binary, different Country Pack

## File map

```
HN_WB/
├── README.md
├── LICENSE
├── SETUP.md                ← you are here
├── .env.example
├── packs/
│   ├── PK.yaml             country pack — Pakistan
│   ├── GH.yaml             country pack — Ghana
│   └── schema.json         JSON Schema for Country Packs
├── backend/
│   ├── requirements.txt    pip dependencies
│   ├── pyproject.toml      same deps, editable-install form
│   ├── app/                FastAPI app
│   ├── data/               DuckDB + seed CSVs
│   └── scripts/            ingestion scripts
├── frontend/
│   ├── package.json
│   └── src/app/            Next.js App Router pages
└── docs/
    ├── strategy.md         build plan + scope decisions
    ├── data-sources.md     citations + limits per dataset
    └── pitch.md            3-min demo script + judge Q&A
```

## Troubleshooting

- **`/skills/extract` returns 500**: check `OPENAI_API_KEY` in `.env`.
- **DuckDB locked error**: stop both ingestion scripts and the API, then re-run.
- **Empty data on `/policy/aggregate`**: re-run `python scripts/ingest_seed.py`.
- **Frontend can't reach backend**: backend must be on `127.0.0.1:8000`. If you change the port, set `NEXT_PUBLIC_API_BASE` in `frontend/.env.local`.
