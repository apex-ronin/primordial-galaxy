import json
import os
import shutil
import sys
import tempfile
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
    
    # 🏮 DEPRECATED: El Dorado (Sniper) - Replaced by CSDA/Vertex
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

    # 2. Analysis Phase
    print(f"\n--- PHASE 2: ANALYSIS ({len(all_opportunities)} items) ---")
    
    scored_opportunities = []
    for opp in all_opportunities:
        # We could also wrap analyze_opportunity in orchestrator if we wanted resilience per-item
        # But for now, let's keep it simple.
        try:
            scored_opp = analyze_opportunity(opp)
            scored_opportunities.append(scored_opp)
            
            # Live feedback
            source_tag = f"[{opp.get('source', 'Unknown')}]"
            print(f"    > {source_tag} {scored_opp['title'][:40]}... | Score: {scored_opp['win_probability']} ({scored_opp['fit_label']})")
        except Exception as e:
            print(f"    [!] Analysis failed for item: {str(e)}")

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

    orchestrator.shutdown()

if __name__ == "__main__":
    main()
