import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def scrub_pii(text):
    """
    Uses Gemini to identify and mask PII and sensitive agency details.
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
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
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
    # Test Data from EID Deep Dive
    eid_finding = {
        "agency": "El Dorado Irrigation District (EID)",
        "rfp_id": "RFP26-03 (24046.01)",
        "officer": "Penny [REDACTED], Project Manager",
        "contact": "530-642-4139 | [REDACTED]",
        "budget_info": "Software & Implementation Experience (25% weight), Price Proposal (20% weight)",
        "legacy_systems": "Excel, Great Plains, Crystal Reports, IPS, Kronos, NeoGov, Target Solutions",
        "requirements": "Integrated ERP solution, mobile support, no-code/low-code configuration, CIP planning live by Oct 2026."
    }
    
    create_anonymized_intelligence(eid_finding)
