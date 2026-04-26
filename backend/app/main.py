from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .country_pack import list_packs, load_pack
from .routers import skills, readiness, opportunities, policy

app = FastAPI(title="UNMAPPED API", version="0.1.0")

import os

# Local dev origins always allowed.
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Production origin(s) injected via env var, comma-separated.
# e.g. FRONTEND_ORIGIN=https://main.d338e8u1ypke1f.amplifyapp.com
_extra = os.environ.get("FRONTEND_ORIGIN", "")
if _extra:
    _ALLOWED_ORIGINS.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    # Also allow any Amplify preview branch (URLs look like https://branch.app-id.amplifyapp.com)
    allow_origin_regex=r"^https://[a-z0-9\-]+\.[a-z0-9]+\.amplifyapp\.com$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/packs")
def packs():
    return {"available": list_packs()}


@app.get("/packs/{code}")
def pack(code: str):
    return load_pack(code).model_dump()


app.include_router(skills.router, prefix="/skills", tags=["skills"])
app.include_router(readiness.router, prefix="/readiness", tags=["readiness"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(policy.router, prefix="/policy", tags=["policy"])
