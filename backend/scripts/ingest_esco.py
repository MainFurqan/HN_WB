"""Ingest ESCO skills + occupations via the public REST API (no auth).

The bulk-download zip on esco.ec.europa.eu is gated behind JS / paged downloads,
so we crawl the live REST search endpoint with a curated seed of LMIC-relevant
query terms. All URIs returned are real ESCO concepts.

Endpoint:
  https://ec.europa.eu/esco/api/search?type=skill|occupation&text=...&language=en

Storage:
  esco_skills(conceptUri, preferredLabel, description, altLabels, isco_hint)
  esco_occupations(conceptUri, preferredLabel, description, iscoGroup)

Total: ~1500-3000 unique skills covering common LMIC occupations.
"""
from __future__ import annotations
import duckdb
import httpx
import json
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "unmapped.duckdb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
CACHE = RAW / "esco_cache"

API = "https://ec.europa.eu/esco/api/search"

# Seed terms covering Pakistan + Ghana informal economies + youth-relevant work.
SKILL_SEEDS = [
    # Trades / informal economy
    "phone repair", "mobile device repair", "computer repair", "tv repair",
    "data entry", "customer service", "selling", "retail", "cooking", "tailoring",
    "sewing", "carpentry", "construction", "welding", "plumbing", "electrical",
    "agriculture", "farming", "irrigation", "livestock", "dairy", "poultry",
    "teaching", "tutoring", "childcare", "elderly care", "nursing", "first aid",
    "driving", "delivery", "logistics", "warehouse", "inventory",
    "accounting", "bookkeeping", "marketing", "social media", "graphic design",
    "photography", "video editing", "translation", "writing", "content creation",
    "machine operation", "textile", "garment", "embroidery",
    "hairdressing", "baking", "food preparation",
    "auto mechanic", "motorcycle repair", "battery", "solar installation",
    "domestic work", "cleaning", "security", "guarding",
    # Soft / transversal skills
    "communication", "team work", "problem solving", "leadership", "negotiation",
    "literacy", "numeracy", "critical thinking", "creativity", "time management",
    "presentation skills", "active listening", "adaptability", "empathy",
    "project management", "decision making", "conflict resolution",
    # Tech / CS / AI / data — added so the demo profile of a CS student / AI engineer
    # gets meaningful candidates in the LLM shortlist
    "computer programming", "software development", "web development",
    "Python programming", "JavaScript programming", "Java programming",
    "machine learning", "artificial intelligence", "deep learning",
    "neural networks", "natural language processing", "computer vision",
    "data science", "data analysis", "data visualisation", "statistical analysis",
    "SQL databases", "database design", "data engineering", "ETL pipelines",
    "cloud computing", "AWS", "Docker containers", "Kubernetes",
    "DevOps", "git version control", "REST APIs", "GraphQL",
    "front-end development", "back-end development", "full stack development",
    "React framework", "Node.js", "TypeScript", "mobile app development",
    "Android development", "iOS development",
    "cybersecurity", "network administration", "system administration",
    "Linux administration", "Microsoft Office", "Excel",
    "UI design", "UX design", "wireframing", "prototyping",
    "digital marketing", "search engine optimisation", "Google Ads",
    "research methods", "scientific writing", "academic research",
    "entrepreneurship", "business planning", "financial planning",
]

OCCUPATION_SEEDS = [
    # Trades / informal
    "mobile phone repair technician", "shop assistant",
    "tailor", "carpenter", "construction worker", "electrician", "plumber",
    "subsistence farmer", "crop farmer", "livestock farmer", "dairy farmer",
    "primary school teacher", "early childhood educator", "nursing assistant",
    "delivery driver", "taxi driver", "warehouse worker",
    "bookkeeper", "marketing assistant", "graphic designer", "translator",
    "garment machinist", "weaver", "embroiderer",
    "hairdresser", "baker", "cook",
    "auto mechanic", "motorcycle mechanic",
    "domestic cleaner", "security guard",
    # Tech / CS / AI / data
    "software developer", "software engineer", "web developer",
    "front-end developer", "back-end developer", "full stack developer",
    "data scientist", "data analyst", "data engineer",
    "machine learning engineer", "AI engineer", "research scientist",
    "DevOps engineer", "cloud architect", "systems administrator",
    "database administrator", "cybersecurity analyst", "QA engineer",
    "mobile application developer", "embedded systems engineer",
    "ICT business analyst", "product manager", "UX designer", "UI designer",
    "technical writer", "digital marketing specialist", "SEO specialist",
    "computer science teacher", "vocational instructor",
    "research assistant", "junior researcher",
]


def fetch(text: str, kind: str, limit: int = 30) -> list[dict]:
    cache_key = f"{kind}_{text.replace(' ', '_').lower()}.json"
    cache_path = CACHE / cache_key
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    for attempt in range(3):
        try:
            r = httpx.get(
                API,
                params={
                    "type": kind,
                    "text": text,
                    "language": "en",
                    "limit": limit,
                    "full": "false",
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("_embedded", {}).get("results", [])
            CACHE.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
            return results
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return []


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    skills_seen: dict[str, dict] = {}
    occs_seen: dict[str, dict] = {}

    print(f"Crawling {len(SKILL_SEEDS)} skill seeds...")
    for seed in SKILL_SEEDS:
        results = fetch(seed, "skill", limit=30)
        for r in results:
            uri = r.get("uri")
            if not uri or uri in skills_seen:
                continue
            preferred = (r.get("preferredLabel") or {}).get("en", r.get("title", ""))
            skills_seen[uri] = {
                "conceptUri": uri,
                "preferredLabel": preferred,
                "description": r.get("searchHit", "") or "",
                "altLabels": "",  # not in search results; would need /resource fetch per skill
                "isco_hint": "",
            }
        print(f"  {seed}: {len(results)} -> total unique skills: {len(skills_seen)}")
        time.sleep(0.1)

    print(f"\nCrawling {len(OCCUPATION_SEEDS)} occupation seeds...")
    for seed in OCCUPATION_SEEDS:
        results = fetch(seed, "occupation", limit=20)
        for r in results:
            uri = r.get("uri")
            if not uri or uri in occs_seen:
                continue
            preferred = (r.get("preferredLabel") or {}).get("en", r.get("title", ""))
            # iscoGroup may appear under broaderHierarchyConcept or via separate fetch.
            isco = ""
            for bh in r.get("broaderHierarchyConcept", []):
                # ESCO ISCO URIs end in 4-digit codes
                tail = bh.rsplit("/", 1)[-1]
                if tail.isdigit() and len(tail) == 4:
                    isco = tail
                    break
            occs_seen[uri] = {
                "conceptUri": uri,
                "preferredLabel": preferred,
                "description": r.get("searchHit", "") or "",
                "iscoGroup": isco,
            }
        print(f"  {seed}: {len(results)} -> total unique occupations: {len(occs_seen)}")
        time.sleep(0.1)

    con = duckdb.connect(str(DB))
    con.execute("""
        CREATE OR REPLACE TABLE esco_skills (
            conceptUri VARCHAR PRIMARY KEY,
            preferredLabel VARCHAR,
            description VARCHAR,
            altLabels VARCHAR,
            isco_hint VARCHAR
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE esco_occupations (
            conceptUri VARCHAR PRIMARY KEY,
            preferredLabel VARCHAR,
            description VARCHAR,
            iscoGroup VARCHAR
        )
    """)
    if skills_seen:
        con.executemany(
            "INSERT INTO esco_skills VALUES (?, ?, ?, ?, ?)",
            [(s["conceptUri"], s["preferredLabel"], s["description"], s["altLabels"], s["isco_hint"]) for s in skills_seen.values()],
        )
    if occs_seen:
        con.executemany(
            "INSERT INTO esco_occupations VALUES (?, ?, ?, ?)",
            [(o["conceptUri"], o["preferredLabel"], o["description"], o["iscoGroup"]) for o in occs_seen.values()],
        )
    print(f"\nESCO skills: {len(skills_seen)}    occupations: {len(occs_seen)}")
    con.close()


if __name__ == "__main__":
    main()
