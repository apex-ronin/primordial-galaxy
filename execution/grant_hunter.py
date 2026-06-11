"""
Grant Hunter — multi-source discovery and scoring pipeline.

Discovery pipeline (in order):
  1. Hardcoded seeds       — verified high-value grants with direct contacts
  2. Federal REST APIs     — grants.gov + sbir.gov (scraper_grants_api)
  3. Browser portals       — California state programs (scraper_grants_browser)
  (Vertex AI semantic gap-filler retired 2026-06-10 — datastore deleted in GCP teardown)

Scoring: 0-100 across four dimensions:
  - Relevance  (40 pts) — keyword match against Apex Ronin focus areas
  - Agency     (25 pts) — priority federal agencies (DHS, DARPA, NSF, DOD, DOE, NIST)
  - Value      (20 pts) — contract size
  - WAS        (15 pts) — Warfighting Acquisition / critical infrastructure alignment

LIVE CONTACT INTELLIGENCE (Finding AS-04 — intentional internal intel, do not publish)
"""

import json
import os
from scraper_grants_api import fetch_all_api_grants
from scraper_grants_browser import fetch_browser_grants

# Intentional internal intel — see git_publication_safety.md exception note
NSF_SBIR_CONTACTS = {
    "AI_Director": "[REDACTED] ([REDACTED] | [REDACTED])",
    "General_Help": "sbir@nsf.gov | [REDACTED]",
    "Solicitation": "NSF 24-579",
}

# --- Scoring configuration ---

PRIORITY_AGENCIES = {"DHS", "DARPA", "NSF", "DOD", "DOE", "NIST"}

WAS_KEYWORDS = [
    "critical infrastructure", "warfighter", "national security", "cyber defense",
    "rapid acquisition", "operational technology", "ot security", "scada",
    "emergency response", "resilience", "warfighting", "homeland",
]

RELEVANCE_KEYWORDS = {
    "artificial intelligence": 20,
    "ai": 20,
    "cybersecurity": 18,
    "cyber": 15,
    "procurement fraud": 15,
    "procurement": 10,
    "fraud detection": 15,
    "automation": 12,
    "machine learning": 12,
    "government technology": 10,
    "govtech": 10,
    "american ai": 12,       # GSAR 552.239-7001 alignment signal
    "security": 8,
    "detection": 8,
    "sbir": 5,
    "sttr": 5,
}

# Hardcoded seeds — verified active, direct contact on file
SEED_GRANTS = [
    {
        "title": "NSF SBIR Phase I: Cybersecurity and Authentication (CA)",
        "source": "NSF SBIR 24-579 (seed)",
        "link": "https://www.nsf.gov/funding/opportunities/sbirsttr-phase-i-nsf-small-business-innovation-research-small-business",
        "snippet": "Seeking innovative technologies to protect the US cyberinfrastructure, specifically AI-ready data and distributed systems.",
        "value": 305000,
        "contact": NSF_SBIR_CONTACTS["AI_Director"],
        "agency": "NSF",
        "deadline": "TBD",
        "grant_id": "NSF 24-579",
    },
]


def promote_grant_fit(grant: dict) -> dict:
    """
    Score a grant on 0-100 scale. Adds win_probability and fit_label fields in-place.

    Dimensions:
      Relevance (max 40): keyword density in title + snippet
      Agency    (max 25): priority federal agencies
      Value     (max 20): award size
      WAS       (max 15): critical infrastructure / rapid acquisition signals
    """
    text = (grant.get("title", "") + " " + grant.get("snippet", "")).lower()
    agency = grant.get("agency", "").upper()
    score = 0

    # Relevance
    rel = 0
    for kw, pts in RELEVANCE_KEYWORDS.items():
        if kw in text:
            rel += pts
    score += min(rel, 40)

    # Agency priority
    if any(pa in agency for pa in PRIORITY_AGENCIES):
        score += 25

    # Value
    value = grant.get("value", 0)
    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            score += 20
        elif value >= 300_000:
            score += 15
        elif value >= 100_000:
            score += 10
        elif value > 0:
            score += 5

    # WAS alignment — binary bonus, max 15 regardless of multiple matches
    for kw in WAS_KEYWORDS:
        if kw in text:
            score += 15
            break

    score = min(score, 100)
    grant["win_probability"] = score
    grant["fit_label"] = "High" if score >= 70 else "Medium" if score >= 45 else "Low"
    return grant


def fetch_grant_opportunities() -> list:
    """
    Full grant discovery pipeline. Returns scored, deduplicated, sorted grant list.

    Called by orchestrator.py as a standard pipeline module.
    Output format is compatible with opportunities.json schema.
    """
    grants = []
    seen = set()

    # 1. Hardcoded seeds
    for seed in SEED_GRANTS:
        grants.append(seed)
        seen.add(seed["title"].lower()[:60])

    # 2. Federal REST APIs (grants.gov + sbir.gov)
    for grant in fetch_all_api_grants():
        key = grant["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            grants.append(grant)

    # 3. Browser portals (California state programs)
    for grant in fetch_browser_grants():
        key = grant["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            grants.append(grant)

    # 4. Vertex AI semantic gap-filler — retired 2026-06-10 (datastore deleted in
    #    GCP teardown, no local equivalent). Seeds + REST APIs + browser portals remain.

    print(f"[+] Grant Hunter: {len(grants)} total before scoring.")

    # Score all + sort descending
    grants = [promote_grant_fit(g) for g in grants]
    grants.sort(key=lambda x: x.get("win_probability", 0), reverse=True)

    print(f"[+] Grant Hunter complete. Top score: {grants[0]['win_probability'] if grants else 0}")
    return grants
