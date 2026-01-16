import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INPUT_FILE = "opportunities.json"
OUTPUT_FILE = "threat_assessment.json"

def init_gemini():
    if not GEMINI_API_KEY:
        print("[!] GEMINI_API_KEY not found in .env file")
        return False
    genai.configure(api_key=GEMINI_API_KEY)
    return True

def red_team_analysis(opportunity):
    """
    Analyzes an opportunity from a "Red Team" perspective (simulating a threat actor).
    """
    title = opportunity.get('title', 'Unknown')
    description = opportunity.get('snippet', '') or title
    
    # Construct the "Black Hat" prompt
    prompt = f"""You are a Red Team security analyst simulating a sophisticated threat actor. 
    Analyze this government contract opportunity to identify potential vulnerabilities to fraud, abuse, or social engineering.

    Opportunity: {title}
    Context: {description}

    Assess the following risks:
    1. **Gig Sweatshop Risk:** Can this work be secretly outsourced to unauthorized offshore labor? (Look for remote work + digital deliverables).
    2. **Spear-Phishing Vector:** What specific department or role would be the best target for a credential harvesting attack?
    3. **Billing Fraud Potential:** Are the deliverables vague enough to allow for "ghost hours" or inflated billing?

    Return ONLY valid JSON in this format:
    {{
      "vulnerability_score": 0-100,
      "primary_vector": "Outsourcing Fraud" or "Spear Phishing" or "Billing Abuse",
      "attack_surface": "Brief explanation of the weak point",
      "red_team_notes": "How an attacker would exploit this"
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.8, # Higher temperature for creative threat modeling
                max_output_tokens=1000,
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        if isinstance(result, list):
            return result[0] if result else None
        return result
        
    except Exception as e:
        print(f"    [!] Analysis failed for '{title}': {e}")
        return None

def main():
    print("="*60)
    print("PROJECT BLOOD DIAMOND: RED TEAM SIMULATION")
    print("="*60)
    
    if not init_gemini():
        return

    # Load existing opportunities
    if not os.path.exists(INPUT_FILE):
        print(f"[!] {INPUT_FILE} not found. Run main.py first.")
        return
        
    with open(INPUT_FILE, 'r') as f:
        opportunities = json.load(f)
    
    print(f"[*] Loaded {len(opportunities)} targets from {INPUT_FILE}")
    print("[*] Initiating Threat Assessment...\n")
    
    threats = []
    
    for opp in opportunities:
        # Only analyze if we have enough data
        if len(opp.get('title', '')) < 10:
            continue
            
        print(f"    Targeting: {opp['title'][:50]}...")
        assessment = red_team_analysis(opp)
        
        if assessment:
            # Merge original data with threat assessment
            threat_profile = {
                "target": opp['title'],
                "source": opp['source'],
                "vulnerability_score": assessment.get('vulnerability_score'),
                "vector": assessment.get('primary_vector'),
                "notes": assessment.get('red_team_notes')
            }
            threats.append(threat_profile)
            
            # Print high-risk findings
            if assessment.get('vulnerability_score', 0) > 70:
                print(f"    [!!!] HIGH VULNERABILITY DETECTED (Score: {assessment['vulnerability_score']})")
                print(f"          Vector: {assessment['primary_vector']}")
                print(f"          Exploit: {assessment['red_team_notes']}\n")
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(threats, f, indent=2)
        
    print("="*60)
    print(f"[*] Simulation Complete. Identified {len(threats)} potential vectors.")
    print(f"[*] Threat assessment saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
