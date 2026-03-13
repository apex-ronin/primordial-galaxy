import json
import os
import random
import requests
from discovery_engine import search_vertex

# LIVE CONTACT INTELLIGENCE (Finding AS-04)
NSF_SBIR_CONTACTS = {
    "AI_Director": "[REDACTED] ([REDACTED] | [REDACTED])",
    "General_Help": "sbir@nsf.gov | [REDACTED]",
    "Solicitation": "NSF 24-579"
}

def fetch_grant_opportunities():
    """
    Live discovery for SBIR/STTR grants using Vertex AI Search.
    """
    # 1. Live Discovery Run
    print("[*] Initiating Grant Hunter Discovery via Vertex AI...")
    grant_query = '"SBIR" "STTR" "grant" "AI" "cybersecurity" site:grants.gov'
    vertex_results = search_vertex(grant_query, num_results=10)
    
    grants = []
    
    # 2. Add verified seed grants (known active node)
    grants.append({
        "title": "NSF SBIR Phase I: Cybersecurity and Authentication (CA)",
        "source": "NSF SBIR 24-579",
        "link": "https://www.nsf.gov/funding/opportunities/sbirsttr-phase-i-nsf-small-business-innovation-research-small-business",
        "snippet": "Seeking innovative technologies to protect the US cyberinfrastructure, specifically AI-ready data and distributed systems.",
        "value": 305000,
        "contact": NSF_SBIR_CONTACTS["AI_Director"]
    })

    # 3. Incorporate live Vertex findings
    for res in vertex_results:
        grants.append({
            "title": res['title'],
            "source": "Live Grant Discovery",
            "link": res['link'],
            "snippet": res['snippet'],
            "value": "TBD (Phase I/II)",
            "contact": "Check link for program officer"
        })
        
    return grants

def promote_grant_fit(grant):
    """
    Calculates a 'Growth Score' for the grant based on Primordial principles.
    """
    # Simply mapping for now
    title = grant.get('title', '').lower()
    score = 50
    if "ai" in title or "security" in title:
        score += 30
    if "cyber" in title:
        score += 15
        
    grant['win_probability'] = score
    grant['fit_label'] = "High" if score > 80 else "Medium"
    return grant
