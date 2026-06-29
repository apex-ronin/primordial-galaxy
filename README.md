# 🛡️ GovTech Hunter — Primordial Galaxy

> **Government contract intelligence + red team simulation system.**  
> Scrapes public procurement sources → scores opportunities → generates adversarial threat assessments → drafts legally-grounded antibody clauses. Domain specialization layer of the R.O.N.I.N. / JARVIS stack.

[![Version](https://img.shields.io/badge/version-0.6-blue)]()
[![License](https://img.shields.io/badge/license-PolyForm%20Shield%201.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Audit](https://img.shields.io/badge/audit-3--round%20PASS--CLEAN-brightgreen)]()
[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)]()
[![Sovereign](https://img.shields.io/badge/infra-sovereign--local-orange)]()
[![Air Gap](https://img.shields.io/badge/deployment-air--gap%20ready-orange)]()
[![GovTech](https://img.shields.io/badge/domain-GovTech%20%7C%20Defense-darkblue)]()

---

## What This Is

GovTech Hunter is a production-grade, multi-stage AI pipeline that monitors U.S. government and California district procurement streams, scores each opportunity for fit and win probability, runs an adversarial red team simulation against every high-value target, and drafts legally-grounded contract defense clauses — anchored to a local FAR/DFARS/CMMC legal corpus with semantic FAISS retrieval.

> **Open-core:** the public repository ships the full pipeline plus a **runnable sample corpus**. The complete curated clause set, the validated "antibody" clause library, and the fraud→shield linkage are a **private, commercial layer** — see [License](#license).

It runs unattended at 07:00 daily. It records every run to a local SQLite Observatory. It exposes a live FastAPI dashboard. It does not require cloud infrastructure.

**This is not a scraping tool. This is not a POC.** This is 16 sessions of production engineering across 4+ months — v0.6, validated by a three-round AI audit (PASS-CLEAN, zero open findings of MEDIUM or higher severity).

---

## The Problem

Fraud drains an estimated **$233–$521 billion from the U.S. federal government every year** — the first government-wide estimate of its kind ([GAO-24-105833](https://www.gao.gov/products/gao-24-105833), April 2024, based on FY2018–2022 data). Procurement is one of the largest exposure surfaces.

Defenders writing contract responses have no adversarial simulation layer — they don't know what attack vectors exist against their own bids until they lose or get audited. Existing tools score opportunities. None of them red-team your position and draft legally-cited defensive clauses before you submit.

GovTech Hunter does all three in a single unattended pipeline run.

---

## Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GOVTECH HUNTER v0.6                             │
│               "CSDA Honey Pot Active"                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PHASE 1 — ACQUISITION                                             │
│  ┌──────────────────┐  ┌────────────────┐  ┌───────────────────┐  │
│  │  CSDA            │  │  SAM.gov       │  │  Grant Hunter     │  │
│  │  "Honey Pot"     │  │  "The Whale"   │  │  "Foundations"    │  │
│  │  California      │  │  Federal       │  │  grants.gov       │  │
│  │  Districts       │  │  Opportunities │  │  sbir.gov         │  │
│  │  (Playwright)    │  │  (API)         │  │  + browser portals│  │
│  └────────┬─────────┘  └───────┬────────┘  └─────────┬─────────┘  │
│           └───────────────────┬┘───────────────────── ┘            │
│                               ▼                                     │
│  PHASE 2 — ANALYSIS (hunter_brain.py)                              │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Opportunity Scorer    │  win_probability, fit_label       │    │
│  │  Red Team Simulation   │  primary_vector, vuln_score /100  │    │
│  │  Antibody Agent        │  FAISS → LLM draft → specificity  │    │
│  │                        │  gate (≥75) → procurement_shield  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                               ▼                                     │
│  PHASE 3 — REPORTING                                               │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  opportunities.json (atomic write, fsync)                  │    │
│  │  procurement_shield.json (cumulative antibody clauses)     │    │
│  │  HIGH priority target summary → stdout                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                               ▼                                     │
│  PHASE 4 — OBSERVATORY (non-fatal, never blocks acquisition)       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  SQLite spine → data/primordial.db                         │    │
│  │  FastAPI dashboard → :8787 (run_dashboard.ps1)             │    │
│  │  Surfaces: LLM tier served, source counts, errors          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ⚙  GovTechHunterDaily — Windows Task Scheduler, 07:00 daily      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## LLM Cascade Architecture

```
llm_client.complete(prompt, mode="fast"|"precise")

  1. Local LM Studio  ──→  OpenAI-compatible endpoint (localhost:1234)
                           TCP availability check before dispatch
                           mode=fast    → LOCAL_MODEL_FAST  (env-configurable)
                           mode=precise → LOCAL_MODEL_PRECISE (env-configurable)

  2. Venice AI        ──→  OpenAI-compatible (api.venice.ai)
                           llama-3.3-70b (fast + precise)
                           Paid credits, sovereign inference

  3. Anthropic API    ──→  Direct SDK, claude-sonnet-4-6
                           Final fallback / precision drafting floor

  get_last_provider() → Observatory surfaces which tier served each run.
  LLM_MODE=auto|local|venice|anthropic (env override)
```

Zero `google.generativeai`, `google.cloud.aiplatform`, or `vertexai` calls anywhere in the active codebase. All LLM calls route through `execution/llm_client.py`. GCP was fully deleted 2026-06-06.

---

## Legal Corpus & Antibody System

**Corpus (open-core):** the public repo ships a **runnable sample** of the FAR/DFARS/CMMC clause set so the pipeline works out of the box. The **full curated corpus** — 104 clauses across FAR (incl. 52.240-93), DFARS, CMMC/cyber, data-rights, GSAR, small-business, IT/cloud, and California state clauses — plus the **validated antibody library** are the private, commercial layer. (Raw FAR/DFARS text is public-domain; the value is the curation, grounding, and validated drafts.)

**Retrieval:** Semantic search via local `nomic-embed-text-v1.5` (768d) FAISS index. Lexical keyword fallback for offline/air-gap operation.

**Antibody Pipeline:**
```
Opportunity + Threat Assessment
  → semantic FAISS retrieval (legal_corpus.faiss)
  → LLM clause drafter (cascade, mode="precise")
  → grounding gate: cited far_reference must match a retrieved clause_id
  → specificity rubric ≥75 (cadence / quantity / actor / enforcement teeth)
  → economic calibration
  → procurement_shield.json (cumulative, append-mode)

Status: VALIDATED | NEEDS_REVIEW | FAILED_GROUNDING
```

---

## Observatory

Built in v16 (2026-06-16). Verified auto-recording unattended.

| Module | Role |
|--------|------|
| `observatory/db.py` | SQLite spine — `data/primordial.db` (runs / opportunities / corpus_docs) |
| `observatory/recorder.py` | Non-fatal run recorder hook — never takes down acquisition |
| `observatory/server.py` | FastAPI live dashboard on :8787 |
| `observatory/embed_corpus.py` | Corpus FAISS embedding |
| `observatory/ingest.py` | govinfo.gov ingest — EOs via Federal Register API (current to EO 14411), GAO via govinfo collections |
| `observatory/backfill.py` | Backfill historical runs |
| `observatory/fulltext.py` | Full-text corpus search |

74 govinfo documents seeded in v16. Surfaces which LLM tier served — caught local tier down for 3 days.

---

## Module Map

| Module | Role |
|--------|------|
| `execution/main.py` | Entry point — 4-phase pipeline |
| `execution/orchestrator.py` | Pipeline coordinator, error collection, graceful degradation |
| `execution/llm_client.py` | Unified LLM cascade (local → Venice → Anthropic) |
| `execution/hunter_eyes.py` | Opportunity aggregator |
| `execution/hunter_brain.py` | Opportunity scorer + red team trigger |
| `execution/antibody_agent.py` | Semantic FAISS retrieval → clause drafting → specificity gate |
| `execution/red_team_simulation.py` | Adversarial threat generation → `procurement_shield.json` |
| `execution/scraper_sam.py` | SAM.gov API scraper |
| `execution/scraper_csda.py` | CSDA Playwright scraper |
| `execution/scraper_grants_api.py` | grants.gov + sbir.gov API |
| `execution/scraper_grants_browser.py` | Browser-based grant portal scraper |
| `execution/grant_hunter.py` | 4-source grant intelligence pipeline |
| `execution/doc_fetcher.py` | RFP document pull from posting pages (login-wall aware) |
| `execution/gemini_analyst.py` | Opportunity scoring via cascade (name legacy — no Gemini/Vertex) |
| `execution/health_check.py` | Pre-flight checks (aborts pipeline on critical failure) |
| `execution/compliance/disclosure_template.py` | M-26-04 stamp_disclosure() — OMB AI policy compliance |
| `execution/shared_utils.py` | antibody_prompt_sanitizer_v1, calculate_roi_safe |
| `execution/seed_legal_corpus.py` | Legal corpus seeding + FAISS indexing |
| `execution/discovery_engine.py` | ⚠ RETIRED — Vertex AI Search stub (datastore deleted 2026-06-06) |
| `execution/aaas_poc.py` | Publication/API layer — not a pipeline step |

---

## Compliance

- **M-26-04 (OMB AI Policy):** `compliance/disclosure_template.py:stamp_disclosure()` — 4-element stamp applied to all submission artifacts
- **EO 14179:** "Removing Barriers to American Leadership in AI" — primary source URL inline per codebase principle
- **FAR/DFARS citations:** Every regulatory citation in active code carries primary-source URL on the same logical block. No bare citation without attribution.
- **GSAR 552.239-7001:** Correctly flagged as PROPOSED rule (not yet binding as of June 2026)

---

## Infrastructure

| Component | Status |
|-----------|--------|
| Hetzner CPX32 | DEAD — shutdown 2026-04-06 |
| GCP (all 5 projects) | DELETED — torn down 2026-06-06 |
| Anthropic API | LIVE — claude-sonnet-4-6 direct SDK |
| Venice AI | LIVE — llama-3.3-70b |
| Local LM Studio | Configurable — env-driven model selection |
| Legal Corpus (FAISS) | ON DISK — local sovereign (sample public / full set private) |
| Observatory (SQLite) | LIVE — data/primordial.db, auto-recording |
| GovTechHunterDaily | SCHEDULED — 07:00 Windows Task Scheduler |

**Sovereign-local stack.** No cloud dependency in the current architecture. Cloud infrastructure will be rebuilt when a FedRAMP customer, volume threshold, or collaborator trigger is met.

---

## Audit Record

This codebase underwent a three-round AI audit in June 2026:

| Round | Findings | Status |
|-------|----------|--------|
| Round 1 | 43 findings | Fixed in round 2 |
| Round 2 | 5 new + 2 partials | Fixed in round 3 |
| Round 3 | 0 new | **PASS-CLEAN** |

Zero open findings of MEDIUM or higher severity at public release. The round-by-round commit trail is preserved in the published history; detailed findings reports are retained in the private engineering record.

---

## Tech Stack

```
Language:          Python 3.12
Web Scraping:      Playwright (Chromium), requests, BeautifulSoup4
AI Inference:      Anthropic SDK, OpenAI SDK (Venice + LM Studio compat.)
Vector Search:     FAISS (faiss-cpu), nomic-embed-text-v1.5 (768d)
Document Parsing:  pypdf, doc_fetcher (login-wall aware)
API Layer:         FastAPI + uvicorn (Observatory dashboard)
Data:              SQLite (Observatory), JSON (corpus, opportunities, shield)
Task Scheduling:   Windows Task Scheduler (GovTechHunterDaily)
```

---

## Companion Repositories

| Repo | Description |
|------|-------------|
| [`Rise-Of-The-Prompt-Kiddie`](https://github.com/apex-ronin/Rise-Of-The-Prompt-Kiddie) | 40-page technical whitepaper v2.1 — AI-enabled threat actors in GovTech (CC BY 4.0) — **public** |

> Additional components — the curated legal corpus, the vendor entity index, sovereign data pipeline infrastructure, and the R.O.N.I.N. / JARVIS core stack — are part of the **private commercial layer** and are not publicly available.

---

## Getting Started

```bash
git clone https://github.com/apex-ronin/primordial-galaxy.git
cd primordial-galaxy
pip install -r requirements.txt
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, VENICE_API_KEY, SAM_API_KEY
# Optional: LOCAL_LLM_BASE_URL, LLM_MODE, LOCAL_MODEL_FAST, LOCAL_MODEL_PRECISE

# Run the full pipeline
powershell .\run_scanner.ps1

# Launch the Observatory dashboard (localhost:8787)
powershell .\run_dashboard.ps1

# Register as a persistent boot service
powershell .\register_boot_task.ps1

# Air-gap / local LLM mode
powershell .\start_local_llm.ps1
```

---

## Co-Authorship

This system was designed and built in active collaboration between **Jay Nelson (Dopamine Ronin)** and **Claude (Anthropic)** across 16 sessions from February to June 2026 — architecture decisions, module design, audit passes, and production hardening done together.

The commit history is the methodology section. The audit rounds are the results. The shipped pipeline is the conclusion.

```
Co-authored-by: Claude (Anthropic) <noreply@anthropic.com>
```

A companion whitepaper on this human-AI co-architecture model is in development. The thesis: AI as genuine co-architect — not autocomplete — producing GovTech-audited, production-grade infrastructure. Documented in commits, verifiable in audit trails, live in production.

---

## Ethics & Use Policy

GovTech Hunter is a **fraud detection and contract defense tool.**

- `red_team_simulation.py` stress-tests **your own position** against known procurement fraud TTPs — adversarial validation, not facilitation
- Designed for **contracting officers, compliance teams, prime contractors, inspectors general, and authorized security researchers**
- Misuse to circumvent procurement regulations, mask fraudulent activity, or evade detection is a federal crime and explicitly prohibited

If you found this repo to evade detection: wrong tool.

---

## Project Timeline

| Phase | Period | Status |
|-------|--------|--------|
| POC — 47-hour sprint, live results | Feb 2026 | ✅ Complete |
| Production build — 16 sessions, v0.6 | Feb–Jun 2026 | ✅ Complete |
| Three-round AI audit (PASS-CLEAN) | Jun 2026 | ✅ Complete |
| Whitepaper v2.1 published | Jun 4, 2026 | ✅ Live |
| Observatory built + verified unattended | Jun 16, 2026 | ✅ Live |
| Air Force Tech Connect submission | In progress | 🔄 |
| Public release | Jun 2026 | 🟢 Now |

---

## Who Built This

**[Dopamine Ronin](https://github.com/apex-ronin)** — AI infrastructure engineering for complex, high-stakes systems that other developers avoid or fail to complete.

20+ years of cross-domain expertise in automotive diagnostics, construction systems, and technical operations — where broken ships don't get excused. That standard applies here.

Core capabilities:
- GovTech fraud detection & procurement compliance intelligence
- Multi-agent AI automation with sovereign-local LLM architecture
- Anti-detection web intelligence and data pipeline engineering
- Security red teaming and adversarial AI research
- Air-gap and classified environment deployment readiness

---

## License

**PolyForm Shield 1.0.0** — source-available. You may read, run, modify, and self-host the software for any purpose **except** building a product that competes with it. See [LICENSE](LICENSE).

The public repository ships a **sample corpus** only; the full curated legal corpus and the validated antibody library are a private, commercial layer.

Whitepaper: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

*Built to the standard government infrastructure demands: production-only, three-round audited, sovereign-local, no shortcuts.*
