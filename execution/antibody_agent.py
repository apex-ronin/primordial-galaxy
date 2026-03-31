import json
import os
import random
import google.generativeai as genai
from typing import Dict, Any, List

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
    """Retrieve legal clause text matching the identified threat vector."""
    far = _load_corpus(FAR_FILE)
    state = _load_corpus(STATE_FILE)
    all_clauses = far + state
    
    # Filter by vector - in a more advanced version, use semantic search
    matches = [c['clause_text'] for c in all_clauses if c['vector'] == vector]
    return matches

def generate(opportunity: Dict[str, Any], threat_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    The main interface for the Antibody Agent. Implements Session B Pipeline.
    """
    # 1. Pipeline Input & Context
    vector = threat_assessment.get('primary_vector', 'General Fraud')
    roi_multiplier = threat_assessment.get('cost_of_fraud_roi', {}).get('roi_multiplier', 5)
    title = opportunity.get('title', 'Unknown Project')

    # Ensure genai is configured (in case global config didn't propagate)
    if not genai.get_model('models/gemini-2.0-flash'):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
    
    # 2. Retrieval Gate
    relevant_legal_text = _retrieve_relevant_clauses(vector)
    corpus_context = "\n".join([f"- {txt}" for txt in relevant_legal_text[:3]]) # Top 3
    
    # 3. Drafter (LLM Session)
    # Using Gemini 2.0 Flash for drafting
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
    
    Return JSON:
    {{
        "clause_title": "string",
        "clause_text": "3-5 sentences",
        "far_reference": "Specific FAR/CA PCC number from context",
        "rationale": "Why this blocks {vector}"
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt, 
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        draft = json.loads(response.text)
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
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"[*] Debug: API Key found: {'Yes' if api_key else 'No'}")
    if api_key:
        genai.configure(api_key=api_key)
    
    # Test stub
    test_opp = {"title": "Lake County Engineering"}
    test_threat = {"primary_vector": "Outsourcing Fraud"}
    print(json.dumps(generate(test_opp, test_threat), indent=2))
