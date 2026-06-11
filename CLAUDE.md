# Primordial Galaxy — CLAUDE.md

## What This Project Is

Government contract intelligence + red team simulation system.
Scrapes public procurement sources → analyzes via a local LLM cascade (LM Studio → Venice → Anthropic) → generates red team threats + antibody clauses grounded in a local FAISS legal corpus.
Domain specialization layer of R.O.N.I.N. / JARVIS.

## Core Operating Principles
1. **Commander's Intent + Semantic Hard-Stops:** Never rely solely on `pytest` passing as proof of correctness. Understand the "why" of every task. Every task has Semantic Hard-Stops — if you hit one, STOP and ask the user.
2. **Trust but Verify:** No substantive commit ships without peer review. Do not blindly push without approval or spot check.
3. **Primary Source Inline:** Any regulatory citation (OMB, FAR, DFARS, etc.) MUST carry the primary source URL in a code comment on the same logical block. If you can't paste the URL, you can't cite the regulation.
4. **Tests Validate Behavior, Not Strings:** If a test asserts on a regulatory authority string (e.g. `assert authority == "EO 14179"`), the test is wrong and must be rewritten. Tests should validate observable behavior — log fields present, wrong-region calls rejected, correct artifact links. Pytest passing is necessary but not sufficient for "done."
5. **Surface, Don't Assume:** If something feels like a substantive choice rather than a mechanical step, STOP and ask. Interrupted is recoverable. Silent wrong assumption is not.

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

- **Server:** Hetzner CPX32 — DEAD. Shutdown verified 2026-04-06.
- **GCP:** ALL PROJECTS DELETED 2026-06-06. Clean slate. org `jsn-nlsn-org` retained.
- **Dashboard:** SUSPENDED — rebuild when cloud trigger fires (FedRAMP customer / volume / collaborator).
- **Inference:** Claude Sonnet via Anthropic API directly (no Vertex endpoint).
- **Legal corpus:** Source JSONs on disk at `data/legal_corpus/` — 104 clauses, 8 files. Ground truth.
- **Vertex datastore:** DELETED with govtech-control. Google Discovery source retired 2026-06-10 — `discovery_engine.py` is a no-op stub and the google-cloud deps were dropped.
- **Retrieval:** local nomic-embed FAISS indexes at `G:\AI-Models\indexes` (legal_corpus 104 clauses, principalities 78k). Embedder served by LM Studio.

## Key Modules

| File | Role |
|------|------|
| `execution/main.py` | Entry point — runs full pipeline |
| `execution/orchestrator.py` | Coordinates pipeline stages |
| `execution/discovery_engine.py` | RETIRED 2026-06-10 — Vertex AI Search no-op stub (datastore deleted) |
| `execution/scraper_sam.py` | SAM.gov scraper (API key in .env — check status) |
| `execution/scraper_eldorado.py` | Eldorado County scraper |
| `execution/scraper_csda.py` | CSDA scraper (Playwright) |
| `execution/gemini_analyst.py` | Opportunity scoring via local LLM cascade (name is legacy — no Gemini/Vertex) |
| `execution/red_team_simulation.py` | Threat generation + antibody clauses via LLM cascade; appends to `data/procurement_shield.json` |
| `execution/antibody_agent.py` | Semantic FAISS legal-corpus retrieval + clause drafting (cascade) + grounded specificity scoring |
| `execution/grant_hunter.py` | Grant intelligence — seeds + REST APIs + browser (Vertex gap-filler retired 2026-06-10) |
| `execution/shared_utils.py` | antibody_prompt_sanitizer_v1, calculate_roi_safe |
| `execution/aaas_poc.py` | **Publication layer only** — not a pipeline step |

## Antibody Agent (Item 24 — BUILT)

- File: `execution/antibody_agent.py` — exists and functional
- Pipeline: semantic FAISS retrieval → clause drafting (LLM cascade) → grounded specificity gate → economic calibration
- **Drafter:** local LLM cascade (LM Studio qwen3 → Venice → Anthropic) via `llm_client.complete(mode="precise")`
- **Retrieval:** semantic search over local nomic-embed FAISS index (`G:\AI-Models\indexes\legal_corpus.faiss`, mirrors ronin `prism_tools`); lexical keyword match retained as offline fallback (semantic rewire 2026-06-10)
- **Validation:** `VALIDATED` requires grounding (cited far_reference matches a retrieved clause id) AND a specificity rubric score ≥75 (cadence / quantity / actor / enforcement teeth) — not verbosity (2026-06-10)
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
- No direct `google.generativeai` calls anywhere — Anthropic API for drafting, local corpus for retrieval
- Dashboard SUSPENDED — rebuild when cloud trigger fires
- AaaS API cut until 5 paying clients
- CSDA membership = hard no, building own 90K entity database

## Git Safety Rules

- Never commit: `.env`, `gcp-key.json`, `data/saturation_status.json`, `peer_review_package/`, any PII
- `.gitignore` covers secrets — verify before any `git add .`
- Force-add corpus files when needed: `git add -f data/legal_corpus/`
- See `directives/git_publication_safety.md` for full policy

## Source of Truth Files

- **This session:** `primordial_galaxy_roadmap.md` (project root)
- **Cross-project:** `C:\Users\jnel9\OneDrive\Workspaces\APEX_RONIN_FUNCTIONAL_ROADMAP.md` — synced to STATE.md 2026-06-06
- **directives/ files:** ARCHIVED — historical reference only

## Model Preferences

Local-primary cascade (post-GCP teardown 2026-06-06 — no Vertex/Gemini anywhere):
- **Triage / classification / scoring:** local `qwen3-8b` via LM Studio (`llm_client.complete(mode="fast")`)
- **Legal-precision drafting (antibody clauses):** cascade `mode="precise"` — local → Venice (llama-3.3-70b) → Anthropic API
- **Retrieval embeddings:** `nomic-embed-text-v1.5` (768d) via LM Studio, indexed in local FAISS (`G:\AI-Models\indexes`)
