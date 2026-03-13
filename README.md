# Primordial Galaxy

> Production-grade government contract intelligence and Red Team simulation platform.
> Discovers RFPs, scores strategic fit, simulates attacker ROI, and generates defensive legal clauses ("Antibodies") that make AI-enabled procurement fraud economically unviable.

---

## Core Philosophy

**Security through Saturation** — rather than hiding vulnerabilities, this system surfaces them, models attacker economics, and generates protective RFP clauses that raise the cost of fraud above the value of the contract. See [directives/saturation_philosophy.md](directives/saturation_philosophy.md) for the full framework.

---

## Architecture

```
Layer 1 — Directives (directives/)
  Strategy documents, SOPs, phase roadmap, philosophy

Layer 2 — Orchestration (execution/orchestrator.py)
  Retry logic, timeout guards, thread pooling, error tracking

Layer 3 — Execution (execution/)
  Acquisition → Analysis → Red Team → Publication
```

---

## System Components

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `execution/main.py` | Full pipeline orchestration | `python execution/main.py` |
| `execution/orchestrator.py` | Retry/timeout wrapper for all modules | `Orchestrator.run_module()` |
| `execution/scraper_csda.py` | CSDA Honey Pot (Playwright, CA special districts) | `fetch_csda_opportunities()` |
| `execution/scraper_sam.py` | SAM.gov federal contracts API | `fetch_federal_opportunities()` |
| `execution/discovery_engine.py` | Vertex AI Search (Google Cloud) | `search_vertex(query)` |
| `execution/grant_hunter.py` | NSF SBIR/STTR grant discovery | `fetch_grant_opportunities()` |
| `execution/hunter_brain.py` | PDF download + keyword scoring + win probability | `analyze_opportunity(opp)` |
| `execution/gemini_analyst.py` | Dual-track RFP analysis (white-hat + red-team + antibody) | `analyze_rfp(text)` |
| `execution/red_team_simulation.py` | Red team threat profiling + ROI inversion | `python execution/red_team_simulation.py` |
| `execution/aaas_poc.py` | PII anonymization for publication (AaaS) | `create_anonymized_intelligence(finding)` |
| `execution/health_check.py` | System diagnostics (4 nodes) | `python execution/health_check.py` |
| `execution/shared_utils.py` | Prompt injection sanitizer, safe ROI calculator | `antibody_prompt_sanitizer_v1()`, `calculate_roi_safe()` |
| `execution/satellite_v1/satellite_server.py` | FastAPI dashboard backend | `python execution/satellite_v1/satellite_server.py` |

---

## Data Flow (Start to Finish)

```
Phase 0: Pre-Flight
  health_check.py → tests Vertex AI, SAM.gov, Gemini, CSDA
                  → [PASS] / [FAIL] per node

Phase 1: Acquisition (parallel threads via orchestrator.py, 30s timeout each)
  scraper_csda.py     → CA special district RFPs (Playwright)
  scraper_sam.py      → Federal contracts (SAM.gov REST API)
  discovery_engine.py → Vertex AI Search (Google Cloud datastore)
  grant_hunter.py     → NSF SBIR/STTR grants
  └→ Consolidated: ~13-22 opportunities

Phase 2: Intelligence Analysis (per opportunity)
  hunter_brain.py     → PDF download + keyword scoring → win_probability, fit_label
  gemini_analyst.py   → Dual-track Gemini analysis:
    Part 1 (White Hat):  strategic fit, remote_friendly, estimated_value
    Part 2 (Black Hat):  vulnerability_score, primary_vector, exploit_scenario
    Part 3 (Antibody):   legally-binding clause to prevent identified fraud vector
  shared_utils.py     → sanitize inputs, calculate safe ROI
  └→ Output: opportunities.json

Phase 3: Red Team Simulation (standalone, human-gated)
  red_team_simulation.py → for each opportunity:
    - parse actual contract value (estimated_value or 'value' field)
    - simulate attacker ROI (payout / 2% cost floor)
    - identify fraud vectors: outsourcing, phishing, billing abuse
    - collect immune_system_antibody from assessment
    - MANDATORY HUMAN GATE: confirm before saving
  └→ Output: threat_assessment.json + data/procurement_shield.json

Phase 4: Publication (optional)
  aaas_poc.py → Gemini-powered PII scrub (names, emails, budgets, systems)
  └→ Output: data/aaas_intelligence_brief.md (portfolio/whitepaper-safe)

Dashboard (always-on, cloud)
  satellite_server.py → FastAPI on port 8080
    /            → dashboard.html (Orbital Command Center UI)
    /run         → triggers main.py as background process
    /status      → polls saturation_status.json
    /diagnostics → runs health_check.py
```

---

## Prerequisites

- Python 3.13+
- [Playwright](https://playwright.dev/python/) with Chromium: `python -m playwright install --with-deps chromium`
- Google Cloud project with Vertex AI Search datastore
- Gemini API key
- SAM.gov API key

**`.env` file** (copy from `.env.example`):
```env
GEMINI_API_KEY=your_gemini_key
GOOGLE_CLOUD_PROJECT=govtech-control
VERTEX_DATA_STORE_ID=govtechdata_1772540768925
VERTEX_LOCATION=global
SAM_API_KEY=your_sam_gov_key
```

For cloud deployment, also place `gcp-key.json` (service account key) in the project root.

---

## Local Setup

```bash
git clone <repo>
cd primordial-galaxy
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
cp .env.example .env
# Fill in .env with your API keys
```

---

## How to Run

### 1. Health Check (verify all nodes)
```bash
python execution/health_check.py
```
Expected: `[PASS]` for Vertex AI, SAM.gov, Gemini, CSDA Honey Pot.

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

### 5. Launch Dashboard (local)
```bash
python execution/satellite_v1/satellite_server.py
```
Visit `http://localhost:8080`.

---

## Cloud Operations (Hetzner)

**Node:** `primordial-galaxy` — CPX32 (4 vCPU, 8GB RAM, 160GB SSD), Helsinki

| Field | Value |
|-------|-------|
| Public IP | `[REDACTED]` |
| Dashboard | `http://[REDACTED]:8080` |
| OS | Ubuntu 24.04 |
| Provider | Hetzner Cloud |

### SSH Access
```bash
ssh -i ~/.ssh/hetzner_primordial root@[REDACTED]
```

### Start Dashboard (background process)
```bash
cd /root
nohup venv/bin/python3 execution/satellite_v1/satellite_server.py > satellite_server.log 2>&1 &
```

### Verify
Navigate to `http://[REDACTED]:8080` and click **Run Diagnostics** to confirm all 4 nodes are live.

---

## Output Files

| File | Created By | Contents |
|------|-----------|---------|
| `opportunities.json` | `main.py` | 13-22 scored RFPs with win_probability, fit_label, red_team findings |
| `threat_assessment.json` | `red_team_simulation.py` | Threat profiles with vulnerability_score, vector, roi_index, immune_system_antibody |
| `data/procurement_shield.json` | `red_team_simulation.py` | Cumulative antibody clauses from all red team runs |
| `data/aaas_intelligence_brief.md` | `aaas_poc.py` | PII-scrubbed case study (publication-safe) |
| `saturation_status.json` | `satellite_server.py` | Dashboard run status (not committed) |
| `logs/error_patterns.json` | `orchestrator.py` | Last 100 API errors for pattern analysis |

---

## GCP Configuration

- **Project:** `govtech-control`
- **Service account:** `[REDACTED]`
- **Key (on server):** `/root/gcp-key.json`
- **Vertex datastore:** `govtechdata_1772540768925` (location: global)
- **Roles:** Vertex AI User + Discovery Engine Viewer

---

## Roadmap & Open Items

See [directives/phase4_roadmap.md](directives/phase4_roadmap.md) for the full 23-item roadmap.

See [directives/functional_roadmap.md](directives/functional_roadmap.md) for the detailed program flow reference.

**Immediate priorities:**
1. LinkedIn revamp (trust signal for cold outreach)
2. Landing page (fills whitepaper URL placeholders)
3. Cold-email EID with free Threat Matrix → paid Red Team report ($2.5K–$10K)

---

## Session History

| Phase | Date | Key Outcome |
|-------|------|-------------|
| 3.5 | 2026-02 | Non-blocking Satellite-01 dashboard; CSDA Playwright scraper; orbital UI |
| 3.6 | 2026-03-03 | Migrated to Hetzner CPX32 (`[REDACTED]`); venv subprocess bug fixed |
| 4.0 Kickoff | 2026-03-04 | Full Phase B-E review; 3 critical bugs catalogued; phase4_roadmap.md written |
| 4.0 Session 1 | 2026-03-05 | B-1 (seed=42) fixed; B-8 (PII note) fixed; roadmap items 22-23 added |
| 4.0 Session 2 | 2026-03-05 | B-2, B-3, B-4 fixed; README rewrite; functional roadmap created |
