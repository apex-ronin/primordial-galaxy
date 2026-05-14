import json
import os
import random
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from anthropic import AnthropicVertex
from typing import Dict, Any, List
from .discovery_engine import search_vertex

# --- Configuration ---
# Use absolute paths relative to the script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "legal_corpus")
FAR_FILE = os.path.join(CORPUS_DIR, "far_clauses.json")
STATE_FILE = os.path.join(CORPUS_DIR, "state_clauses.json")

def _load_corpus(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

def _retrieve_relevant_clauses(vector: str) -> List[str]:
    """Retrieve legal clause text matching the identified threat vector via Vertex AI Search."""
    results = search_vertex(query=vector, num_results=5)
    return [r['snippet'] for r in results]

def generate(opportunity: Dict[str, Any], threat_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    The main interface for the Antibody Agent. Implements Session B Pipeline.
    """
    # 1. Pipeline Input & Context
    vector = threat_assessment.get('primary_vector', 'General Fraud')
    roi_multiplier = threat_assessment.get('cost_of_fraud_roi', {}).get('roi_multiplier', 5)
    title = opportunity.get('title', 'Unknown Project')

    # Initialize Vertex AI if not already done
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "govtech-control")
    LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # 2. Retrieval Gate
    relevant_legal_text = _retrieve_relevant_clauses(vector)
    
    # M-26-04 Policy Wedge Detection (Item 6)
    llm_keywords = ['llm', 'generative ai', 'large language model', 'chatbot', 'ai-assisted', 'claude', 'gpt', 'gemini']
    is_llm_context = any(kw in title.lower() or kw in vector.lower() for kw in llm_keywords)
    
    policy_context = ""
    if is_llm_context:
        print("[*] LLM Context Detected. Pulling M-26-04 Policy Layer...")
        policy_results = search_vertex(query="M-26-04 vendor disclosure requirements", num_results=3)
        policy_context = "\n".join([f"- POLICY: {r['snippet']}" for r in policy_results])
        if not policy_context:
            print("[!] WARNING: No M-26-04 policy found in corpus. Proceeding with caution.")

    corpus_context = "\n".join([f"- {txt}" for txt in relevant_legal_text[:3]]) # Top 3
    if policy_context:
        corpus_context += "\n" + policy_context
    
    # 3. Drafter (LLM Session)
    # Using Anthropic Claude Sonnet for drafting via Vertex AI
    prompt = f"""You are a Specialized Antibody Agent. Draft a high-specificity RFP clause.
    
    THREAT VECTOR: {vector}
    FRAUD ROI: {roi_multiplier}x
    OPPORTUNITY: {title}
    
    LEGAL CORPUS CONTEXT (Use terminology from these if applicable):
    {corpus_context}
    
    CRITERIA:
    - Must be a 'Procurement Shield' clause.
    - Specificity over boilerplate: Mention concrete verification steps (e.g. bi-weekly live screenings).
    - Economic Burden: The verification cost must be high enough to break the {roi_multiplier}x ROI.
    - M-26-04 Compliance Wedge (Mandatory): Ensure vendor must disclose Acceptable Use Policies (AUP), provide model/data cards, implement a feedback mechanism, and adhere to 72-hour incident reporting requirements.
    
    Return JSON:
    {{
        "clause_title": "string",
        "clause_text": "3-5 sentences",
        "far_reference": "Specific FAR/CA PCC number from context",
        "rationale": "Why this blocks {vector}"
    }}
    """
    
    # DEI COMPLIANCE GUARD (March 26, 2026 Executive Order)
    dei_prompt_suffix = """
    
    DEI COMPLIANCE (Non-negotiable): Focus ONLY on qualifications, experience, and efficiency. \
Do NOT use or recommend race, ethnicity, or any identity-based metrics. \
Compliance is material to the government's payment obligation.
    """
    full_prompt = prompt + dei_prompt_suffix
    
    try:
        client = AnthropicVertex(project_id=PROJECT_ID, region="us-east5")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system="You are a JSON-only API. Output strictly valid JSON. Do not include markdown formatting or backticks.",
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        
        raw_text = response.content[0].text
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]

        draft = json.loads(raw_text.strip())
        if isinstance(draft, list):
            draft = draft[0] if draft else {}
        
        # 4. Specificity & Calibration Gate
        # Heuristic validation for the POC (can be upgraded to second LLM pass)
        clause_len = len(draft.get('clause_text', ''))
        has_mechanism = any(word in draft.get('clause_text', '').lower() for word in ['verify', 'submit', 'monitor', 'audit', 'screen'])
        
        specificity_score = 40 + (min(clause_len, 400) // 10) + (20 if has_mechanism else 0)
        
        return {
            "clause_title": draft.get('clause_title'),
            "clause_text": draft.get('clause_text'),
            "specificity_score": specificity_score,
            "far_reference": draft.get('far_reference'),
            "validation_status": "VALIDATED" if specificity_score >= 75 else "NEEDS_REVIEW",
            "economic_calibration": "ENFORCED" if (specificity_score/10) > roi_multiplier else "POTENTIAL_BLEED"
        }
        
    except Exception as e:
        import traceback
        error_msg = f"[!] Antibody Generation Error: {e}\n{traceback.format_exc()}"
        with open(os.path.join(BASE_DIR, "antibody_agent_error.log"), "a") as log:
            log.write(error_msg + "\n" + "="*40 + "\n")
        return {
            "clause_title": "Emergency Default Antibody",
            "clause_text": f"Contractor must prove work authorship via live periodic audit sessions for {vector}.",
            "specificity_score": 50,
            "validation_status": "EMERGENCY_FAILSAFE"
        }

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    if PROJECT_ID:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # Test stub
    test_opp = {"title": "Lake County Engineering"}
    test_threat = {"primary_vector": "Outsourcing Fraud"}
    print(json.dumps(generate(test_opp, test_threat), indent=2))
