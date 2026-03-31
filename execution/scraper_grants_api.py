"""
Federal grant discovery via public REST APIs.
No browser required. No API key required.

Sources:
  - grants.gov  — POST /v1/api/search  (all federal agencies)
  - sbir.gov    — GET  /solicitations   (SBIR/STTR across DHS, NSF, DARPA, DOD, DOE)

Policy context (OMB M-26-04 / GSAR 552.239-7001 / WAS):
  Filters and keywords are tuned to surface AI, cybersecurity, and critical-infrastructure
  opportunities aligned with the 2026 federal buying environment.
"""

import time
import requests

GRANTS_GOV_URL = "https://api.grants.gov/v1/api/search"
SBIR_API_URL = "https://api.sbir.gov/solicitations"

# Search terms ordered by expected relevance to Apex Ronin's focus areas
SEARCH_TERMS = [
    "cybersecurity artificial intelligence",
    "AI procurement fraud detection",
    "critical infrastructure technology",
    "government technology automation",
    "American AI systems compliance",       # GSAR 552.239-7001 alignment
    "warfighting acquisition rapid",        # WAS buying trigger
]

# Agencies whose SBIR/STTR programs are highest-priority for Apex Ronin
SBIR_AGENCIES = ["DHS", "NSF", "DARPA", "DOD", "DOE", "NIST"]


def _normalize_value(raw) -> int:
    """Parse award ceiling/floor to int. Returns 0 on failure."""
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        raw = raw.replace("$", "").replace(",", "").strip()
        try:
            return int(float(raw))
        except ValueError:
            return 0
    return 0


def search_grants_gov(keyword: str, rows: int = 25) -> list:
    """
    POST search to grants.gov public API.
    Returns normalized grant dicts. Never raises — logs and returns [] on failure.
    """
    payload = {
        "keyword": keyword,
        "oppStatuses": "posted",
        "rows": rows,
        "startRecordNum": 0,
        "sortBy": "openDate|desc",
    }
    try:
        resp = requests.post(GRANTS_GOV_URL, json=payload, timeout=20)
        resp.raise_for_status()
        hits = resp.json().get("data", {}).get("oppHits", [])
        results = []
        for opp in hits:
            results.append({
                "title": opp.get("title", "Unknown"),
                "source": "grants.gov",
                "link": f"https://www.grants.gov/search-results-detail/{opp.get('id', '')}",
                "snippet": (opp.get("synopsis") or "")[:300],
                "value": _normalize_value(opp.get("awardCeiling") or opp.get("awardFloor", 0)),
                "agency": opp.get("agencyName", "Unknown"),
                "deadline": opp.get("closeDate", "TBD"),
                "grant_id": opp.get("number", ""),
            })
        return results
    except Exception as e:
        print(f"[!] grants.gov '{keyword}': {e}")
        return []


def search_sbir(agency: str = None) -> list:
    """
    GET open solicitations from sbir.gov.
    agency: one of DHS, NSF, DARPA, DOD, DOE, NIST — or None for all.
    Returns normalized grant dicts.
    """
    params = {"open": "1", "rows": 20}
    if agency:
        params["agency"] = agency
    try:
        resp = requests.get(SBIR_API_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get("results", [])
        results = []
        for sol in items:
            results.append({
                "title": (
                    sol.get("program_title")
                    or sol.get("solicitation_title")
                    or "SBIR Solicitation"
                ),
                "source": f"sbir.gov/{agency or 'all'}",
                "link": sol.get("solicitation_agency_url") or "https://www.sbir.gov/solicitations",
                "snippet": (sol.get("program_description") or "")[:300],
                "value": _normalize_value(
                    sol.get("award_amount_max") or sol.get("award_amount", 0)
                ),
                "agency": sol.get("agency", agency or "Unknown"),
                "deadline": sol.get("close_date") or sol.get("solicitation_close_date", "TBD"),
                "grant_id": sol.get("solicitation_number", ""),
            })
        return results
    except Exception as e:
        print(f"[!] sbir.gov agency={agency}: {e}")
        return []


def fetch_all_api_grants() -> list:
    """
    Aggregate all API-sourced grants. Deduplicates by normalized title prefix.
    Returns a flat list ready for grant_hunter.promote_grant_fit() scoring.
    """
    all_grants = []
    seen = set()

    print("[*] Grant API: Querying grants.gov...")
    for term in SEARCH_TERMS:
        for grant in search_grants_gov(term):
            key = grant["title"].lower()[:60]
            if key not in seen:
                seen.add(key)
                all_grants.append(grant)
        time.sleep(0.5)  # polite rate limiting

    print(f"[*] Grant API: {len(all_grants)} unique from grants.gov. Querying sbir.gov...")
    for agency in SBIR_AGENCIES:
        for grant in search_sbir(agency):
            key = grant["title"].lower()[:60]
            if key not in seen:
                seen.add(key)
                all_grants.append(grant)
        time.sleep(0.3)

    print(f"[+] Grant API: {len(all_grants)} total unique grants discovered.")
    return all_grants
