# PRIMORDIAL GALAXY — Roadmap

**Owner:** Jay Nelson | **Updated:** 2026-06-03 | **Session:** v12

---

## STATUS

Core pipeline complete, Vertex-migrated, legal corpus at 104 clauses, antibody drafter on Claude Sonnet.
Active work: whitepaper publish → grant scanner scheduling → dashboard → outreach.
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
| antibody_agent.py built | 183aec2 | Corpus retrieval, Vertex drafting, specificity scoring (≥75 gate), economic calibration |
| Legal corpus seeded | a1f740a | Originally 32 clauses; expanded to 104 (25 FAR + 8 CA + CMMC/cyber/data-rights/GSAR domains) |
| Grant Hunter (Item 18) | 183aec2 | 4-source pipeline: grants.gov + sbir.gov + browser portals + seeds |
| GTG-1002 whitepaper preface | 183aec2 | directives/WHITEPAPER_PREFACE.md |
| OMB policy reference | 726440d | directives/OMB_AI_POLICY_REFERENCE.md — M-25-21/M-25-22 |
| SAM.gov API key rotated + live | — | Verified live 2026-04-14 |
| peer_review_package/ gitignored | 7741d6b | Contained exposed SAM API key — never committed |
| Roadmap system established | 7741d6b | This file is session SoT. directives/ files archived. |
| Legal corpus expanded to 104 | 1d7816b | 6 new domain files: cmmc, cyber, data-rights, small-biz, IT-cloud, GSAR |
| Corpus ingested to Vertex | 1d7816b | 104 docs ingested, datastore purged of 6 orphans, pristine |
| Antibody drafter → Claude Sonnet | 1d7816b | Swapped from Gemini Flash to claude-sonnet-4-6 via Vertex (spec gap closed) |
| M-26-04 disclosure (item 6) | 1d7816b | Wedge injected to antibody prompt; superseded 2026-06-03 by stamp function |
| M-26-04 disclosure_template.py | — | `execution/compliance/disclosure_template.py` — canonical 4-element stamp_disclosure(). Replaces TTSI_SPEC_v2 runtime gate. |
| TTSI_SPEC_v2 reviewed + killed | — | Runtime gate was wrong layer for current scale. Disclosure is a human-review + stamp obligation. See Settled Decisions. |

---

## OPEN DECISIONS

| # | Question | Blocks? |
|---|---|---|
| 1 | LLC filing — deferred to post-revenue. Sole prop until first paying client. | Blocks domain/email but not pipeline or outreach |
| 2 | Whitepaper publish — 3 placeholder URLs are the only blocker. Fill GitHub repo URLs then publish. | Blocks prime contractor outreach |

---

## SPEC GAPS (backlog — not bugs)

| Gap | File | Priority |
|---|---|---|
| Corpus retrieval is keyword-equality match, not semantic/TF-IDF | `execution/antibody_agent.py:_retrieve_relevant_clauses()` | Low — works for exact matches today |
| Old M-26-04 wedge stub still in antibody_agent.py (lines 46–58) | `execution/antibody_agent.py` | Low — coexists harmlessly with stamp function; clean up before enterprise client |
| GEMINI_API_KEY still declared in red_team_simulation.py (unused) | `execution/red_team_simulation.py:15` | Low — cosmetic |

---

## EXECUTION ORDER — NEXT SESSION

1. **Whitepaper publish** — fill 3 placeholder GitHub URLs in `Rise_Of_The_Prompt_Kiddie.md`, push to jsnnlsn-prog/primordial-galaxy, publish
2. **Grant scanner scheduling** — `execution/grant_hunter.py` exists and works, not yet on a cron. Wire to Cloud Scheduler (3× daily or daily at minimum).
3. **Bug runs** — run full pipeline end-to-end, verify antibody agent on Claude Sonnet, verify corpus retrieval, check output quality
4. **Dashboard** — rebuild on GCP with auth when bug runs pass clean
5. **Prime contractor outreach** — once whitepaper is live and pipeline is clean

---

## SYSTEM STATE

| Component | Status | Notes |
|---|---|---|
| Hetzner CPX32 | DEAD | Shutdown verified 2026-04-06. No response. |
| GCP (govtech-control) | LIVE ✅ | Billing active, verified 2026-05-29 |
| Anthropic Pro subscription | LIVE ✅ | Restored 2026-06-02 |
| Gemini pipeline | VERTEX MIGRATED ✅ | All 3 files confirmed — zero google.generativeai imports |
| Legal corpus | LIVE — 104 clauses ✅ | Ingested to Vertex, datastore clean |
| Antibody drafter | CLAUDE SONNET ✅ | claude-sonnet-4-6 via Vertex (spec gap closed 2026-05-14) |
| Grant Hunter | COMPLETE ✅ | 4-source pipeline — NOT YET SCHEDULED on cron |
| M-26-04 compliance | STAMP FUNCTION ✅ | `compliance/disclosure_template.py:stamp_disclosure()` |
| SAM.gov API key | LIVE ✅ | Verified 2026-04-14 |
| Whitepaper | 99% DONE — BLOCKED | 3 placeholder URLs only. `Rise_Of_The_Prompt_Kiddie.md` |
| Dashboard | NOT REBUILT | Rebuild on GCP with auth after pipeline bug runs pass |
| LLC (Apex Ronin LLC Arizona) | DEFERRED | Post-revenue. Sole prop for now. |
| apexronin.com domain | NOT REGISTERED | Deferred with LLC |
| Scott Nelson | PERMANENTLY CLOSED | Own merit, own timeline. Do not contact. |

---

## WHAT NOT TO DO

- Do not contact Scott Nelson — permanently closed (2026-06-02). Own rodeo, own merit.
- Do not register domain before LLC name confirmed
- Do not reintroduce direct `google.generativeai` calls — Vertex only
- Do not commit `peer_review_package/` — gitignored, contains legacy data files
- Do not open Antigravity — confirmed unstable, caused data loss
- Do not start Unclaimed Funds — parked 90+ days minimum
- Do not build a runtime TTSI compliance gate — TTSI_SPEC_v2 reviewed and killed 2026-06-03. M-26-04 compliance is human-review + stamp at current scale. Use `compliance/disclosure_template.py:stamp_disclosure()` on submission artifacts.
- Do not relitigate: aaas_poc.py = publication layer only, [REDACTED] contact = intentional, 13 vs 22 opportunities = not a bug

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
