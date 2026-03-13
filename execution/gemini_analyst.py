import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from shared_utils import antibody_prompt_sanitizer_v1

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def analyze_rfp(rfp_text, max_chars=30000):
    """
    Analyze RFP text using Gemini API.
    
    Args:
        rfp_text: The full text of the RFP document
        max_chars: Maximum characters to send
    
    Returns:
        dict: Analysis results or None if failed
    """
    if not GEMINI_API_KEY:
        print("    [!] GEMINI_API_KEY not found in .env file")
        return None
        
    if not rfp_text:
        return None

    # Budget Guard - Finding AS-03 (B-4 fix: guard must run on original input, before truncation)
    # Rejects absurdly large documents that would cause excessive API cost.
    MAX_SESSION_CHARS = 100000
    if len(rfp_text) > MAX_SESSION_CHARS:
        print(f"    [!!!] COST CAP TRIGGERED: RFP too large ({len(rfp_text)} chars). Rejecting to prevent budget bleed.")
        return {"status": "rejected", "reason": "cost_cap_exceeded"}

    # Truncate if too long for prompt context
    if len(rfp_text) > max_chars:
        rfp_text = rfp_text[:max_chars] + "\n... [TRUNCATED]"

    prompt = f"""You are a senior AI Fraud Security Researcher performing a dual-track analysis on a government RFP document.

Follow the **Saturation Philosophy**: Combatting fraud through openness and making it too expensive to execute.

### Part 1: Strategic Fit (White Hat)
Analyze if this opportunity is suitable for a small consulting/software firm specializing in remote work.

### Part 2: Red Team Analysis (Black Hat)
Identify specific vectors where an AI-enabled fraudster (a "Prompt Kiddie") could exploit this contract:
1. **Gig Platform Outsourcing**: Can the work be trivially sub-contracted offshore?
2. **Template Farming**: Can AI generate the deliverables with zero human overhead?
3. **Identity Fraud**: Is there a lack of rigorous human-in-the-loop verification?

### Part 3: Antibody Generation (Immune System)
Generate a specific, legally-binding RFP clause (the "Antibody") that would prevent the identified fraud vectors by making them too expensive to facilitate.

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "project_type": "Consulting" | "Construction" | "Mixed",
  "remote_friendly": true | false,
  "small_business_setaside": true | false,
  "estimated_value": "string or Not Specified",
  "win_probability": 0-100,
  "strategic_reasoning": "1 sentence explanation",
  "red_team_findings": {{
    "vulnerability_score": 0-100,
    "primary_vector": "string",
    "exploit_scenario": "How an attacker wins"
  }},
  "immune_system_antibody": {{
    "clause_title": "string",
    "clause_text": "The actual legally-sounding text to insert into the RFP",
    "mitigation_target": "Which vector this blocks"
  }}
}}

RFP Text:
{rfp_text}
"""
    
    # Sanitize input - Finding PA-02
    rfp_text = antibody_prompt_sanitizer_v1(rfp_text)
    # Configure and Run
    genai.configure(api_key=GEMINI_API_KEY)
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1000,
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"    [!] Gemini Analysis Error: {e}")
        return None

if __name__ == "__main__":
    # Test with a sample RFP snippet
    sample_text = """
    LAKE COUNTY SPECIAL DISTRICTS
    REQUEST FOR PROPOSAL
    ON-CALL CIVIL ENGINEERING SERVICES
    
    The Lake County Special Districts is seeking qualified civil engineering firms to provide
    on-call engineering services for various projects including water system improvements,
    wastewater treatment, and road maintenance.
    
    Contract Duration: 3 years
    Estimated Annual Value: $100,000 - $250,000
    
    Small Business Preference: The District encourages small businesses to apply and will
    give preference to qualified local firms.
    
    Work Location: Services may be performed remotely with occasional site visits required
    for field inspections and stakeholder meetings.
    """
    
    analysis = analyze_rfp(sample_text)
    
    if analysis:
        print("\n" + "="*60)
        print("ANALYSIS RESULTS:")
        print(json.dumps(analysis, indent=2))
    else:
        print("\nAnalysis failed.")
