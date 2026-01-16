import json
import os
from datetime import datetime
from hunter_eyes import fetch_opportunities
from hunter_brain import analyze_opportunity
from discovery_engine import search_google

from scraper_eldorado import fetch_eldorado_opportunities
from scraper_sam import fetch_federal_opportunities

OUTPUT_FILE = "opportunities.json"

def normalize_search_result(result):
    """Converts a Google Search result into an Opportunity object."""
    return {
        "title": result['title'],
        "link": result['link'],
        "deadline": "Unknown (PDF)",  # Search results don't have structured deadlines
        "source": "Google Discovery",
        "scraped_at": datetime.now().isoformat(),
        "snippet": result.get('snippet', '')
    }

def main():
    print("="*60)
    print("GovTech Hunter v0.4 - Full Spectrum + Federal")
    print("="*60)
    
    all_opportunities = []

    # Step 1: The Honey Pot (CSDA)
    print(f"\n[1] Scoping The Honey Pot (CSDA Clearinghouse)...")
    csda_opportunities = fetch_opportunities()
    if csda_opportunities:
        print(f"    [*] Scraped {len(csda_opportunities)} opportunities.")
        all_opportunities.extend(csda_opportunities)
    else:
        print("    [!] CSDA Scraper returned no results.")

    # Step 2: The Sniper (Specific Targets)
    print(f"\n[2] Sniping Specific Targets (El Dorado)...")
    eldorado_opportunities = fetch_eldorado_opportunities()
    if eldorado_opportunities:
        print(f"    [*] Scraped {len(eldorado_opportunities)} opportunities.")
        all_opportunities.extend(eldorado_opportunities)
    else:
        print("    [!] El Dorado Scraper returned no results.")

    # Step 3: The Whale (Federal / SAM.gov)
    print(f"\n[3] Hunting The Whale (SAM.gov Federal Set-Asides)...")
    federal_opportunities = fetch_federal_opportunities()
    if federal_opportunities:
        print(f"    [*] Scraped {len(federal_opportunities)} opportunities.")
        all_opportunities.extend(federal_opportunities)
    else:
        print("    [!] SAM.gov Scraper returned no results.")

    # Step 4: Discover New Targets ("The Scout")
    print(f"\n[4] Scouting for New Targets (Google Search)...")
    # Query: Look for PDF RFPs related to special districts
    query = '"special district" "RFP" site:.gov filetype:pdf'
    search_results = search_google(query, num_results=5)
    
    if search_results:
        print(f"    [*] Discovered {len(search_results)} potential targets.")
        for res in search_results:
            opp = normalize_search_result(res)
            all_opportunities.append(opp)
            print(f"    [+] Found PDF: {opp['title'][:50]}...")
    else:
        print("    [!] No new targets discovered.")

    if not all_opportunities:
        print("\n[!] No opportunities found from any source.")
        return

    # Step 3: Analyze ("The Brain")
    print(f"\n[3] Analyzing {len(all_opportunities)} total opportunities...")
    scored_opportunities = []
    
    for opp in all_opportunities:
        scored_opp = analyze_opportunity(opp)
        scored_opportunities.append(scored_opp)
        
        # Live feedback
        source_tag = "[Scraped]" if opp['source'] != "Google Discovery" else "[PDF]"
        print(f"    > {source_tag} {scored_opp['title'][:40]}... | Score: {scored_opp['win_probability']} ({scored_opp['fit_label']})")

    # Step 4: Save results
    print(f"\n[4] Saving intelligence to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(scored_opportunities, f, indent=2)
        
    print(f"[*] Done. Saved {len(scored_opportunities)} opportunities.")
    
    # Summary
    high_value = [o for o in scored_opportunities if o['fit_label'] == 'High']
    print(f"\n[!] Found {len(high_value)} HIGH priority targets.")
    for h in high_value:
        print(f"    - {h['title']} (Source: {h['source']})")

if __name__ == "__main__":
    main()
