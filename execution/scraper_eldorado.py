import json
from datetime import datetime
from playwright.sync_api import sync_playwright

TARGET_URL = "https://www.eid.org/doing-business-with-eid/procurement-and-contracts"

def fetch_eldorado_opportunities():
    """
    Fetches active RFPs from the El Dorado Irrigation District website using Playwright.
    This launches a visible browser to bypass Cloudflare/JavaScript challenges.
    """
    print(f"[*] Connecting to {TARGET_URL} via Headless Browser...")
    
    opportunities = []
    
    try:
        with sync_playwright() as p:
            # Launch browser with stealth args
            # headless=False is CRITICAL for bypassing strong Cloudflare protections
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # Navigate and wait for content
            page.goto(TARGET_URL, wait_until="domcontentloaded")
            
            # Wait for the table to appear (timeout after 30s)
            try:
                page.wait_for_selector("table", timeout=30000)
            except:
                print("[!] Table not found. Capturing debug screenshot...")
                page.screenshot(path="debug_error.png")
                browser.close()
                return []

            # Extract data using page evaluation (runs JS in the browser)
            rows_data = page.evaluate("""() => {
                const rows = Array.from(document.querySelectorAll('table tr')).slice(1);
                return rows.map(row => {
                    const cols = row.querySelectorAll('td');
                    if (cols.length < 3) return null;
                    
                    const linkTag = cols[1].querySelector('a');
                    const title = linkTag ? linkTag.innerText.trim() : cols[1].innerText.trim();
                    const link = linkTag ? linkTag.href : window.location.href;
                    const deadline = cols[3] ? cols[3].innerText.trim() : '';
                    const status = cols[4] ? cols[4].innerText.trim() : '';
                    
                    return { title, link, deadline, status };
                }).filter(item => item !== null);
            }""")
            
            print(f"[*] Found {len(rows_data)} rows in the table.")
            
            for item in rows_data:
                # Filter for active only
                if "Closed" in item['status'] or "Awarded" in item['status']:
                    continue
                    
                opp = {
                    "title": item['title'],
                    "link": item['link'],
                    "deadline": item['deadline'],
                    "source": "El Dorado Irrigation District",
                    "scraped_at": datetime.now().isoformat(),
                    "snippet": f"Deadline: {item['deadline']}"
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
    opps = fetch_eldorado_opportunities()
    print(json.dumps(opps, indent=2))
