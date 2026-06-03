import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

# The "Honey Pot" - Member-only RFP Clearinghouse
TARGET_URL = "https://www.csda.net/career-center/rfp-clearinghouse"

def fetch_csda_opportunities():
    """
    Specialized scraper for CSDA.net. 
    Detects if content is behind a login wall and extracts RFP details from the public feed.
    """
    print(f"[*] [SATELLITE-CSDA] Connecting to {TARGET_URL}...")
    
    opportunities = []
    
    try:
        with sync_playwright() as p:
            # We use a real-looking user agent to avoid common bot blocks
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate to the clearinghouse
            response = page.goto(TARGET_URL, wait_until="networkidle")
            
            # 1. Detect Auth Wall
            # Higher Logic (CSDA's platform) redirects to a login page if private
            if "login" in page.url.lower():
                print("[!] [SATELLITE-CSDA] ALERT: Member Login Required to access full Clearinghouse.")
                # We return a placeholder to alert the user in the dashboard
                return [{
                    "title": "CSDA ACCESS RESTRICTED",
                    "link": TARGET_URL,
                    "snippet": "The CSDA RFP Clearinghouse is currently behind a member login wall. Please provide credentials or log in via the dashboard browser session.",
                    "source": "CSDA",
                    "scraped_at": datetime.now().isoformat()
                }]

            # 2. Extract Publicly Visible RFPs
            # Heuristic: Look for list items or containers with RFP keywords
            page.wait_for_timeout(2000) # Small wait for dynamic content
            
            items = page.evaluate("""() => {
                const results = [];
                // Bug 5 fix: require title length > 20 and exclude exact nav-menu labels
                const NAV_LABELS = ['RFP Clearinghouse', 'About Special Districts',
                                    'Learn About Districts', 'Special Districts Map'];
                const rfpLinks = Array.from(document.querySelectorAll('a')).filter(function(a) {
                    var t = a.innerText.trim();
                    if (NAV_LABELS.indexOf(t) !== -1) return false;
                    if (t.length <= 20) return false;
                    return t.indexOf('RFP') !== -1 || t.indexOf('RFQ') !== -1 || t.indexOf('District') !== -1;
                });

                rfpLinks.forEach(function(link) {
                    var title = link.innerText.trim();
                    var href = link.href;
                    var container = link.closest('div') || link.parentElement;
                    var snippet = container ? container.innerText.substring(0, 200).replace(/\\n/g, ' ') : '';
                    results.push({ title: title, link: href, snippet: snippet });
                });
                return results;
            }""")
            
            print(f"[*] [SATELLITE-CSDA] Found {len(items)} potential items.")
            
            for item in items:
                opp = {
                    "title": item['title'],
                    "link": item['link'],
                    "snippet": item['snippet'],
                    "source": "CSDA Clearinghouse",
                    "scraped_at": datetime.now().isoformat()
                }
                opportunities.append(opp)
            
            browser.close()
            return opportunities

    except Exception as e:
        print(f"[!] [SATELLITE-CSDA] Scrape Failed: {e}")
        return []

if __name__ == "__main__":
    results = fetch_csda_opportunities()
    print(json.dumps(results, indent=2))
