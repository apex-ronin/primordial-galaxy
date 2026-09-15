import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from dotenv import load_dotenv
from hunter_eyes import fetch_opportunities
from hunter_brain import analyze_opportunity
from scraper_csda import fetch_csda_opportunities
from scraper_sam import fetch_federal_opportunities
from health_check import run_all_checks
from orchestrator import Orchestrator
from grant_hunter import fetch_grant_opportunities, promote_grant_fit

OUTPUT_FILE = "opportunities.json"

def main():
    load_dotenv()

    run_started_at = datetime.now().isoformat()

    print("="*60)
    print("GovTech Hunter v0.6 - CSDA Honey Pot Active")
    print("="*60)
    
    # 0. Pre-flight Health Check
    print("\n[0] Running Pre-flight Health Checks...")
    if not run_all_checks():
        print("\n[!!!] Critical health check failed — aborting. Fix the issue above and re-run.")
        sys.exit(1)

    orchestrator = Orchestrator()
    
    # 1. Execution Phase (Parallel-ish execution via Orchestrator)
    print("\n--- PHASE 1: ACQUISITION ---")
    
    # 🌟 NEW: CSDA (Honey Pot) - Central Hub for all California Districts
    results_csda_raw = orchestrator.run_module(
        "CSDA (Honey Pot)", 
        fetch_csda_opportunities
    )
    results_csda = results_csda_raw.get('data', [])
    
    # 🏮 DEPRECATED: El Dorado (Sniper) - single-district scraper superseded by the CSDA source
    # results_eldorado_raw = orchestrator.run_module(
    #     "El Dorado (Sniper)", 
    #     fetch_eldorado_opportunities
    # )
    # results_eldorado = results_eldorado_raw.get('data', [])
    results_eldorado = []
    
    results_sam_raw = orchestrator.run_module(
        "SAM.gov (The Whale)", 
        fetch_federal_opportunities
    )
    results_sam = results_sam_raw.get('data', [])

    # Google Discovery (Vertex AI Search) retired 2026-06-10 — datastore deleted
    # in the GCP teardown, no local equivalent. See execution/discovery_engine.py.

    # 1.5 Grant Hunter Market Prototype
    results_grants_raw = orchestrator.run_module(
        "Grant Hunter (Foundations)",
        fetch_grant_opportunities
    )
    results_grants = results_grants_raw.get('data', [])

    # Per-source counts for the observability run record (raw acquisition,
    # before scoring). Keyed by the module's display name.
    source_counts = {
        "CSDA (Honey Pot)": len(results_csda),
        "SAM.gov (The Whale)": len(results_sam),
        "Grant Hunter (Foundations)": len(results_grants),
    }

    # Consolidate
    all_opportunities = orchestrator.consolidate_results([
        results_csda,
        results_eldorado,
        results_sam,
        results_grants
    ])
    
    if not all_opportunities:
        print("\n[!] No opportunities found from any source (all failed or returned 0).")
        return

    # 2. Analysis Phase — delta-aware (Jay's directive, 2026-09-07): the
    # `opportunities` table already accumulates one row per link across every
    # run (first_seen preserved), so a link seen in any prior run gets its
    # stored score reused instead of paying for a fresh fetch + LLM call.
    # Every genuinely new link still gets fully analyzed AND has its raw
    # document text permanently archived (see hunter_brain.analyze_opportunity
    # -> observatory/archive.py), regardless of the score it lands on.
    print(f"\n--- PHASE 2: ANALYSIS ({len(all_opportunities)} items) ---")

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from observatory import db as obs_db
    obs_db.init_db()

    scored_opportunities = []
    new_count = reused_count = 0
    for opp in all_opportunities:
        link = opp.get('link')
        try:
            existing = None
            if link:
                with obs_db.session() as conn:
                    existing = obs_db.get_opportunity_by_link(conn, link)

            if existing and existing.get('raw_json'):
                # Note: analysis_method is left exactly as originally recorded
                # (reflects how it was actually scored) -- delta_status/first_seen
                # are separate fields instead of appending a tag onto
                # analysis_method, so re-reusing the same opportunity across many
                # future runs can't stack up repeated "[reused...]" text.
                scored_opp = json.loads(existing['raw_json'])
                scored_opp['delta_status'] = "reused"
                scored_opp['first_seen'] = existing.get('first_seen')
                reused_count += 1
                source_tag = f"[{opp.get('source', 'Unknown')}]"
                print(f"    > {source_tag} {scored_opp['title'][:40]}... | Score: {scored_opp['win_probability']} ({scored_opp['fit_label']}) [reused]")
            else:
                scored_opp = analyze_opportunity(opp)
                scored_opp['delta_status'] = "new"
                new_count += 1
                source_tag = f"[{opp.get('source', 'Unknown')}]"
                print(f"    > {source_tag} {scored_opp['title'][:40]}... | Score: {scored_opp['win_probability']} ({scored_opp['fit_label']})")

            scored_opportunities.append(scored_opp)
        except Exception as e:
            print(f"    [!] Analysis failed for item: {str(e)}")

    print(f"\n[*] Phase 2 delta summary: {new_count} new (scored), {reused_count} reused (already archived)")

    # 3. Save & Report
    print(f"\n--- PHASE 3: REPORTING ---")
    print(f"[*] Saving intelligence to {OUTPUT_FILE}...")

    # Atomic write — write to temp file then rename so a crash mid-write
    # never leaves a corrupt opportunities.json.
    # dir=output_dir keeps temp on same volume so shutil.move is an atomic rename.
    # flush+fsync before move ensures OS page cache is committed to disk first.
    output_dir = os.path.dirname(os.path.abspath(OUTPUT_FILE)) or "."
    with tempfile.NamedTemporaryFile("w", dir=output_dir, suffix=".tmp", delete=False) as tmp:
        json.dump(scored_opportunities, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    shutil.move(tmp_path, OUTPUT_FILE)

    print(f"[*] Done. Saved {len(scored_opportunities)} opportunities.")
    
    # Summary of High Value
    high_value = [o for o in scored_opportunities if o['fit_label'] == 'High']
    print(f"\n[!] Found {len(high_value)} HIGH priority targets.")
    
    for h in high_value:
        print(f"\n    --- {h['title']} ---")
        print(f"    [*] Source: {h['source']}")
        print(f"    [*] Score: {h['win_probability']} | Fit: {h['fit_label']}")
        
        red_team = h.get('red_team', {})
        if red_team:
            print(f"    [!] VULNERABILITY: {red_team.get('primary_vector', 'Unknown')}")
            print(f"    [!] RISK SCORE: {red_team.get('vulnerability_score', 0)}/100")
        
        # Finding AS-04: Display Contact Intelligence
        contact = h.get('contact')
        if contact:
            print(f"    [+] POINT OF CONTACT: {contact}")

    # 3.5 Grounded Antibody Pipeline (Item 24) — HIGH-fit opportunities only.
    # Scoped to high_value, not the full actionable set: red_team_analysis() +
    # antibody_agent.generate() are each a "precise"-mode LLM call, and this
    # pipeline was previously orphaned from main.py entirely (never wired in,
    # procurement_shield.json untouched since 2026-06-11) partly because its
    # old CLI path blocked on input() -- incompatible with an unattended run.
    # See red_team_simulation.run_batch()/save_threats() for the pending-review
    # replacement for that gate.
    #
    # 2026-09-07 fix: further scoped to delta_status == "new" -- live-caught via
    # a real run: a HIGH-fit opportunity that's still live (and correctly
    # reused, no re-fetch/re-score) was still getting a full fresh red-team +
    # antibody draft every single run, because this step never checked
    # delta_status at all. That's the most expensive part of the pipeline (2
    # precise-mode LLM calls) re-running on unchanged input, and it was
    # quietly appending a near-duplicate clause for the same opportunity into
    # procurement_shield_pending.json on every run it stayed live -- exactly
    # the "accumulates forever, nothing tells good from bad/redundant apart"
    # problem Jay flagged 09-07. A reused opportunity keeps its
    # already-recorded red_team/immune_system fields (from when it was new);
    # nothing here re-derives or drops them.
    new_high_value = [h for h in high_value if h.get('delta_status') == 'new']
    if new_high_value:
        print(f"\n--- PHASE 3.5: ANTIBODY (grounded clause drafting, {len(new_high_value)} new HIGH-fit"
              f" of {len(high_value)} total) ---")
        try:
            import red_team_simulation
            red_team_simulation.init_simulation()
            threats = red_team_simulation.run_batch(new_high_value)
            red_team_simulation.save_threats(threats)
        except Exception as e:
            print(f"[!] Antibody pipeline failed (non-fatal): {e}")

    # 4. Observability — record this run into the SQLite spine for the dashboard.
    # Non-fatal by design: any failure here is logged and swallowed so the
    # observability layer can never take down acquisition.
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from observatory.recorder import record_run
        log_path = os.environ.get("SCAN_LOG_PATH")  # set by run_scanner.ps1
        run_id = record_run(
            scored_opportunities=scored_opportunities,
            source_counts=source_counts,
            errors=orchestrator.errors,
            started_at=run_started_at,
            log_path=log_path,
        )
        print(f"[*] Observatory: recorded run #{run_id} to data/primordial.db")
    except Exception as e:
        print(f"[!] Observatory recorder failed (non-fatal): {e}")

    orchestrator.shutdown()

if __name__ == "__main__":
    main()
