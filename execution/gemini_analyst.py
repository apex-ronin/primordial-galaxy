"""
RFP Analyst — dual-track analysis (strategic fit + red team + antibody).

Formerly used Vertex AI / Gemini Flash. Swapped to Anthropic API (claude-sonnet-4-6)
after GCP teardown 2026-06-06. Local-primary architecture.

Primary source — M-26-04: https://www.whitehouse.gov/wp-content/uploads/2025/12/M-26-04-Increasing-Public-Trust-in-Artificial-Intelligence-Through-Unbiased-AI-Principles-1.pdf
"""

import json
import os
from dotenv import load_dotenv
from llm_client import complete as llm_complete
from shared_utils import antibody_prompt_sanitizer_v1

load_dotenv()

# Budget cap — reject documents that would cause excessive token spend
MAX_SESSION_CHARS = 100_000
MAX_PROMPT_CHARS = 30_000


def analyze_rfp(rfp_text: str, max_chars: int = MAX_PROMPT_CHARS) -> dict | None:
    """
    Analyze RFP text using Claude API.

    Returns a dict with strategic fit, red team findings, and an immune system antibody clause.
    Returns None on any failure — caller falls back to keyword scoring.
    """
    if not rfp_text:
        return None

    # Budget Guard (B-4 fix: guard runs on original input before truncation)
    if len(rfp_text) > MAX_SESSION_CHARS:
        print(f"    [!!!] COST CAP TRIGGERED: {len(rfp_text)} chars > {MAX_SESSION_CHARS}. Rejecting.")
        return {"status": "rejected", "reason": "cost_cap_exceeded"}

    if len(rfp_text) > max_chars:
        rfp_text = rfp_text[:max_chars] + "\n... [TRUNCATED]"

    # Sanitize input — Finding PA-02
    rfp_text = antibody_prompt_sanitizer_v1(rfp_text)

    prompt = f"""You are a senior AI Fraud Security Researcher performing a dual-track analysis on a government RFP document.

Follow the **Saturation Philosophy**: Combatting fraud through openness and making it too expensive to execute.

### Part 1: Strategic Fit (White Hat)
Analyze if this opportunity is suitable for a small consulting/software firm specializing in remote work.

### Part 2: Red Team Analysis (Black Hat)
Identify specific vectors where an AI-enabled fraudster (a "Prompt Kiddie") could exploit this contract:
1. **Gig Platform Outsourcing**: Can the work be trivially sub-contracted offshore?
2. **Template Farming**: Can AI generate the deliverables with zero human overhead?
3. **Identity Fraud**: Is there a lack of rigorous human-in-the-loop verification?

**DEI COMPLIANCE (Non-negotiable)**: Focus ONLY on qualifications, experience, and efficiency. Do NOT use or recommend race, ethnicity, or any identity-based metrics. Identity-based scoring is a compliance failure under the 2026 DEI Executive Order.

### Part 3: Antibody Generation (Immune System)
Generate a specific, legally-binding RFP clause that prevents the identified fraud vectors by making them too expensive to execute. Use legally precise language. Focus on performance verification.

Return ONLY valid JSON — no markdown, no backticks, no explanation:
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
        raw = llm_complete(
            prompt,
            system="You are a JSON-only API. Output strictly valid JSON. No markdown, no code blocks, no backticks.",
            mode="fast",
        )
        if not raw:
            print("    [!] All LLM providers failed — falling back to keyword scoring")
            return None
        # Strip accidental markdown fences
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"    [!] JSON parse error in RFP analysis: {e}")
        return None
    except Exception as e:
        print(f"    [!] RFP analysis error: {e}")
        return None


if __name__ == "__main__":
    sample = """
    LAKE COUNTY SPECIAL DISTRICTS
    REQUEST FOR PROPOSAL — ON-CALL CIVIL ENGINEERING SERVICES

    Seeking qualified civil engineering firms for water system improvements,
    wastewater treatment, and road maintenance. 3-year contract. Est. $100K-$250K/yr.
    Small business preference. Remote work with occasional site visits.
    """
    result = analyze_rfp(sample)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Analysis failed — check ANTHROPIC_API_KEY in .env")
