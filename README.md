# Primordial Galaxy

> Production-grade government contract intelligence and Red Team simulation platform.
> Discovers RFPs, scores strategic fit, simulates attacker ROI, and generates defensive legal clauses ("Antibodies") that make AI-enabled procurement fraud economically unviable.

---

## Core Philosophy

**Security through Saturation** — rather than hiding vulnerabilities, this system surfaces them, models attacker economics, and generates protective RFP clauses that raise the cost of fraud above the value of the contract. See [directives/saturation_philosophy.md](directives/saturation_philosophy.md) for the full framework.

---

## Architecture

The stack is **sovereign-local**. All LLM inference runs through a local-primary
cascade — no cloud AI dependency, no GCP, no Vertex, no Gemini.

```
LLM cascade (execution/llm_client.py)
  1. Local LM Studio   (Qwen3-8b on RAZZOR-FACCE, free/instant, OpenAI-compatible)
  2. Venice AI         (paid credits, OpenAI-compatible)
  3. Anthropic API     (claude-sonnet-4-6, direct SDK)
  → set LLM_MODE in .env to pin a tier; default is the full auto cascade.

Retrieval: local nomic-embed FAISS over the legal corpus (no cloud vector search).

Layer 1 — Directives (directives/)   strategy, SOPs, philosophy (mostly ARCHIVED)
Layer 2 — Orchestration (execution/orchestrator.py)   retry, timeout, threading
Layer 3 — Execution (execution/)   Acquisition → Analysis → Red Team → Publication
```

> **History note:** Earlier eras of this project ran on Hetzner + GCP (Vertex AI /
> Discovery Engine / Gemini). All of that was torn down 2026-06-06. Any document
> still describing that infrastructure as live is archived under `_ARCHIVE/` or
> `directives/` and is **historical only**. Ground truth is `STATE.md` + `CLAUDE.md`.

---

## System Components

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `execution/main.py` | Full pipeline orchestration | `python execution/main.py` |
| `execution/orchestrator.py` | Retry/timeout wrapper for all modules | `Orchestrator.run_module()` |
| `execution/llm_client.py` | Local→Venice→Anthropic LLM cascade | `complete(prompt, mode=...)` |
| `execution/scraper_csda.py` | CSDA Honey Pot (Playwright, CA special districts) | `fetch_csda_opportunities()` |
| `execution/scraper_sam.py` | SAM.gov federal contracts API | `fetch_federal_opportunities()` |
| `execution/grant_hunter.py` | NSF SBIR/STTR grant discovery | `fetch_grant_opportunities()` |
| `execution/discovery_engine.py` | **RETIRED** stub (was Vertex AI Search) | no-op, returns `[]` |
| `execution/hunter_brain.py` | PDF download + keyword scoring + win probability | `analyze_opportunity(opp)` |
| `execution/gemini_analyst.py` | Dual-track RFP analysis (white-hat + red-team + antibody). **Name is legacy** — body uses the cascade, no Gemini | `analyze_rfp(text)` |
| `execution/antibody_agent.py` | FAISS corpus retrieval + grounded antibody drafting + specificity rubric | `generate(opp, assessment)` |
| `execution/red_team_simulation.py` | Red team threat profiling + ROI inversion (via cascade) | `python execution/red_team_simulation.py` |
| `execution/aaas_poc.py` | PII anonymization for publication (AaaS, via cascade) | `create_anonymized_intelligence(finding)` |
| `execution/health_check.py` | System diagnostics (5 nodes) | `python execution/health_check.py` |
| `execution/shared_utils.py` | Prompt injection sanitizer, safe ROI calculator | `antibody_prompt_sanitizer_v1()`, `calculate_roi_safe()` |

---

## Data Flow (Start to Finish)

```
Phase 0: Pre-Flight
  health_check.py → 5 nodes: Anthropic API, SAM.gov, CSDA, Local Corpus, Local Embedder
                  → [PASS] / [WARN] / [CRITICAL] per node
                    (Local Corpus is the only critical node; the rest degrade gracefully)

Phase 1: Acquisition (parallel threads via orchestrator.py, 30s timeout each)
  scraper_csda.py  → CA special district RFPs (Playwright)
  scraper_sam.py   → Federal contracts (SAM.gov REST API)
  grant_hunter.py  → NSF SBIR/STTR grants
  (discovery_engine.py is retired — returns no results)
  └→ Consolidated opportunity set

Phase 2: Intelligence Analysis (per opportunity)
  hunter_brain.py    → PDF download + keyword scoring → win_probability, fit_label
  gemini_analyst.py  → Dual-track analysis via the LLM cascade:
    Part 1 (White Hat): strategic fit, remote_friendly, estimated_value
    Part 2 (Black Hat): vulnerability_score, primary_vector, exploit_scenario
    Part 3 (Antibody):  legally-binding clause to prevent the identified fraud vector
  shared_utils.py    → sanitize inputs, calculate safe ROI
  └→ Output: opportunities.json

Phase 3: Red Team Simulation (standalone, human-gated)
  red_team_simulation.py → for each opportunity:
    - parse actual contract value (estimated_value or 'value' field)
    - simulate attacker ROI (payout / 2% cost floor)
    - identify fraud vectors: outsourcing, phishing, billing abuse
    - draft antibody via antibody_agent (FAISS-grounded, specificity-scored)
    - MANDATORY HUMAN GATE: confirm before saving
  └→ Output: threat_assessment.json + data/procurement_shield.json

Phase 4: Publication (optional)
  aaas_poc.py → cascade-powered PII scrub (names, emails, budgets, systems)
  └→ Output: data/aaas_intelligence_brief.md (portfolio/whitepaper-safe)
```

---

## Prerequisites

- Python 3.12+
- [Playwright](https://playwright.dev/python/) with Chromium: `python -m playwright install --with-deps chromium`
- **LM Studio** running locally (Qwen3-8b, OpenAI-compatible endpoint) for the free primary tier — optional; the cascade falls back to Venice/Anthropic if it is down
- **Venice AI** API key (optional fallback tier)
- **Anthropic** API key (final fallback tier, `claude-sonnet-4-6`)
- **SAM.gov** API key

**`.env` file:**
```env
# LLM cascade (set LLM_MODE=auto for full fallback, or local|venice|anthropic to pin)
LLM_MODE=auto
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
VENICE_API_KEY=your_venice_key
ANTHROPIC_API_KEY=your_anthropic_key
# Data sources
SAM_API_KEY=your_sam_gov_key
```

There is **no** GCP project, service-account key, or Gemini key required. If you
find `gcp-key.json`, `GOOGLE_CLOUD_PROJECT`, or `GEMINI_API_KEY` referenced
anywhere, it is legacy — see `_ARCHIVE/` and `execution/_archive_vertex/`.

---

## Local Setup

```bash
git clone <repo>
cd primordial-galaxy
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
cp .env.example .env   # then fill in keys
```

---

## How to Run

### 1. Health Check (verify all nodes)
```bash
python execution/health_check.py
```
Checks 5 nodes: Anthropic API, SAM.gov, CSDA Honey Pot, Local Corpus (critical), Local Embedder (nomic via LM Studio).

### 2. Full Saturation Pipeline
```bash
python execution/main.py
```
Output: `opportunities.json` — scored and analyzed RFPs from all sources.

### 3. Red Team Simulation (run after main.py)
```bash
python execution/red_team_simulation.py
```
Requires `opportunities.json`. Human gate confirmation required before saving.
Output: `threat_assessment.json`, appends antibodies to `data/procurement_shield.json`.

### 4. Anonymize for Publication
```bash
python execution/aaas_poc.py
```
Output: `data/aaas_intelligence_brief.md` — PII-scrubbed intelligence brief.

---

## Scheduling

The daily scan runs locally via Windows Task Scheduler task **`GovTechHunterDaily`**,
which invokes `run_scanner.ps1` from this repo on `G:\`. No cloud node or always-on
server is involved.

---

## Output Files

| File | Created By | Contents |
|------|-----------|---------|
| `opportunities.json` | `main.py` | Scored RFPs with win_probability, fit_label, red_team findings |
| `threat_assessment.json` | `red_team_simulation.py` | Threat profiles with vulnerability_score, vector, roi_index, immune_system_antibody |
| `data/procurement_shield.json` | `red_team_simulation.py` | Cumulative antibody clauses from all red team runs |
| `data/aaas_intelligence_brief.md` | `aaas_poc.py` | PII-scrubbed case study (publication-safe) |
| `logs/error_patterns.json` | `orchestrator.py` | Last 100 API errors for pattern analysis |

(Runtime JSON outputs and `data/` are gitignored — never committed.)

---

## Regulatory Grounding

Antibody clauses and disclosures cite primary sources only (per `CLAUDE.md`
Principle 3). Current key citations: **OMB M-26-04** (implements **EO 14319**),
**FAR 52.240-93** (formerly 52.204-21, renumbered Feb 2026), and the renumbered
**DFARS 252.204-7020/7021** series. Every regulatory citation in code carries a
primary-source URL comment.

---

## Roadmap & Open Items

See [primordial_galaxy_roadmap.md](primordial_galaxy_roadmap.md) for the current session log and open items.
