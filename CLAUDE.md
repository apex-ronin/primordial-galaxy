# Primordial Galaxy — CLAUDE.md

## What This Project Is
Government contract intelligence + red team simulation system.
Scrapes public procurement sources → analyzes with Gemini → generates red team threats + antibody clauses → serves results on a live dashboard.

## Infrastructure
- **Server:** Hetzner CPX32 — `[REDACTED]` — Ubuntu 24.04, Helsinki
- **SSH:** `ssh -i ~/.ssh/hetzner_primordial root@[REDACTED]`
- **Dashboard:** `http://[REDACTED]:8080`
- **Server root:** `/root/` — contains `execution/`, `directives/`, `venv/`, `.env`, `gcp-key.json`
- **Activate venv on server:** `source /root/venv/bin/activate`

## GCP / APIs
- Project: `govtech-control`
- Service account: `[REDACTED]`
- Key: `/root/gcp-key.json` (server-side only — never commit)
- Vertex datastore: `govtechdata_1772540768925` (global region)
- Roles: Vertex AI User + Discovery Engine Viewer

## Key Modules
| File | Role |
|------|------|
| `execution/main.py` | Entry point — runs full pipeline |
| `execution/orchestrator.py` | Coordinates pipeline stages |
| `execution/discovery_engine.py` | Vertex AI search queries |
| `execution/scraper_sam.py` | SAM.gov scraper |
| `execution/scraper_eldorado.py` | Eldorado County scraper |
| `execution/scraper_csda.py` | CSDA scraper (Playwright) |
| `execution/gemini_analyst.py` | Gemini opportunity scoring |
| `execution/red_team_simulation.py` | Threat generation + antibody clauses |
| `execution/satellite_v1/satellite_server.py` | FastAPI dashboard server |
| `execution/aaas_poc.py` | **Publication layer only** — not a pipeline step |
| `execution/grant_hunter.py` | Grant intelligence ([REDACTED] contact = intentional) |
| `execution/shared_utils.py` | Shared helpers |

## Data Files (never commit)
- `data/opportunities.json` — overwritten each pipeline run (13 vs 22 count discrepancy = expected, not a bug)
- `data/procurement_shield.json` — antibody clauses output
- `data/saturation_status.json` — in `.gitignore`
- `data/error_patterns.json` — archived

## Settled Decisions (do not re-litigate)
- `aaas_poc.py` is a **publication/API layer**, not a pipeline step
- `grant_hunter.py` [REDACTED] contact is **intentional internal intel**
- pureswarm-node is **retired** — Hetzner is the active node
- 13 vs 22 opportunities: `main.py` overwrites `opportunities.json` each run — not a bug
- All Phase B bugs are fixed (see MEMORY.md for full list)

## Git Safety Rules
- Never commit: `.env`, `gcp-key.json`, `data/saturation_status.json`, any PII
- `.gitignore` covers secrets — verify before any `git add .`
- See `directives/git_publication_safety.md` for full policy

## Antibody Agent (Item 24 — future, not yet built)
- File: `execution/antibody_agent.py` (does not exist yet)
- **DO NOT inline into `red_team_simulation.py`**
- Pipeline: classifier → FAR corpus retrieval → Claude Sonnet clause drafter → specificity gate (≥75) → economic calibration gate
- Standalone: `antibody_agent.generate(opportunity, threat)`

## Current Priorities (as of 2026-03-05)
1. LinkedIn revamp (Item 22) — primary trust signal
2. Landing page (Item 23) — fills whitepaper URL placeholders
3. Fill whitepaper placeholders → export PDF (`peer_review_package.zip/documentation/`)
4. Cold outreach to EID with free Threat Matrix
5. Commit all pending untracked/modified files

## Model Preferences
- Gemini: fast classification, scoring, bulk analysis
- **Claude Sonnet: legal-precision drafting** (antibody clauses, contract language)
