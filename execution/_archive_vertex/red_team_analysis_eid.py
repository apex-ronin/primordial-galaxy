import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def run_red_team_eid(requirements, legacy_systems, target="Example Irrigation District"):
    """
    Performs a Red Team security/risk analysis for a GovTech ERP target.
    `target` is parameterized — do not hardcode a real district name.
    """
    prompt = f"""
    You are a Red Team Security Architect for 'Primordial Galaxy'.
    Perform a targeted risk analysis for the following GovTech ERP discovery:

    TARGET: {target}
    REQUIREMENTS: {requirements}
    LEGACY SYSTEMS: {legacy_systems}
    
    Analyze for the following 'Antibody' vectors:
    1. Legacy Debt: Risks of integrating with 'Excel' and 'Great Plains'.
    2. Shadow IT: Security risks of the 'no-code/low-code' requirement.
    3. Mobile Attack Surface: Risks of exposing all ERP interfaces to mobile.
    4. Compliance Gaps: Risks with the Oct 2026/Jan 2027 aggressive timeline.
    
    Structure the output as a 'Threat Matrix' with Risk Levels (1-100).
    """
    
    print("[*] Initiating Deep Analysis: Red Team Simulation (EID Target)...")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        output_path = "data/red_team_eid_analysis.md"
        os.makedirs("data", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# RED TEAM THREAT MATRIX: {target} (ERP)\n\n")
            f.write(response.text)
        
        print(f"[*] Deep Analysis Complete. Report saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"[!] Red Team Analysis Failed: {e}")
        return None

if __name__ == "__main__":
    requirements = "Integrated ERP solution, mobile support, no-code/low-code configuration, CIP planning live by Oct 2026."
    legacy_systems = "Excel, Great Plains, Crystal Reports, IPS, Kronos, NeoGov, Target Solutions"
    
    run_red_team_eid(requirements, legacy_systems)
