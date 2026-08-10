# PRIMORDIAL GALAXY — Roadmap

**Owner:** Jay Nelson | **Updated:** 2026-08-10 | **Session:** v18

> Global cross-project ledger = `G:\Workspaces\STATE.md` (the old OneDrive
> APEX_RONIN_FUNCTIONAL_ROADMAP.md did not survive OneDrive retirement; STATE.md
> is now canonical for cross-project state).

---

## STATUS

Core pipeline complete + **Observatory (live observability) built and proven running unattended.** Whitepaper published (v2.1, 2026-06-04). GCP fully torn down (2026-06-06) — clean slate, local-primary architecture. Legal corpus on disk (104 clauses, 8 files). Daily scanner clean 06-14→06-16 (Venice-served).

**Public flip: DONE.** `apex-ronin/primordial-galaxy` is live and public, confirmed intact 2026-08-08 (README, license, docs, 31 commits — verified via direct fetch, nothing missing).

**Cloud-failover scanner: DONE, not a blocker.** v17 (above, written by a companion chat session without STATE.md/HANDOFF access) re-flagged the 3 mirror secrets and `workflow_dispatch` test as pending. **Both were actually completed 2026-08-05** — verified fresh this session (2026-08-10): `gh secret list -R jsnnlsn-prog/primordial-galaxy` shows all 3 secrets set 2026-08-05; `gh run list` shows the scheduled workflow green every day 08-05→08-10 except one transient GitHub-hosted-runner infra failure on 08-06 ("not acquired by Runner") that self-healed the next day — not a config problem. **Do not re-litigate this.**

**Real front-and-center items for next session** (from cross-referencing `G:\Workspaces\STATE.md` tail + `HANDOFF_2026-08-05.md`, none of which made it into v17):
1. **Embed the 1,060 `far_rfo` docs into FAISS.** `python -m observatory.embed_corpus` (venv python, repo root) — rebuilds the full `corpus_docs` index (1,788 rows: 678 far + 50 gao + 1,060 far_rfo), requires the local LM Studio daemon serving `nomic-embed-text-v1.5` on `:1234`. **Attempted this session, blocked:** the daemon would not start from this session (`lms.exe ls`/`server start` both timed out — "Timed out waiting for LM Studio daemon to start" — repeatedly). Confirmed independently: today's real 07:00 scheduled scan (`logs/scan_2026-08-10_0700.log`) ran entirely on Venice, zero local calls — so the local tier was actually down for the live scan too, not just unreachable from this session. This is the same logged-out/session gap the roadmap has flagged since 06-16; it has not been durably fixed despite multiple partial fixes (GPU split, boot-CPU profile, LMStudioServerAtLogon repoint). **Needs Jay to check the box directly** (is LM Studio actually running? did the service crash?) before the embed step can complete.
2. **🔴 Regulatory correction sweep.** STATE 2026-08-05: FAR 52.204-21 was **not** actually renumbered in the codified FAR — it's still live at HEAD on acquisition.gov. 52.240-93 is a separate RFO Part 40 class-deviation number (DHS 25-23 etc.); both are citable, dual-numbering era. The old flat "renumbered to 52.240-93" claim from the June audit propagated into repo docs, the curated legal corpus, and the whitepaper. Sweep to dual-numbering language — gated on Jay's review (compliance-adjacent).
3. `LMStudioServerAtBoot` still not registered — recurring gap across many sessions, needs Jay running `register_boot_task.ps1` from an elevated terminal (Claude is blocked from SYSTEM-persistence changes by design).
4. July catch-up backfill — SAM `postedFrom`/`postedTo` sweep of the ~06-30→08-04 window — never run.
5. Arc #6 "Heartland" Phase 1 spec (`ARC6_HEARTLAND_PLAN_2026-08-05.md`) — entity_procurement table + Midwest verifier job — not started.
6. **Air Force Tech Connect submission status unconfirmed.** Package is ready (`Outreach/AF_TECH_CONNECT_SUBMISSION_2026-08.md`), HANDOFF_2026-08-05.md lists it as a Jay action item ("Submit AF Tech Connect... Screenshot confirmation → STATE line"), but no STATE.md line confirms it was sent. **Ask Jay directly rather than assuming either way.**

Scott Nelson engagement permanently closed — building on merit, own timeline.

**Note for whoever picks up next (human or Code):** this file drifted from ground truth between v16 and v17 because a companion chat session updated it without reading `G:\Workspaces\STATE.md`'s tail or `HANDOFF_2026-08-05.md`. **Always check STATE.md's tail and the most recent HANDOFF_*.md before trusting this file's "front and center" section** — this file is a snapshot, STATE.md is append-only ground truth.

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
| Cloud-failover scanner secrets + workflow_dispatch test | — (08-05, verified 08-10) | All 3 mirror secrets set on `jsnnlsn-prog/primordial-galaxy` 2026-08-05; `workflow_dispatch` tested same day; schedule green 08-05→08-10 (one transient runner-infra blip 08-06, self-healed). |
| RFO-current FAR ingest module | dab4249 (08-10) | `observatory/ingest.py` `fetch_far_rfo()` — acquisition.gov FARHTML.zip, RFO-current text. Run live 08-05: 1,060 sections (parts 3/9/15/19/52) ingested. **Not yet embedded** — see priority #1 above. |
| Mirror-secrets sync script | 310bf27 (08-10) | `scripts/set_mirror_secrets.ps1` — pushes `.env` vars to `jsnnlsn-prog/primordial-galaxy` Actions secrets with name-mapping. Used to unblock the item above on 08-05. |

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

*(Public flip, American-models scrub, Arc #4 phases 1-4, and Scott Nelson are all CLOSED — see WHAT IS COMPLETE. Do not relitigate.)*

1. **FRONT AND CENTER — get the local LLM tier actually reachable.** Confirmed down for real on 2026-08-10 (today's live 07:00 scan ran 100% on Venice, zero local calls — `logs/scan_2026-08-10_0700.log`), and the daemon would not start from a Code session either (`lms.exe` timed out repeatedly). This is the same gap flagged 06-16, 06-20, 06-22, 06-25, 08-05 — partial fixes (GPU split, boot-CPU profile, logon repoint) have not durably closed it. Jay needs to check the box directly: is the LM Studio background service actually installed/running as a persistent service, or does it die between logons? Once confirmed up, run `python -m observatory.embed_corpus` (venv python) to embed the 1,060 pending `far_rfo` docs.
2. Register `LMStudioServerAtBoot` (Jay, elevated terminal — Claude is blocked from SYSTEM-persistence changes by design). Closes the logged-out 07:00 gap specifically for boot-CPU profile, independent of item 1.
3. Regulatory correction sweep — dual-numbering language for FAR 52.204-21 / 52.240-93 across repo docs, curated corpus, whitepaper. Gated on Jay's review.
4. July catch-up backfill — SAM `postedFrom`/`postedTo` sweep of ~06-30→08-04.
5. Confirm AF Tech Connect submission status with Jay directly; if not sent, package is ready at `Outreach/AF_TECH_CONNECT_SUBMISSION_2026-08.md`.
6. Arc #6 Heartland Phase 1 spec (`ARC6_HEARTLAND_PLAN_2026-08-05.md`) — entity_procurement table + Midwest verifier job.
7. Untracked scripts in `scripts/` awaiting a keep/delete call: `show_env_names.ps1` + `uncomment_venice.ps1` (one-off .env diagnostics, low future value), `verify_rfo_ingest.py` (docstring says "delete after review"), `probe_demolition.py` (unrelated one-off, proves long-tail thesis — may be worth keeping as documented evidence).

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
| Local LLM tier | ⚠️ DOWN (confirmed 08-10) | Daemon unreachable from Code session (repeated timeout) AND today's real 07:00 scan ran 100% on Venice — not just a session-access issue, actually down. Recurring gap since 06-16 despite partial fixes. FIX = Jay to check the box directly (priority #1). |
| Cloud-failover scanner (mirror) | LIVE ✅ | Secrets set + workflow_dispatch tested 08-05; schedule green 08-05→08-10 (1 self-healed runner blip 08-06). |
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
| v16 | 2026-06-16 | Built **Observatory** (SQLite spine + FastAPI live dashboard + non-fatal run recorder; verified auto-recording unattended). **govinfo.gov research + ingest** (74 corpus_docs seeded; EOs via Federal Register, GAO via govinfo). **Pre-public history audit** + reusable checklist — caught [REDACTED] PII in history (scrub staged Method A, not run). Decisions: keep git history (proof-of-work), invite collaboration openly, Conventional Commits. Surfaced: local tier down 3 days (logon-trigger) + Chinese daily-driver model. | — |
| v17 | 2026-08-09 (verified state as of 08-08/08-09, with Claude/chat — companion session, not this file's usual Code author) | **Confirmed public repo intact** (`apex-ronin/primordial-galaxy` live, 31 commits, nothing lost — false alarm about account being wiped, root cause was a bad web-search result compounded by exhaustion/no sleep). **Found + pulled** `scanner_daily.yml` (2 commits on `jsnnlsn/main`, private-mirror cloud-failover design, local rig crash under load was the driver) — local checkout was 2 behind, now fast-forwarded clean, zero conflicts. Confirmed remotes: `origin`=public, `jsnnlsn`=private mirror. Scan logs confirm pipeline ran unattended through 08-05 → 08-08 without intervention. **⚠️ CORRECTED IN v18: this session's "not yet done" list (secrets, workflow_dispatch) was wrong — both were already done 08-05, 4 days before this session, per STATE.md/HANDOFF_2026-08-05.md that this session didn't check.** | 82cad27 (pulled, not authored this session) |
| v18 | 2026-08-10 (Claude Code) | **Corrected v17's stale premise** by cross-referencing `STATE.md` tail + `HANDOFF_2026-08-05.md`: cloud-failover secrets + workflow_dispatch were already done 08-05, re-verified green through 08-10 (`gh secret list`, `gh run list`). **Committed** the RFO ingest module (`dab4249`) and the mirror-secrets sync script (`310bf27`), both previously uncommitted/untracked. **Attempted** the pending `far_rfo` FAISS embed step — blocked: LM Studio daemon unreachable from this session (repeated timeout), independently confirmed down for the real 07:00 scan too (100% Venice-served, `logs/scan_2026-08-10_0700.log`). **Surfaced 5 items STATE.md had that this file never carried:** the FAR 52.204-21 dual-numbering regulatory correction, `LMStudioServerAtBoot` still unregistered, July SAM backfill, Arc #6 Heartland Phase 1 spec, and unconfirmed AF Tech Connect submission status. 4 scripts (`show_env_names.ps1`, `uncomment_venice.ps1`, `verify_rfo_ingest.py`, `probe_demolition.py`) still untracked, left for Jay's keep/delete call. | dab4249, 310bf27 |
