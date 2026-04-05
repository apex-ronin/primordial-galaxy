# Primordial Galaxy — CLAUDE.md

## What This Project Is

Government contract intelligence + red team simulation system.
Scrapes public procurement sources → analyzes via Vertex AI → generates red team threats + antibody clauses.
Domain specialization layer of R.O.N.I.N. / JARVIS.

## Session Protocol — FOLLOW EVERY SESSION

### Session Open (first 5 minutes)
1. Read `primordial_galaxy_roadmap.md` — load state, open decisions, execution order
2. Check hard deadlines (Oracle A1 April 8, SAM key status, etc.)
3. Start with item 1 from Execution Order — no context switching

### Session Close (mandatory before ending)
1. Update `primordial_galaxy_roadmap.md`:
   - Completed items → "What Is Complete" with commit hash
   - Open decisions → resolved or updated context
   - Rewrite Execution Order for next session
   - Update System State table
   - Add row to Session Log
2. `git add primordial_galaxy_roadmap.md && git commit -m "Session vN: roadmap updated"`
3. `git push` — session is not done until this succeeds

## Infrastructure

- **Server:** Hetzner CPX32 — `[REDACTED]` — SHUTDOWN PENDING
- **SSH:** `ssh -i ~/.ssh/hetzner_primordial root@[REDACTED]`
- **Dashboard:** TAKEN DOWN — rebuild on GCP with auth when enterprise-ready
- **GCP Project:** `govtech-control`
- **Service account:** `[REDACTED]`
- **Vertex datastore:** `govtechdata_1772540768925` (global region)
- **Key:** `/root/gcp-key.json` (server-side only — never commit)

## Key Modules

| File | Role |
|------|------|
| `execution/main.py` | Entry point — runs full pipeline |
| `execution/orchestrator.py` | Coordinates pipeline stages |
| `execution/discovery_engine.py` | Vertex AI search queries |
| `execution/scraper_sam.py` | SAM.gov scraper (API key in .env — check status) |
| `execution/scraper_eldorado.py` | Eldorado County scraper |
| `execution/scraper_csda.py` | CSDA scraper (Playwright) |
| `execution/gemini_analyst.py` | Opportunity scoring via Vertex AI |
| `execution/red_team_simulation.py` | Threat generation + antibody clauses via Vertex AI |
| `execution/antibody_agent.py` | Legal corpus retrieval + clause drafting + scoring |
| `execution/grant_hunter.py` | Grant intelligence — 4 sources ([REDACTED] contact = intentional) |
| `execution/shared_utils.py` | antibody_prompt_sanitizer_v1, calculate_roi_safe |
| `execution/aaas_poc.py` | **Publication layer only** — not a pipeline step |

## Antibody Agent (Item 24 — BUILT)

- File: `execution/antibody_agent.py` — exists and functional
- Pipeline: classifier → corpus retrieval → Vertex AI drafting → specificity gate (≥75) → economic calibration
- **Known spec gap:** drafter uses Gemini Flash, spec calls for Claude Sonnet
- **Known spec gap:** retrieval uses keyword-equality, not semantic search
- Interface: `antibody_agent.generate(opportunity, threat_assessment)`
- DO NOT inline into `red_team_simulation.py`

## Data Files (never commit)

- `data/opportunities.json` — overwritten each pipeline run
- `data/procurement_shield.json` — cumulative antibody clauses
- `data/legal_corpus/far_clauses.json` — 24 FAR clauses (committed via -f flag)
- `data/legal_corpus/state_clauses.json` — 8 CA state clauses (committed via -f flag)
- `data/saturation_status.json` — gitignored runtime artifact
- `peer_review_package/` — gitignored, do not commit

## Settled Decisions (do not re-litigate)

- `aaas_poc.py` is a publication/API layer only, not a pipeline step
- `grant_hunter.py` [REDACTED] contact is intentional internal intel
- pureswarm-node is retired — Hetzner is the active node (shutdown pending)
- 13 vs 22 opportunities = not a bug, main.py overwrites each run
- Vertex AI only — no direct `google.generativeai` calls anywhere
- Dashboard is DOWN — no auth = not enterprise, rebuild on GCP
- AaaS API cut until 5 paying clients
- CSDA membership = hard no, building own 90K entity database

## Git Safety Rules

- Never commit: `.env`, `gcp-key.json`, `data/saturation_status.json`, `peer_review_package/`, any PII
- `.gitignore` covers secrets — verify before any `git add .`
- Force-add corpus files when needed: `git add -f data/legal_corpus/`
- See `directives/git_publication_safety.md` for full policy

## Source of Truth Files

- **This session:** `primordial_galaxy_roadmap.md` (project root)
- **Cross-project:** `C:\Users\Jnel9\Workspaces\APEX_RONIN_FUNCTIONAL_ROADMAP.md`
- **directives/ files:** ARCHIVED — historical reference only

## Model Preferences

- Vertex AI (Gemini Flash): classification, scoring, bulk analysis
- Claude Sonnet via Vertex: legal-precision drafting (antibody clauses) — spec, not yet implemented
