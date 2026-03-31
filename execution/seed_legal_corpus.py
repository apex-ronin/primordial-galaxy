import json
import os
import requests
from bs4 import BeautifulSoup

# This is a seedling script for Session A: Legal Corpus Seeding
# It will eventually be replaced by a more robust scraper if needed.

DATA_DIR = "data/legal_corpus"
FAR_FILE = os.path.join(DATA_DIR, "far_clauses.json")
STATE_FILE = os.path.join(DATA_DIR, "state_clauses.json")

# Initial Curated Clauses for POC (Seed Data)
# In a full run, we would scrape acquisition.gov and leginfo.ca.gov
SEED_FAR = [
    {
        "id": "FAR 52.222-50",
        "title": "Combating Trafficking in Persons",
        "vector": "Outsourcing Fraud",
        "clause_text": "The Contractor shall inform the Contracting Officer and the agency Inspector General immediately of any credible information it receives from any source... that alleges a Contractor employee, subcontractor, or subcontractor employee... has engaged in conduct that violates the policy in paragraph (b) of this clause."
    },
    {
        "id": "FAR 52.204-21",
        "title": "Basic Safeguarding of Covered Contractor Information Systems",
        "vector": "Identity Fraud",
        "clause_text": "The Contractor shall apply the following basic safeguarding requirements and procedures to protect covered contractor information systems... (1) Limit information system access to authorized users, processes acting on behalf of authorized users, or devices..."
    },
    {
        "id": "FAR 52.232-5",
        "title": "Payments under Fixed-Price Construction Contracts",
        "vector": "Billing Abuse",
        "clause_text": "The Government shall make progress payments monthly as the work proceeds, or at more frequent intervals as determined by the Contracting Officer, on estimates of work accomplished which meets the standards of quality established under the contract."
    }
]

SEED_STATE = [
    {
        "id": "CA PCC 20101",
        "title": "Prequalification Questionnaire",
        "vector": "Identity Fraud",
        "clause_text": "A public entity may require, for any contract for which a person is required to be licensed... that each prospective bidder for the contract submit a standardized questionnaire and financial statement, including a complete statement of the bidder's experience in performing public works."
    }
]

def seed_corpus():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(FAR_FILE, 'w') as f:
        json.dump(SEED_FAR, f, indent=2)
        print(f"[*] Seeded {len(SEED_FAR)} FAR clauses to {FAR_FILE}")

    with open(STATE_FILE, 'w') as f:
        json.dump(SEED_STATE, f, indent=2)
        print(f"[*] Seeded {len(SEED_STATE)} State clauses to {STATE_FILE}")

if __name__ == "__main__":
    seed_corpus()
