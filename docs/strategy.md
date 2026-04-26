# UNMAPPED — Strategy & Build Plan

## Judging vector (from the brief)

| Strong submission criterion | Our commitment |
|---|---|
| Show the data | ≥2 econometric signals visible: ILOSTAT wage range + WDI sector growth, with source labels |
| Design for constraint | PWA, low-bandwidth mode, 6-inch screen first, offline JSON-LD Skills Passport |
| Demonstrate localizability with evidence | Live Country Pack swap PK ↔ GH during demo (no code change) |
| Be honest about limits | "What we don't know" panel on every score; calibration notes; uncertainty bounds |

## Country choices

- **Pakistan (PK)** — primary, live demo. South Asia, mixed urban informal + rural ag, en/ur UI.
- **Ghana (GH)** — contrast country. Sub-Saharan urban informal. Also home of brief's Amara persona. Maximum narrative leverage.

## Architecture

```
Next.js PWA (Tailwind, en/ur)
        │
FastAPI (Python 3.11)
  ├── Skills Signal Engine  (gpt-4o-mini → ESCO IDs → JSON-LD passport + QR)
  ├── AI Readiness Lens     (Frey-Osborne × LMIC discount + ESCO graph + Wittgenstein)
  ├── Opportunity Match     (ILOSTAT wage + WDI sector growth visible per opportunity)
  └── Policy aggregate      (NEET + skill-supply divergence)
        │
DuckDB (all data preloaded)
        │
Country Packs (YAML) — drives every country-specific behaviour
```

## Build plan (~24 hours)

| # | Task | Hours |
|---|---|---|
| 1 | Repo scaffold + skeleton (DONE) | 0–2 |
| 2 | Data ingestion (ESCO subset, Frey-Osborne, ILOSTAT, WDI, Wittgenstein, ITU) | 2–6 |
| 3 | Skills Signal Engine + Passport | 6–11 |
| 4 | AI Readiness Lens | 11–15 |
| 5 | Opportunity Match | 15–18 |
| 6 | Policymaker aggregate page | 18–20 |
| 7 | Localizability live-switch demo + bug-bash | 20–22 |
| 8 | Demo polish + record video backup + pitch | 22–24 |

## Hard scope cuts

Cut: voice input, W3C Verifiable Credential, PDF passport, auth, Urdu skill-label translation (UI strings only), live API calls during demo, full-blown policymaker dashboard.

## Demo flow (3 minutes)

1. Amara intro (30s) — read from brief, "she is unmapped"
2. Live Skills Signal Engine in PK (60s) — Urdu text describing phone-repair work + self-taught coding → Skills Passport with ESCO URIs
3. Readiness Lens (30s) — automation risk + durable + adjacent skills, with limits panel
4. Opportunity Match (30s) — wage range + sector growth visible
5. **The protocol moment (45s)** — swap `packs/PK.yaml` → `packs/GH.yaml`, refresh, app shifts to Ghana context
6. Close (15s) — "open infra, country packs are pull requests"
