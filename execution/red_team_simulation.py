import json
import os
import re
import random
import time
from dotenv import load_dotenv
from llm_client import complete as llm_complete, get_last_provider
from shared_utils import antibody_prompt_sanitizer_v1, calculate_roi_safe

# Load environment variables
load_dotenv()

INPUT_FILE = "opportunities.json"
OUTPUT_FILE = "threat_assessment.json"

def init_simulation():
    """Seeds the simulation. LLM calls route through the local-primary cascade
    (LM Studio → Venice → Anthropic) via llm_client — no GCP/Vertex auth required."""
    # Entropy-based seed for non-deterministic simulation results
    random.seed(int(time.time()))
    return True

def antibody_prompt_sanitizer_v1_local(text):
    # Keeping local copy for backward compatibility or switching to shared
    from shared_utils import antibody_prompt_sanitizer_v1
    return antibody_prompt_sanitizer_v1(text)

def parse_opportunity_value(opportunity):
    """Extract a numeric contract value from opportunity data with graceful fallback."""
    # 1. Direct integer 'value' field
    raw = opportunity.get('value')
    if isinstance(raw, (int, float)) and raw > 0:
        return int(raw)
    # 2. Parse 'estimated_value' string (e.g., "$100,000 - $250,000" or "$50,000")
    est = str(opportunity.get('estimated_value', '') or '')
    if est and est.lower() not in ('not specified', 'none', ''):
        numbers = re.findall(r'[\d,]+', est)
        vals = [int(n.replace(',', '')) for n in numbers if n.replace(',', '').isdigit() and int(n.replace(',', '')) > 0]
        if vals:
            return int(sum(vals) / len(vals))  # midpoint of any range
    # 3. Fall back to default
    return 50000


# Signatures that identify CSDA navigation pages masquerading as opportunities
_NAV_SIGNATURES = [
    "Advocate  Learn  Member Resources",
    "Posted in: RFP Clearinghouse",
    "About Special Districts",
]
_NAV_TITLES = {"RFP Clearinghouse", "About Special Districts", "Learn About Districts",
               "Special Districts Map", "RFP Clearinghouse\n"}

def is_actionable_rfp(opportunity):
    """Return True only if this opportunity contains enough real contract context to analyze."""
    title = (opportunity.get('title') or '').strip()
    snippet = (opportunity.get('snippet') or '')
    # Filter known navigation/category pages
    if title in _NAV_TITLES:
        return False
    # Filter pages whose snippet is just the CSDA site navigation menu
    if any(sig in snippet for sig in _NAV_SIGNATURES):
        return False
    # Require meaningful combined context length
    if len(title) + len(snippet) < 40:
        return False
    return True


def red_team_analysis(opportunity):
    """
    Analyzes an opportunity from a "Red Team" perspective (simulating a threat actor).
    """
    title = opportunity.get('title', 'Unknown')
    description = opportunity.get('snippet', '') or title

    # ROI Parameters — derived from actual opportunity value (B-2 fix)
    estimated_payout = parse_opportunity_value(opportunity)
    estimated_attacker_cost = max(1000, int(estimated_payout * 0.02))  # 2% of contract value
    roi_multiple = estimated_payout // estimated_attacker_cost

    # Sanitize input
    description = antibody_prompt_sanitizer_v1(description)

    # Construct the "Black Hat" prompt
    prompt = f"""You are a senior Red Team security analyst specializing in government procurement fraud. \
You simulate sophisticated threat actors to find exploitable weaknesses in RFP structures.

CONTRACT CONTEXT:
  Opportunity: {title}
  Description: {description}
  Estimated Contract Value: ${estimated_payout:,}
  Simulated Attacker Setup Cost: ${estimated_attacker_cost:,}
  Fraud ROI Multiple: {roi_multiple}x (flag as HIGH if > 5x)

TASK 1 — THREAT ASSESSMENT
Evaluate these three specific fraud vectors for this contract:
1. Outsourcing Fraud (Gig Sweatshop): Can the work be secretly sub-contracted to offshore labor via Upwork/Fiverr? Look for: remote-first deliverables, digital outputs with no in-person requirement, vague authorship rules.
2. Spear Phishing: Which specific role (e.g., Contracts Officer, IT Director, Finance Manager) is the highest-value credential target? What lure would work?
3. Billing Abuse: Are deliverables defined by hours/effort rather than outcomes? Are milestones vague enough to pad with ghost work?

TASK 2 — IMMUNE SYSTEM ANTIBODY
Generate ONE targeted, legally-binding RFP clause that makes the PRIMARY fraud vector economically unviable.

STRONG ANTIBODY CRITERIA — your clause MUST meet all of these:
- SPECIFIC: Name the exact verification mechanism (not "provide documentation" — say "submit signed git commit logs + bi-weekly live screen-share review")
- ECONOMIC: Enforcement cost for the attacker must exceed the fraud ROI ({roi_multiple}x). If ROI is high, the clause must be proportionally burdensome.
- VECTOR-TARGETED: Clause directly attacks the primary vector. Different vectors require different mechanisms:
    - Outsourcing Fraud → require named individuals, live human-in-the-loop verification sessions, background checks, geo-verified login telemetry
    - Billing Abuse → convert to milestone/outcome-based payment, require pre-approved hour caps per deliverable, mandate auditable work logs (screenshots/commits/timestamps)
    - Spear Phishing → mandate hardware MFA for all contract comms, require out-of-band phone verification for any payment/credential change, whitelist-only email domains
- ENFORCEABLE: Clause must include a concrete consequence (payment forfeiture for that deliverable, contract termination, financial penalty)
- NOT BOILERPLATE: Clauses like "all personnel must be US-based" or "work must be original" are too generic and fail this test. Those can be bypassed by lying. The clause must create a verification burden the attacker cannot economically fake.

Return ONLY valid JSON:
{{
  "vulnerability_score": 0-100,
  "primary_vector": "Outsourcing Fraud" | "Spear Phishing" | "Billing Abuse",
  "attack_surface": "Specific weak point in this contract's structure",
  "red_team_notes": "Exactly how an attacker would exploit this contract step by step",
  "cost_of_fraud_roi": {{
      "estimated_attacker_cost_usd": {estimated_attacker_cost},
      "estimated_payout_usd": {estimated_payout},
      "roi_multiplier": {roi_multiple}
  }},
  "immune_system_antibody": {{
      "clause_title": "Descriptive name (e.g. 'Live Authorship Verification Requirement')",
      "clause_text": "The full, legally-precise clause text ready to insert into an RFP. Must be 3-6 sentences. Must name the specific mechanism, frequency, responsible party, and consequence for non-compliance.",
      "mitigation_target": "Which vector this blocks and why it raises attacker cost above the {roi_multiple}x ROI threshold"
  }}
}}
"""
    
    # Pre-calculated local ROI for prompt context (Finding AS-02)
    local_roi = calculate_roi_safe(estimated_payout, estimated_attacker_cost)

    # DEI COMPLIANCE GUARD (March 26, 2026 Executive Order)
    # Ensure qualifications and performance only.
    dei_prompt_suffix = """
    
    DEI COMPLIANCE (Non-negotiable): Focus ONLY on qualifications, experience, and efficiency. \
Do NOT use or recommend race, ethnicity, or any identity-based metrics in vendor selection or scoring. \
Identity-based scoring is a compliance failure under the 2026 DEI Executive Order.
    """
    full_prompt = prompt + dei_prompt_suffix
    
    try:
        raw = llm_complete(
            full_prompt,
            system="You are a JSON-only API. Output strictly valid JSON. No markdown, no code blocks, no backticks.",
            mode="precise",  # threat modeling + legal antibody drafting — precision tier
        )
        if not raw:
            print(f"    [!] All LLM providers failed for '{title}'")
            return None
        # Strip accidental markdown fences
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0]
        result = json.loads(raw.strip())
        if isinstance(result, list):
            return result[0] if result else None
        if isinstance(result, dict):
            result["_llm_provider"] = get_last_provider() or "unknown"
        return result

    except json.JSONDecodeError as e:
        print(f"    [!] JSON parse error for '{title}': {e}")
        return None
    except Exception as e:
        print(f"    [!] Analysis failed for '{title}': {e}")
        return None

def main():
    print("="*60)
    print("PROJECT BLOOD DIAMOND: RED TEAM SIMULATION")
    print("="*60)
    
    if not init_simulation():
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
    
    skipped = sum(1 for opp in opportunities if not is_actionable_rfp(opp))
    if skipped:
        print(f"[*] Filtered {skipped} navigation/placeholder entries. Analyzing actionable RFPs only.\n")

    for opp in opportunities:
        # Skip navigation pages and low-context entries
        if not is_actionable_rfp(opp):
            continue
            
        print(f"    Targeting: {opp['title'][:50]}...")
        assessment = red_team_analysis(opp)
        
        if assessment:
            # Merge original data with threat assessment
            # Finding AS-02: Ensure ROI multiplier is safe even if LLM fails
            llm_roi = assessment.get('cost_of_fraud_roi', {}).get('roi_multiplier', 0)
            safe_roi = calculate_roi_safe(llm_roi, 1) # Normalizing index

            # Session C Integration: Call the specialized Antibody Agent
            import antibody_agent
            antibody = antibody_agent.generate(opp, assessment)

            threat_profile = {
                "target": opp['title'],
                "source": opp['source'],
                "vulnerability_score": assessment.get('vulnerability_score'),
                "vector": assessment.get('primary_vector'),
                "notes": assessment.get('red_team_notes'),
                "roi_index": safe_roi,
                "immune_system_antibody": antibody
            }
            threats.append(threat_profile)
            
            # Print high-risk findings
            if assessment.get('vulnerability_score', 0) > 70:
                print(f"    [!!!] HIGH VULNERABILITY DETECTED (Score: {assessment['vulnerability_score']})")
                print(f"          Vector: {assessment['primary_vector']}")
                print(f"          Exploit: {assessment['red_team_notes']}\n")
    
    # Finding AS-02: Mandatory Human Gate for Red Team Findings
    print("\n[MANDATORY AUDIT GATE]")
    print(f"[*] Identified {len(threats)} potential vectors.")
    confirm = input("Confirm acceptance of these findings into the Immune System (y/n)? ")
    if confirm.lower() != 'y':
        print("[!] Deployment aborted by Human Gate.")
        return

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(threats, f, indent=2)

    # B-3 fix: append new antibodies to procurement_shield.json
    shield_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'procurement_shield.json')
    shield_file = os.path.normpath(shield_file)
    os.makedirs(os.path.dirname(shield_file), exist_ok=True)
    try:
        with open(shield_file, 'r') as f:
            shield = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        shield = []
    new_antibodies = [t['immune_system_antibody'] for t in threats if t.get('immune_system_antibody')]
    shield.extend(new_antibodies)
    with open(shield_file, 'w') as f:
        json.dump(shield, f, indent=2)
    print(f"[*] {len(new_antibodies)} antibody clause(s) saved to {shield_file}")

    print("="*60)
    print(f"[*] Simulation Complete. Identified {len(threats)} potential vectors.")
    print(f"[*] Threat assessment saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
