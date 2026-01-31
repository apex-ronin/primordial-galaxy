import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

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
    
    # Truncate if too long
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
    
    try:
        print(f"    [*] Sending {len(rfp_text)} chars to Gemini API...")
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
            safety_settings=safety_settings
        )
        
        # Check if response was blocked
        if not response.candidates:
            print(f"    [!] Response blocked or empty")
            return None
            
        # Extract text from response
        try:
            response_text = response.text.strip()
        except ValueError as e:
            print(f"    [!] Could not extract text: {e}")
            return None
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last line (``` markers)
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        # Parse JSON
        analysis = json.loads(response_text)
        
        print(f"    [+] AI Analysis: {analysis.get('project_type', 'Unknown')}, Prob={analysis.get('win_probability', 0)}")
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"    [!] Failed to parse AI response as JSON: {e}")
        print(f"    Raw response: {response_text[:200]}")
        return None
    except Exception as e:
        print(f"    [!] Gemini API call failed: {e}")
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
