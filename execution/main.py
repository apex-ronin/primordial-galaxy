import json
import os
from datetime import datetime
from hunter_eyes import fetch_opportunities
from hunter_brain import analyze_opportunity
from discovery_engine import search_google
from scraper_eldorado import fetch_eldorado_opportunities
from scraper_sam import fetch_federal_opportunities
from health_check import run_all_checks
from orchestrator import Orchestrator

OUTPUT_FILE = "opportunities.json"

def normalize_google_result(results):
    """
    Wrapper to normalize Google results inside the orchestrator flow if needed,
    but Orchestrator returns the raw list. We can normalize post-fetch.
    """
    normalized = []
    if not results: return []
    
    for res in results:
        normalized.append({
            "title": res.get('title', 'Unknown PDF'),
            "link": res.get('link', '#'),
            "deadline": "Unknown (PDF)",
            "source": "Google Discovery",
            "scraped_at": datetime.now().isoformat(),
            "snippet": res.get('snippet', '')
        })
    return normalized

def main():
    print("="*60)
    print("GovTech Hunter v0.5 - Self-Healing & Adaptive")
    print("="*60)
    
    # 0. Pre-flight Health Check
    print("\n[0] Running Pre-flight Health Checks...")
    if not run_all_checks():
        print("\n[!] Health checks reported issues. Engaging self-healing protocols...")
        # In a real scenario, we might attempt auto-fixes here. 
        # For now, we proceed with caution, relying on Orchestrator to skip broken modules.
    
    orchestrator = Orchestrator()
    
    # 1. Execution Phase (Parallel-ish execution via Orchestrator)
    print("\n--- PHASE 1: ACQUISITION ---")
    
    # Define tasks
    # We pass the function reference and its arguments
    results_csda = orchestrator.run_module(
        "CSDA (Honey Pot)", 
        fetch_opportunities
    )
    
    results_eldorado = orchestrator.run_module(
        "El Dorado (Sniper)", 
        fetch_eldorado_opportunities
    )
    
    results_sam = orchestrator.run_module(
        "SAM.gov (The Whale)", 
        fetch_federal_opportunities
    )
    
    # Google requires arguments
    query = '"special district" "RFP" site:.gov filetype:pdf'
    results_google_raw = orchestrator.run_module(
        "Google Discovery",
        search_google,
        query,
        num_results=5
    )
    
    # Normalization for Google results
    results_google = normalize_google_result(results_google_raw)

    # Consolidate
    all_opportunities = orchestrator.consolidate_results([
        results_csda, 
        results_eldorado, 
        results_sam, 
        results_google
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
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(scored_opportunities, f, indent=2)
        
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

if __name__ == "__main__":
    main()
