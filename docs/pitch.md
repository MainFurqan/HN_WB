# UNMAPPED — 3-minute Pitch Script

## Pitch line (memorise this)

> "UNMAPPED is not an app. It is a protocol with two reference implementations.
> Watch — Pakistan, Urdu, Pakistani wages, Frey-Osborne discounted by ITU
> broadband. Now I change one YAML file. Same binary, Ghana, English/Twi,
> Ghanaian wages, different LMIC calibration. **Country Packs are pull
> requests.** Open infrastructure means anyone — government, NGO, training
> provider — can own their context without owning our codebase."

---

## Cold-open (0:00–0:25) — the Amara story

Read straight from the brief, no slides:

> "Her name is Amara. She is 22, lives outside Accra, holds a secondary school
> certificate. She speaks three languages, has been running a phone repair
> business since she was 17, taught herself basic coding from YouTube videos
> on a shared mobile connection. By any reasonable measure, Amara has skills.
> But no employer in her city knows she exists. To the formal economy, Amara
> is unmapped. **She is not the exception. She is the rule.**"

Pause. Then:

> "We're going to map her, in 90 seconds."

---

## Live demo flow (0:25–2:30)

### Step 1 — Skills Signal Engine (40s)

- Open http://localhost:3000
- Click "Map my skills" → lands on `/youth?country=PK`
- **Point out**: page is in Urdu, RTL, because Pakistan's Country Pack defaults to Urdu
- The textarea pre-fills with Amara's story (in Urdu placeholder)
- Hit "میری مہارتیں ڈھونڈیں" (Find my skills)
- ~3-4 seconds → confirm step appears with 5-6 ESCO-grounded skills, each with confidence + the exact phrase quoted from the input
- **Say**: "Notice the candidates are unchecked. The brief says Amara should *own* her passport — our AI proposes, she chooses."
- Tick the 4-5 skills that are clearly hers
- Hit "میری تیاری اور مواقع دیکھیں" (See my readiness and opportunities)

### Step 2 — Result page (50s)

The page renders:
- **Skills Passport** with QR code + JSON-LD viewer (open the JSON to show real ESCO URIs)
- **AI Readiness Lens**: "17% calibrated risk vs 40% Frey-Osborne base" — call out the calibration_notes line: "Frey-Osborne base = 0.40, Pakistan broadband 1.4/100, calibrated risk = 0.17"
- Adjacent skills as resilience pathways
- **Wittgenstein cohort chart** showing youth attainment 2020 → 2035
- **"What we don't know" panel** — read one bullet aloud. "We don't pretend to know what we don't know. Frey-Osborne is from 2013, EU labour structure. We discount by infrastructure but cannot capture informal-economy effects. We tell the user this."
- **Opportunities** — point to PKR wage range + WDI sector growth on the first card. "Two visible econometric signals per opportunity. Source labels visible. No buried numbers."

### Step 3 — THE PROTOCOL MOMENT (40s)

Click the country swap chip in the header: → 🇬🇭 Ghana.

- Page reloads. Same components. **English. Ghanaian wages. Different broadband. Different LMIC discount. Different opportunity sector mix.**
- Open `packs/PK.yaml` and `packs/GH.yaml` in a side window. Show: 30 lines each. No code.
- **Say**: "That was a YAML file. Not a feature flag, not an environment switch — a Country Pack. Anyone can write one for their country in an afternoon. We can ship Bangladesh, Kenya, Indonesia next week without touching the binary."

### Step 4 — Policymaker view (15s)

- Navigate to http://localhost:3000/policy?country=PK
- Show NEET, sector employment bars, cohort chart, divergence diagnostic
- "Same data layer, different audience. Dual interface, both grounded on ILOSTAT and WDI."

---

## Close (2:30–3:00)

> "600 million unmapped young people. ESCO is open. ILOSTAT is open. WDI is
> open. Wittgenstein is open. We made the connective tissue open. **Country
> Packs are pull requests.** First country deployment is one PR away.
> Thank you."

---

## What if the live demo fails

- **OpenAI rate-limit / outage**: We disk-cache LLM responses — replay kicks in transparently. The Amara extraction has been cached during pre-demo dry-run.
- **Backend crashes**: have the recorded video ready, switch to it.
- **Network down**: `npm run dev` and `uvicorn` both serve 100% locally — only the Skills Signal Engine needs OpenAI; everything else (Readiness, Opportunities, Policy) runs from local DuckDB.

---

## Recorded backup video (record this BEFORE the live demo)

OBS Studio → Window Capture → 1080p 30fps → record 3:00 going through the
exact script above. Save as `demo-backup.mp4` next to the pitch deck.

---

## What to say if a judge asks…

| Question | Answer |
|---|---|
| "Is this real data or mocked?" | Real. ESCO via live API crawl (1490 skills, 411 occupations cached). Frey-Osborne 2013 from the published appendix. ILOSTAT, WDI, Wittgenstein bundled snapshots — see `docs/data-sources.md` for citations. |
| "Why bundled snapshots, not live ingestion?" | Demo reliability. Live ingestion scripts are wired (`backend/scripts/ingest_wdi.py` works against the live World Bank API). Bundled snapshot guarantees the demo doesn't depend on upstream API health. |
| "How does the calibration work?" | Linear formula in `readiness.py`: `calibrated = base × (1 − discount_weight × digital_infra_gap)` where digital_infra_gap is 1 minus broadband saturation. Transparent, auditable, in the docstring and surfaced in the UI. |
| "How portable is the passport?" | JSON-LD with real ESCO URIs and ISO country codes. Ready to extend to W3C Verifiable Credential (signed). Production gap, not architecture gap. |
| "What's the next country pack?" | Bangladesh — South Asia rural-ag analog to PK urban-informal. Could ship in a day given the ILOSTAT + Wittgenstein data is the same shape. |
| "What about voice / low-literacy users?" | Cut for hackathon scope. Architecture supports it — `description` is just a string into the Skills Signal Engine; a Whisper transcription step plugs in cleanly. |
| "Why OpenAI not an open model?" | Hackathon speed. Production: self-host with vLLM + Llama-3.1-70B for cost floor; the grounding pattern (shortlist-first prompt) works with any instruction-tuned model. |
