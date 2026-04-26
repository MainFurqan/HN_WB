from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .country_pack import list_packs, load_pack
from .routers import skills, readiness, opportunities, policy

app = FastAPI(title="UNMAPPED API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
