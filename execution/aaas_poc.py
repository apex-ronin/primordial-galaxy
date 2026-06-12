import os
import json
import re
from dotenv import load_dotenv
from llm_client import complete as llm_complete

load_dotenv()

def scrub_pii(text):
    """
    Uses the local-primary LLM cascade to identify and mask PII and sensitive agency details.
    """
    prompt = f"""
    You are a GovTech Anonymization Agent (AaaS). 
    Below is a raw data packet from a recent federal/state RFP discovery run.
    Your task is to identify and mask the following:
    1. Names of specific individuals (e.g., procurement officers).
    2. Direct phone numbers and email addresses.
    3. Specific internal legacy system names (e.g., 'Great Plains', 'IPS').
    4. Exact dollar amounts or budget figures.
    
    Replace these with generic placeholders like [OFFICER_NAME], [CONTACT_EMAIL], [LEGACY_SYSTEM_X], [BUDGET_AMOUNT].
    
    Keep the context of the RFQ/RFP requirements intact, but make the report safe for external publication in a portfolio.
    
    RAW DATA:
    {text}
    
    OUTPUT ONLY THE ANONYMIZED REPORT.
    """
    
    try:
        result = llm_complete(prompt, mode="fast")
        return result if result else text
    except Exception as e:
        print(f"[!] AaaS Scrubbing Failed: {e}")
        return text

def create_anonymized_intelligence(raw_finding):
    """
    Creates a 'Publication-Safe' intelligence brief.
    """
    print("[*] Initiating AaaS POC: Anonymizing Intelligence Brief...")
    
    raw_text = f"""
    Agency: {raw_finding.get('agency', 'Unknown')}
    RFP ID: {raw_finding.get('rfp_id', 'Unknown')}
    Officer: {raw_finding.get('officer', 'N/A')}
    Contact: {raw_finding.get('contact', 'N/A')}
    Budget Info: {raw_finding.get('budget_info', 'N/A')}
    Legacy Systems: {raw_finding.get('legacy_systems', 'N/A')}
    Requirements: {raw_finding.get('requirements', 'N/A')}
    """
    
    anonymized_report = scrub_pii(raw_text)
    
    output_path = "data/aaas_intelligence_brief.md"
    os.makedirs("data", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# ANONYMIZED INTELLIGENCE BRIEF (Satellite-01 / AaaS)\n\n")
        f.write(anonymized_report)
    
    print(f"[*] AaaS POC Complete. Report saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Synthetic test data — demonstrates the scrubbing pipeline without exposing real
    # agency/officer PII (this file may ship in a public portfolio).
    sample_finding = {
        "agency": "Example Regional Water District",
        "rfp_id": "RFP00-00 (00000.00)",
        "officer": "Jane Doe, Project Manager",
        "contact": "555-555-0100 | jdoe@example.gov",
        "budget_info": "Software & Implementation Experience (25% weight), Price Proposal (20% weight)",
        "legacy_systems": "Excel, Generic ERP, Reporting Suite, Timekeeping System",
        "requirements": "Integrated ERP solution, mobile support, no-code/low-code configuration, CIP planning live by Q4."
    }

    create_anonymized_intelligence(sample_finding)
