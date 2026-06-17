# PRIMORDIAL GALAXY — Roadmap

**Owner:** Jay Nelson | **Updated:** 2026-06-16 | **Session:** v16

> Global cross-project ledger = `G:\Workspaces\STATE.md` (the old OneDrive
> APEX_RONIN_FUNCTIONAL_ROADMAP.md did not survive OneDrive retirement; STATE.md
> is now canonical for cross-project state).

---

## STATUS

Core pipeline complete + **Observatory (live observability) built and proven running unattended.** Whitepaper published (v2.1, 2026-06-04). GCP fully torn down (2026-06-06) — clean slate, local-primary architecture. Legal corpus on disk (104 clauses, 8 files). Daily scanner clean 06-14→06-16 (Venice-served).

**Two priorities for next session (front and center):**
1. **Fix the local LLM tier** — it's been DOWN 3 days. LM Studio server is logon-triggered, so the 07:00 scan runs with no local tier when Jay isn't logged in. Move it to a **boot** trigger. (Venice covers it, but it's costing credits + dropping antibody retrieval to keyword.)
2. **American-models-only scrub** — Jay's directive. VERIFY the regulatory basis against primary sources first (see Open Decisions), then swap the Chinese daily-driver `qwen3-8b` → an American model (gemma/llama).

**Then:** public-flip prep — surgical history scrub (keep history, Method A) + corpus open/closed decision + license + collaboration files. **Decision locked: keep git history (proof-of-work), invite collaboration openly.**
Scott Nelson engagement permanently closed — building on merit, own timeline.

---

## WHAT IS COMPLETE — DO NOT RELITIGATE

| Item | Commit | Notes |
|---|---|---|
| B-1: random seed entropy | 2a970a2 | `random.seed(int(time.time()))` in red_team_simulation.py |
| B-2: real ROI values | 2a970a2 | `parse_opportunity_value()` reads actual contract values |
| B-3: antibody collection loop | 2a970a2 | procurement_shield.json populated each run |
| B-4: budget guard before truncation | 2a970a2 | Guard fires on original input, not post-truncation |
| B-5: false AaaS proxy reference | 2a970a2 | csda_honey_pot.md updated |
| B-7: SSH -i flag | 2a970a2 | satellite_dashboard_ops.md corrected |
| B-8: grant_hunter PII exception | 2a970a2 | git_publication_safety.md updated |
| B-9: pureswarm refs in backlog | 2a970a2 | backlog_and_reminders.md updated |
| Vertex AI migration | 183aec2 | gemini_analyst.py, red_team_simulation.py, antibody_agent.py — zero google.generativeai imports |
| antibody_agent.py built | 183aec2 | Corpus retrieval, drafting (was Vertex; now direct Anthropic API cascade), specificity scoring (≥75 gate), economic calibration |
| Legal corpus seeded | a1f740a | Originally 32 clauses; expanded to 104 (25 FAR + 8 CA + CMMC/cyber/data-rights/GSAR domains) |
| Grant Hunter (Item 18) | 183aec2 | 4-source pipeline: grants.gov + sbir.gov + browser portals + seeds |
| GTG-1002 whitepaper preface | 183aec2 | directives/WHITEPAPER_PREFACE.md |
| OMB policy reference | 726440d | directives/OMB_AI_POLICY_REFERENCE.md — M-25-21/M-25-22 |
| SAM.gov API key rotated + live | — | Verified live 2026-04-14 |
| peer_review_package/ gitignored | 7741d6b | Contained exposed SAM API key — never committed |
| Roadmap system established | 7741d6b | This file is session SoT. directives/ files archived. |
| Legal corpus expanded to 104 | 1d7816b | 6 new domain files: cmmc, cyber, data-rights, small-biz, IT-cloud, GSAR |
| Corpus ingested to Vertex | 1d7816b | 104 docs ingested (HISTORICAL — Vertex datastore deleted in 2026-06-06 teardown; corpus now served by local nomic-embed FAISS) |
| Antibody drafter → Claude Sonnet | 1d7816b | Swapped from Gemini Flash to claude-sonnet-4-6 (Vertex stage later removed; now direct Anthropic API via llm_client cascade) |
| M-26-04 disclosure (item 6) | 1d7816b | Wedge injected to antibody prompt; superseded 2026-06-03 by stamp function |
| M-26-04 disclosure_template.py | — | `execution/compliance/disclosure_template.py` — canonical 4-element stamp_disclosure(). Replaces TTSI_SPEC_v2 runtime gate. |
| TTSI_SPEC_v2 reviewed + killed | — | Runtime gate was wrong layer for current scale. Disclosure is a human-review + stamp obligation. See Settled Decisions. |
| **Observatory — live dashboard + run recorder** | v16 (06-16) | `observatory/` pkg: SQLite spine (`data/primordial.db`: runs/opportunities/corpus_docs), FastAPI live dashboard (`run_dashboard.ps1`, :8787), non-fatal recorder hook in main.py. **Verified auto-recording unattended** (runs #2,#3). Surfaces which LLM tier served — caught local tier down 3 days. |
| **govinfo.gov research + ingest** | v16 (06-16) | `docs/GOVINFO_RESEARCH_2026-06-14.md` + `observatory/ingest.py`. EOs via Federal Register API (current to EO 14411), GAO via govinfo collections (historical archive). 74 docs seeded into corpus_docs. Sets up arc #4 (antibody ORACLE). |
| **Pre-public history audit (checklist)** | v16 (06-16) | `G:\Workspaces\GITHUB_PRE_PUBLIC_CHECKLIST.md` (reusable). Ran live: secrets CLEAN (no key ever in history); **PII BLOCKER** — [REDACTED] NSF contact in 7 historical commits + 4 tracked docs. Scrub staged (Method A), not executed. |

---

## OPEN DECISIONS

| # | Question | Blocks? |
|---|---|---|
| 1 | LLC filing — deferred to post-revenue. Sole prop until first paying client. | Does not block pipeline or outreach |
| 2 | ~~Whitepaper publish~~ | ✅ CLOSED — v2.1 live at apex-ronin/Rise-Of-The-Prompt-Kiddie (2026-06-04) |
| 3 | **Public-flip: GO in principle (Jay), but GATED on a clean scrub.** Current-files audit passed, but HISTORY is not clean ([REDACTED] PII). Decision: keep history → **Method A surgical scrub** (filter-repo, redact PII strings + drop 4 internal docs), NOT re-init. | Blocks flip until scrub done + checklist re-run zero-hits |
| 4 | **Legal corpus in the public repo — open / sample / closed?** Full 104-clause set is currently committed in primordial. Clause text is public law; the curation + vector tagging is the IP overlap with the private legal-corpus repo. Leaning: open it (it's defensive knowledge; moat is principalities + service, not clause tags). UNDECIDED. | Blocks flip — must decide what data ships public |
| 5 | **License** — permissive (MIT/Apache) vs noncommercial source-available (BSL/PolyForm). "See & run but don't commercialize" = noncommercial. UNDECIDED. | Blocks collaboration (collaborators need a license) |
| 6 | **American-models-only** — VERIFY the regulatory basis (is there a *binding* rule, or just EO 14179 pro-dominance + congressional urging on FAR/PRC?). Then swap qwen daily-driver. | Strategically sound for govtech regardless; verify before stating as compliance |

---

## SPEC GAPS (backlog — not bugs)

| Gap | File | Priority |
|---|---|---|
| ~~Corpus retrieval is keyword-equality match~~ | `execution/antibody_agent.py` | ✅ RESOLVED — semantic nomic-embed FAISS retrieval + grounding gate (branch `pipeline-hardening-2026-06-11` @ 813726d) |
| ~~Old M-26-04 wedge stub still in antibody_agent.py~~ | `execution/antibody_agent.py` | Verify on the hardening branch; superseded by grounding gate + stamp function |
| ~~GEMINI_API_KEY declared in red_team_simulation.py~~ | `execution/red_team_simulation.py` | ✅ RESOLVED — module rewired to llm_client cascade; Vertex imports + GEMINI_API_KEY removed (2026-06-11 legacy audit) |
| Drafter prompt does not request `actor`/`teeth` though the rubric scores them | `execution/antibody_agent.py` | Med — real outputs land at NEEDS_REVIEW until the drafter prompt asks for enforcement actor + consequence |

---

## EXECUTION ORDER — NEXT SESSION

1. **FRONT AND CENTER — fix the local LLM tier.** Down 3 days. Root cause: LM Studio server is **logon**-triggered (`LMStudioServerAtLogon`), so the 07:00 SYSTEM scan finds nothing listening when Jay isn't logged in. Move server+model autostart to a **boot** trigger (or a SYSTEM service) so the sovereign-local tier is live at 07:00 regardless of login. Verify: a 07:00 run shows `local=UP` on the dashboard.
2. **FRONT AND CENTER — American-models-only scrub.** (a) VERIFY primary sources: is there a *binding* rule requiring American models, or only EO 14179 (pro-dominance, not a mandate) + the Moolenaar FAR/PRC urging? Cite primary URLs per CLAUDE.md principle #3. (b) Swap the Chinese daily-driver `qwen3-8b` (and `qwen3.6-moe`) → American model (`gemma` is downloaded; or a Llama). Re-point `LOCAL_MODEL_FAST`/`LOCAL_MODEL_PRECISE` in `.env`. Note: embedder `nomic-embed` = US ✅, Venice `llama` = US ✅, Anthropic = US ✅; `hermes` base = Mistral (French).
3. **Public-flip prep** (gated, Jay-supervised) — execute the surgical scrub (`G:\Workspaces\_private\primordial-galaxy-internal\SCRUB_RUNBOOK.md`, Method A): redact [REDACTED] PII + drop 4 internal docs from history, re-run pre-public checklist → zero hits. THEN resolve corpus (open/sample/closed) + license, add collaboration files (README invite, CONTRIBUTING.md, LICENSE, CODE_OF_CONDUCT.md). Flip only when all green.
4. **Outreach** — two M-26-04 email drafts ready. Send after pipeline + flip settled.
5. **Arc #4 — antibody ORACLE** (when ready): Title 48 granule ingest → full-text fill → embed corpus_docs to FAISS → flip `embedded=1`. Needs a real `GOVINFO_API_KEY` in `.env` for bulk.

---

## SYSTEM STATE

| Component | Status | Notes |
|---|---|---|
| Hetzner CPX32 | DEAD | Shutdown verified 2026-04-06. |
| GCP — all 5 projects | DELETED ✅ | Torn down 2026-06-06. Clean slate. org jsn-nlsn-org retained. |
| Anthropic Pro subscription | LIVE ✅ | Restored 2026-06-02 |
| Inference layer | LOCAL — Claude via API | Vertex endpoints gone. Claude Sonnet via Anthropic API directly. |
| Legal corpus | ON DISK ✅ | 104 clauses, 8 source JSONs at `data/legal_corpus/`. Vertex datastore gone — source files are ground truth. |
| Antibody drafter | CLAUDE SONNET ✅ | claude-sonnet-4-6 via Anthropic API (Vertex endpoint deleted with project) |
| Vertex Discovery Engine | DEAD | Deleted with govtech-control. Bug 1 (Google Discovery 0 results) is now permanent until cloud rebuilt. |
| Grant Hunter | SCHEDULED ✅ | `GovTechHunterDaily` 07:00 daily. Clean runs 06-14→06-16. |
| Observatory (local) | LIVE ✅ | `observatory/` — SQLite + FastAPI dashboard (`run_dashboard.ps1`). Auto-records every run. Distinct from the old cloud HUD. |
| Local LLM tier | ⚠️ DOWN 3 days | LM Studio logon-triggered → not up at 07:00 SYSTEM scan. Venice covering. FIX = boot trigger (priority #1). |
| Models in stack | ⚠️ Chinese present | Daily-driver `qwen3-8b` + `qwen3.6-moe` = Chinese (Alibaba). `gemma`/`llama`/`anthropic`/`nomic-embed` = US. American-only scrub = priority #2. |
| M-26-04 compliance | STAMP FUNCTION ✅ | `compliance/disclosure_template.py:stamp_disclosure()` |
| SAM.gov API key | LIVE ✅ | Verified 2026-04-14. Rotation reminder ~2026-07-02. |
| Whitepaper | PUBLISHED ✅ | v2.1 live — apex-ronin/Rise-Of-The-Prompt-Kiddie (2026-06-04) |
| Cloud HUD (old) | SUSPENDED | The *cloud* dashboard — rebuild when cloud trigger fires. (Local Observatory above is the current observability surface.) |
| Brand | SETTLED ✅ | Sole operator. apexronin.com owned. apex-ronin GitHub org live. |
| LLC | DEFERRED | Post-revenue. Sole prop for now. |
| Scott Nelson | PERMANENTLY CLOSED | Own merit, own timeline. Do not contact. |

---

## WHAT NOT TO DO

- Do not contact Scott Nelson — permanently closed (2026-06-02). Own rodeo, own merit.
- Do not register domain before LLC name confirmed
- Do not reintroduce any `google.generativeai`, `google.cloud.aiplatform`, or `vertexai` calls — all LLM calls go through `execution/llm_client.py:complete()` (local → Venice → Anthropic cascade). Vertex/GCP are dead.
- Do not commit `peer_review_package/` — gitignored, contains legacy data files
- Do not open Antigravity — confirmed unstable, caused data loss
- Do not start Unclaimed Funds — parked 90+ days minimum
- Do not build a runtime TTSI compliance gate — TTSI_SPEC_v2 reviewed and killed 2026-06-03. M-26-04 compliance is human-review + stamp at current scale. Use `compliance/disclosure_template.py:stamp_disclosure()` on submission artifacts.
- Do not relitigate: aaas_poc.py = publication layer only, 13 vs 22 opportunities = not a bug. (NSF program-officer contact is now stripped from code → gitignored `.env`; do not re-hardcode.)

---

## SESSION LOG

| Session | Date | Key Actions | Commit |
|---|---|---|---|
| v1-v6 | 2026-02-05 to 2026-03-03 | Initial build, Hetzner deployment, Vertex migration v1 | various |
| v7 | 2026-03-23 | GTG-1002 realignment, Oracle hunter deployed | 1584b28 |
| v8 | 2026-03-31 | Grant Hunter rebuilt, R.O.N.I.N. integration mapped | 6c5b948 |
| v9 | 2026-04-01 | Planning meeting, B-1/B-2/B-3 fixed, antibody_agent built, corpus live | 2a970a2 |
| v10 | 2026-04-01 | Vertex migration complete, GTG-1002 preface, all decisions locked | 183aec2 |
| v11 | 2026-04-03-04 | Full audit, git cleanup, OMB doc recovered, roadmap system established | 7741d6b |
| handoff sprint | 2026-05-14 | Corpus 33→104, drafter→Claude Sonnet, corpus ingested, item6 complete, handoff package | 1d7816b |
| v12 | 2026-06-03 | TTSI_SPEC_v2 reviewed + killed; disclosure_template.py built; full roadmap audit + sync | — |
| v13 | 2026-06-10 | Handoff Items 3.1–3.4: AI-gate fix (>100-char silent keyword fallback root-caused — not an LLM outage), honest analysis_method tier label, diag scripts deleted, doc_fetcher.py document pull (login-wall aware). | — |
| v14 | 2026-06-11 | Sonnet legacy audit (43 findings) + fix pass: red_team_simulation.py & aaas_poc.py rewired Vertex/Gemini→cascade; disclosure_template.py model attribution fixed; README full rewrite; stale Vertex/Hetzner/Scott docs archived to `_ARCHIVE/`; dead Gemini/Vertex scripts → `_archive_vertex/`/`_archive_legacy/`; peer_review_package.zip untracked; FAR/oracle/whitepaper-preface fixes. | 46b72cf |
| v15 | 2026-06-12 | Audit round 2: 5 new findings (1 high/2 med/2 low) + 2 partials, fixed. Audit round 3: PASS-CLEAN, zero medium+ findings — 3-round loop converged. NSF program-officer PII final-stripped from all tracked files, `.env`-driven. Ready to flip working parts public on Jay's go. | 2b45872, 5b351c2 |
| v16 | 2026-06-16 | Built **Observatory** (SQLite spine + FastAPI live dashboard + non-fatal run recorder; verified auto-recording unattended). **govinfo.gov research + ingest** (74 corpus_docs seeded; EOs via Federal Register, GAO via govinfo). **Pre-public history audit** + reusable checklist — caught [REDACTED] PII in history (scrub staged Method A, not run). Decisions: keep git history (proof-of-work), invite collaboration openly, Conventional Commits. Surfaced: local tier down 3 days (logon-trigger) + Chinese daily-driver model. | _this session_ |
