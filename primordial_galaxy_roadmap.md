# PRIMORDIAL GALAXY — Roadmap

**Owner:** Jay Nelson | **Updated:** 2026-06-06 | **Session:** v13

---

## STATUS

Core pipeline complete. Whitepaper published (v2.1, 2026-06-04). GCP fully torn down (2026-06-06) — clean slate, local-primary architecture. Vertex Discovery Engine gone with govtech-control. Legal corpus source JSONs confirmed on disk (104 clauses, 8 files). Outreach gate cleared.
**Active work: grant scanner cron → outreach.**
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
| 1 | LLC filing — deferred to post-revenue. Sole prop until first paying client. | Does not block pipeline or outreach |
| 2 | ~~Whitepaper publish~~ | ✅ CLOSED — v2.1 live at apex-ronin/Rise-Of-The-Prompt-Kiddie (2026-06-04) |

---

## SPEC GAPS (backlog — not bugs)

| Gap | File | Priority |
|---|---|---|
| Corpus retrieval is keyword-equality match, not semantic/TF-IDF | `execution/antibody_agent.py:_retrieve_relevant_clauses()` | Low — works for exact matches today |
| Old M-26-04 wedge stub still in antibody_agent.py (lines 46–58) | `execution/antibody_agent.py` | Low — coexists harmlessly with stamp function; clean up before enterprise client |
| GEMINI_API_KEY still declared in red_team_simulation.py (unused) | `execution/red_team_simulation.py:15` | Low — cosmetic |

---

## EXECUTION ORDER — NEXT SESSION

1. **Grant scanner cron** — `execution/grant_hunter.py` exists and works, not scheduled. Wire to local Windows Task Scheduler or a simple scheduled script (Cloud Scheduler suspended — GCP torn down, local-primary until cloud trigger fires). Daily minimum.
2. **Fix bugs 1–4** — grants.gov API key (register at grantsolutions.gov) · sbir.gov URL update · CalOSBA URL verify · Google Discovery dead (govtech-control deleted — skip or stub until cloud rebuilt)
3. **Bug run** — full pipeline end-to-end post-fixes. Verify antibody agent on Claude Sonnet, corpus retrieval quality, output shape.
4. **Outreach** — two M-26-04 email drafts ready. Send after bug run confirms pipeline is clean.
5. **Dashboard** — rebuild after first paying client or when cloud trigger fires (FedRAMP customer / volume / collaborator).

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
| Grant Hunter | COMPLETE ✅ — NOT SCHEDULED | Pipeline works. Needs local cron. |
| M-26-04 compliance | STAMP FUNCTION ✅ | `compliance/disclosure_template.py:stamp_disclosure()` |
| SAM.gov API key | LIVE ✅ | Verified 2026-04-14 |
| Whitepaper | PUBLISHED ✅ | v2.1 live — apex-ronin/Rise-Of-The-Prompt-Kiddie (2026-06-04) |
| Dashboard | SUSPENDED | Rebuild when cloud trigger fires or first paying client. |
| Brand | SETTLED ✅ | Sole operator. apexronin.com owned. apex-ronin GitHub org live. |
| LLC | DEFERRED | Post-revenue. Sole prop for now. |
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
