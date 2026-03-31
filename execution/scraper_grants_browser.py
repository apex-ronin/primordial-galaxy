"""
State and portal grant discovery via Playwright browser automation.

Uses the human-navigator humanizer + parser layer for bot-detection resistance:
  - Non-linear mouse movement with jitter
  - Variable typing delays
  - Natural scroll patterns
  - navigator.webdriver fingerprint suppression

Targets portals that have no public REST API. Add new sources to PORTAL_CONFIGS —
no code changes required, just a new config dict.

Current portals:
  - CalOSBA SBIR/STTR Match  — California state SBIR matching program
  - CA IBank Innovation       — California Infrastructure and Economic Development Bank
  - CA CRIN                   — TODO: confirm URL before enabling

Policy context: California state grants are outside the federal API surface (grants.gov /
sbir.gov) but align with WAS and OMB M-26-04 mandates at the state-procurement level.
"""

import asyncio
import sys
import os

from playwright.async_api import async_playwright

# Allow running from execution/ directory directly
sys.path.insert(0, os.path.dirname(__file__))
from browser.humanizer import human_scroll
from browser.parser import parse_page_state

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# Keywords that indicate a link or element describes a grant/funding opportunity
OPPORTUNITY_KEYWORDS = {
    "grant", "funding", "sbir", "sttr", "innovation", "opportunity",
    "solicitation", "award", "program", "rfp", "rfq", "contract",
    "cybersecurity", "technology", "ai", "artificial intelligence",
}

# Portal configs — each entry is self-contained, no code changes to add a new source
PORTAL_CONFIGS = [
    {
        "name": "CalOSBA SBIR Match",
        "url": "https://calblocks.calosba.ca.gov/",
        "description": "California SBIR/STTR matching — state agencies paired with federal awardees",
        "agency": "State — California / CalOSBA",
        "enabled": True,
    },
    {
        "name": "CA IBank Programs",
        "url": "https://ibank.ca.gov/programs/",
        "description": "California Infrastructure and Economic Development Bank grant programs",
        "agency": "State — California / IBank",
        "enabled": True,
    },
    # TODO: Confirm URL for California CRIN before enabling
    # {
    #     "name": "California CRIN",
    #     "url": "https://CONFIRM_URL/",
    #     "description": "California Research Innovation Network grant program",
    #     "agency": "State — California / CRIN",
    #     "enabled": False,
    # },
]


async def scrape_portal(portal: dict) -> list:
    """
    Navigate to a portal, scroll naturally, parse DOM state, extract grant-relevant links.
    Returns normalized grant dicts. Never raises — returns [] on any failure.
    """
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # Suppress webdriver fingerprint
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            print(f"[*] Browser: Navigating to {portal['name']}...")
            await page.goto(portal["url"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5)

            # Natural scroll to trigger lazy-loaded content
            for _ in range(3):
                await human_scroll(page)
                await asyncio.sleep(0.8)

            state = await parse_page_state(page)
            print(f"[*] Browser: {len(state['elements'])} elements on {portal['name']}")

            seen_titles = set()
            for el in state["elements"]:
                text = el.get("text", "").strip()
                href = el.get("href") or portal["url"]

                if len(text) < 10:
                    continue

                words = set(text.lower().split())
                if words & OPPORTUNITY_KEYWORDS:
                    title = text[:120]
                    if title.lower() not in seen_titles:
                        seen_titles.add(title.lower())
                        results.append({
                            "title": title,
                            "source": portal["name"],
                            "link": href if href.startswith("http") else portal["url"],
                            "snippet": portal["description"],
                            "value": 0,
                            "agency": portal["agency"],
                            "deadline": "TBD",
                            "grant_id": "",
                        })

        except Exception as e:
            print(f"[!] Browser scrape failed for {portal['name']}: {e}")
        finally:
            await browser.close()

    return results


def fetch_browser_grants() -> list:
    """
    Scrape all enabled portal configs. Synchronous entry point for orchestrator.
    Returns normalized grant list ready for grant_hunter.promote_grant_fit() scoring.
    """
    enabled = [p for p in PORTAL_CONFIGS if p.get("enabled", True)]
    if not enabled:
        print("[*] Grant Browser: No portals enabled.")
        return []

    print(f"[*] Grant Browser: Scraping {len(enabled)} portal(s)...")
    all_results = []

    for portal in enabled:
        try:
            results = asyncio.run(scrape_portal(portal))
        except RuntimeError:
            # Already inside an event loop (e.g. Jupyter / some orchestrators)
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(scrape_portal(portal))

        all_results.extend(results)
        print(f"[+] {portal['name']}: {len(results)} opportunities found")

    print(f"[+] Grant Browser: {len(all_results)} total from browser portals.")
    return all_results
