from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from ..services.skills_engine import extract_skills
from ..services.passport import build_passport, passport_qr_png_b64
from ..services.cv_parser import parse_cv_to_profile

router = APIRouter()

ACCEPTED_CV_EXTS = (".pdf", ".docx", ".txt", ".md")
MAX_CV_BYTES = 5 * 1024 * 1024  # 5 MB


class SkillsExtractRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=4000)
    education_level: str | None = Field(default=None, max_length=200)
    country: str = Field(default="PK", min_length=2, max_length=2)
    language: str = Field(default="en", min_length=2, max_length=5)


class SkillCandidate(BaseModel):
    esco_uri: str
    label: str
    confidence: float
    evidence_quote: str
    category: str = "hard"  # hard | soft | knowledge


class SkillsExtractResponse(BaseModel):
    candidates: list[SkillCandidate]
    isco_hint: str | None = None
    shortlist_size: int = 0


@router.post("/extract", response_model=SkillsExtractResponse)
def extract(req: SkillsExtractRequest) -> SkillsExtractResponse:
    out = extract_skills(req.description, country=req.country, language=req.language)
    candidates = []
    for s in out.get("skills", []):
        try:
            candidates.append(SkillCandidate(
                esco_uri=s.get("esco_uri", ""),
                label=s.get("label", ""),
                confidence=float(s.get("confidence", 0.0)),
                evidence_quote=str(s.get("evidence_quote", "") or ""),
                category=str(s.get("category", "hard") or "hard"),
            ))
        except Exception:
            continue
    return SkillsExtractResponse(
        candidates=candidates,
        isco_hint=out.get("isco_hint"),
        shortlist_size=out.get("shortlist_size", 0),
    )


class PassportRequest(BaseModel):
    confirmed_skill_uris: list[str]
    holder_name: str = "Anonymous"
    country: str = "PK"
    education_level: str | None = None
    isco_cluster: str | None = None
    share_url: str = "https://unmapped.dev/p/demo"


@router.post("/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    """Parse a PDF/DOCX/TXT CV and auto-fill the 6 profile sections."""
    name = (file.filename or "").lower()
    if not name.endswith(ACCEPTED_CV_EXTS):
        raise HTTPException(415, f"Unsupported file type. Accepted: {', '.join(ACCEPTED_CV_EXTS)}")
    data = await file.read()
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_CV_BYTES // 1024 // 1024} MB)")
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        profile = parse_cv_to_profile(name, data)
    except Exception as e:
        raise HTTPException(500, f"CV parsing failed: {e}")
    return profile


@router.post("/passport")
def passport(req: PassportRequest):
    p = build_passport(
        confirmed_skill_uris=req.confirmed_skill_uris,
        holder_name=req.holder_name,
        country=req.country,
        education_level=req.education_level,
        isco_cluster=req.isco_cluster,
    )
    qr = passport_qr_png_b64(p, req.share_url)
    return {"jsonld": p, "qr_png_b64": qr}
