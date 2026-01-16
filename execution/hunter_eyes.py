import json
from datetime import datetime
from playwright.sync_api import sync_playwright

TARGET_URL = "https://www.csda.net/career-center/rfp-clearinghouse"

def fetch_opportunities():
    """
    Fetches active RFPs from the CSDA RFP Clearinghouse.
    This is the "Honey Pot" - a single source aggregating RFPs from many districts.
    """
    print(f"[*] Connecting to {TARGET_URL} via Headless Browser...")
    
    opportunities = []
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # Navigate
            page.goto(TARGET_URL, wait_until="domcontentloaded")
            
            # Wait for the content to load
            try:
                # The RFPs are in a container, often under "Open RFPs and RFQs"
                # We'll wait for at least one h3 which usually holds the title
                page.wait_for_selector("h3", timeout=15000)
            except:
                print("[!] Content did not load or selector changed.")
                browser.close()
                return []

            # Extract data
            # CSDA structure appears to be:
            # <h3><a href="...">Title</a></h3>
            # <p>...description text...</p>
            
            items_data = page.evaluate("""() => {
                const items = [];
                // Select all H3 headers that contain links (common pattern for their feed)
                const headers = Array.from(document.querySelectorAll('h3 a'));
                
                headers.forEach(header => {
                    const title = header.innerText.trim();
                    const link = header.href;
                    
                    // The description/metadata is usually in the parent's next sibling or surrounding text
                    // For simplicity in this generic scraper, we'll try to grab the parent container's text
                    // In many Higher Logic based sites (like CSDA), the structure is nested.
                    // Let's look for the closest container.
                    
                    // Attempt to find the container text to parse out the District Name
                    // This is heuristic-based.
                    let container = header.closest('div') || header.parentElement;
                    let fullText = container ? container.innerText : "";
                    
                    items.push({ title, link, fullText });
                });
                return items;
            }""")
            
            print(f"[*] Found {len(items_data)} potential items.")
            
            for item in items_data:
                # Basic filtering
                if not item['title']:
                    continue
                    
                # Heuristic to extract District Name if possible
                # Often the text says "The [District Name] is seeking..."
                # For now, we will label the source as "CSDA Clearinghouse" but try to find the district in the title/text
                
                opp = {
                    "title": item['title'],
                    "link": item['link'],
                    "deadline": "See Link", # CSDA text parsing for dates is complex, leaving for Phase 3
                    "source": "CSDA Clearinghouse", 
                    "scraped_at": datetime.now().isoformat(),
                    "snippet": item['fullText'][:200] # Save snippet for analysis
                }
                opportunities.append(opp)
                print(f"    [+] Found: {item['title'][:50]}...")
                
            browser.close()
            return opportunities

    except Exception as e:
        print(f"[!] Error fetching opportunities: {ascii(e)}")
        return []

if __name__ == "__main__":
    # Test run
    opps = fetch_opportunities()
    print(json.dumps(opps, indent=2))
