# PRIMORDIAL GALAXY — Roadmap

**Owner:** Jay Nelson | **Updated:** 2026-04-04 | **Session:** v11

---

## STATUS

Core pipeline complete and Vertex-migrated. Blocked on LLC filing → domain → email chain.
Enterprise hardening (auth, HTTPS, RBAC) pending. No active server — Hetzner shutdown pending.

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
| Vertex AI migration | 183aec2 | gemini_analyst.py, red_team_simulation.py, antibody_agent.py — confirmed zero google.generativeai imports |
| antibody_agent.py built | 183aec2 | Corpus retrieval, Vertex drafting, specificity scoring (≥75 gate), economic calibration |
| Legal corpus seeded | a1f740a | 32 clauses: 24 FAR + 8 CA state in data/legal_corpus/ |
| Grant Hunter (Item 18) | 183aec2 | 4-source pipeline: grants.gov + sbir.gov + browser portals + seeds |
| GTG-1002 whitepaper preface | 183aec2 | directives/WHITEPAPER_PREFACE.md |
| OMB policy reference | 726440d | directives/OMB_AI_POLICY_REFERENCE.md — M-25-21/M-25-22 |
| SAM.gov API key rotated | — | 24hr blackout — new key needed from sam.gov |
| peer_review_package/ gitignored | 7741d6b | Contained exposed SAM API key — never committed |
| Roadmap system established | 7741d6b | This file is now the session SoT. directives/ files archived. |

---

## OPEN DECISIONS — RESOLVE NEXT SESSION

| # | Question | Blocks? |
|---|---|---|
| 1 | Partner decision — yes or no? If yes: operating agreement terms before LLC filing. | Blocks LLC |
| 2 | LLC filing — Arizona, Apex Ronin LLC. File once partner is resolved. | Blocks everything downstream |
| 3 | Oracle A1 — check GitHub Issues. Deadline April 8. Fire or cancel. | Infrastructure decision |
| 4 | New SAM.gov API key — retrieve from sam.gov and add to .env | Pipeline SAM source offline until done |

---

## SPEC GAPS (not bugs — backlog)

| Gap | File | Priority |
|---|---|---|
| Drafter uses Gemini Flash, spec calls for Claude Sonnet | `execution/antibody_agent.py` | Medium — fix before first enterprise client |
| Corpus retrieval is keyword-equality match, not semantic/TF-IDF | `execution/antibody_agent.py:_retrieve_relevant_clauses()` | Low — works for exact matches today |
| GEMINI_API_KEY still declared in red_team_simulation.py (unused noise) | `execution/red_team_simulation.py:15` | Low — cosmetic |

---

## EXECUTION ORDER — NEXT SESSION

1. Oracle A1 check — `gh issue list` on hunter repo. Fired = deploy. No = cancel April 8.
2. New SAM.gov API key — sam.gov → account → API keys → generate → add to `.env`
3. Partner decision → LLC filing (Arizona, AZ Corporation Commission, ~$50 online, same day)
4. Domain registration — `apexronin.com` (~$70-90/yr) + `apexronin.com` (~$15/yr) via Cloudflare Registrar
5. Google Workspace — Business Starter on apexronin.com, create jay@apexronin.com, verify MX
6. LinkedIn revamp — Apex Ronin brand, jay@apexronin.com contact, whitepaper teaser as Featured
7. Landing page — apexronin.com single page: headline, paragraph, whitepaper PDF, contact
8. Whitepaper placeholders — fill [Repository URL], [Docs URL], [Demo URL] once domain live
9. EID cold outreach — GTG-1002 hook + EID Threat Matrix, once LinkedIn + domain live

---

## SYSTEM STATE

| Component | Status | Notes |
|---|---|---|
| Hetzner CPX32 | SHUTDOWN PENDING | Oracle deadline April 8, then GCP migration |
| Dashboard | TAKEN DOWN | Rebuild on GCP with auth when enterprise-ready |
| Oracle A1 hunter | DEADLINE APRIL 8 | Check GitHub Issues. 4 days remaining. |
| Gemini pipeline | VERTEX MIGRATED ✅ | All 3 files confirmed — GSAR exposure closed |
| Legal corpus | LIVE — 32 clauses | Target 100+ for enterprise gate |
| Grant Hunter | COMPLETE ✅ | 4-source pipeline (Item 18) |
| antibody_agent.py | COMPLETE (spec gaps) | Vertex-migrated, corpus-loaded, scoring live |
| SAM.gov API key | ROTATED — 24hr BLACKOUT | New key needed before pipeline runs |
| apexronin.com domain | NOT REGISTERED | Blocked on LLC |
| LLC (Apex Ronin LLC Arizona) | DECISION LOCKED, NOT FILED | File this session |
| EID outreach | READY | Waiting on domain + LinkedIn |
| Scott Nelson | NOT CONTACTED | Zero contact until enterprise-ready |

---

## WHAT NOT TO DO

- Do not contact Scott Nelson until all 3 enterprise gates cleared (see APEX_RONIN_FUNCTIONAL_ROADMAP.md)
- Do not register domain before LLC name confirmed
- Do not reintroduce direct `google.generativeai` calls — Vertex only
- Do not commit `peer_review_package/` — gitignored, contains legacy data files
- Do not open Antigravity — confirmed unstable, caused data loss
- Do not start Unclaimed Funds — parked 90+ days minimum
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
