# UNMAPPED backend
# IMPORTANT: build from the REPO ROOT, not from backend/, so packs/ is in scope:
#   docker build -t hn-wb-backend:latest -f backend/Dockerfile .

FROM python:3.11-slim

WORKDIR /app

# System deps for DuckDB + httpx TLS + python-docx (lxml) + pypdf
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev libxslt1-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for layer cache
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/app /app/app
COPY backend/scripts /app/scripts
COPY backend/data /app/data

# Country packs — these MUST be in the image, otherwise /packs returns []
COPY packs /app/packs

# Populate DuckDB at build time from bundled seed CSVs (reliable, no network).
RUN python scripts/ingest_seed.py

# Crawl ESCO via the live EU REST API at build time so the container starts fast.
# If the build host has no internet (or the EU API is down), continue anyway —
# the container can still serve everything except Skills extract.
RUN python scripts/ingest_esco.py || echo "[warn] ESCO crawl skipped at build time"

# Tell our config loader exactly where packs live (defensive override).
ENV PACKS_DIR=/app/packs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
