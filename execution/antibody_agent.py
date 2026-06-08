"""
Antibody Agent — legal clause drafting pipeline.

Formerly used AnthropicVertex (Vertex AI endpoint). Swapped to Anthropic API directly
after GCP teardown 2026-06-06. Corpus retrieval now uses local JSON files.

M-26-04 compliance wedge is mandatory on LLM-context opportunities.
Primary source — M-26-04: https://www.whitehouse.gov/wp-content/uploads/2025/12/M-26-04-Increasing-Public-Trust-in-Artificial-Intelligence-Through-Unbiased-AI-Principles-1.pdf
"""

import glob
import json
import os
from dotenv import load_dotenv
from llm_client import complete as llm_complete
from typing import Dict, Any, List

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "legal_corpus")


def _retrieve_relevant_clauses(vector: str) -> List[str]:
    """
    Retrieve legal clause text matching the identified threat vector from local corpus files.

    Replaces Vertex AI Search (dead post-GCP teardown). Uses keyword match on the
    'vector' field in each clause record — exact same field the corpus was built with.
    Falls back to partial word overlap if no direct match found.
    """
    vector_lower = vector.lower()
    vector_words = set(w for w in vector_lower.replace(",", " ").split() if len(w) > 3)

    direct_matches = []
    fuzzy_matches = []

    corpus_files = glob.glob(os.path.join(CORPUS_DIR, "*.json"))
    for fpath in corpus_files:
        try:
            with open(fpath, "r") as f:
                clauses = json.load(f)
            if not isinstance(clauses, list):
                continue
            for clause in clauses:
                clause_vector = clause.get("vector", "").lower()
                clause_text = clause.get("clause_text", "")
                if not clause_text:
                    continue
                if vector_lower in clause_vector or clause_vector in vector_lower:
                    direct_matches.append(clause_text)
                elif vector_words & set(clause_vector.split()):
                    fuzzy_matches.append(clause_text)
        except Exception:
            continue

    results = direct_matches + fuzzy_matches
    return results[:5]  # Top 5 — same limit as Vertex Search had


def generate(opportunity: Dict[str, Any], threat_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    The main interface for the Antibody Agent. Implements Session B Pipeline.

    Returns a dict with clause_title, clause_text, specificity_score, far_reference,
    validation_status, and economic_calibration.
    """
    vector = threat_assessment.get("primary_vector", "General Fraud")
    roi_multiplier = threat_assessment.get("cost_of_fraud_roi", {}).get("roi_multiplier", 5)
    title = opportunity.get("title", "Unknown Project")

    # 1. Retrieval Gate — local corpus
    relevant_legal_text = _retrieve_relevant_clauses(vector)

    # 2. M-26-04 Policy Wedge Detection (Item 6)
    # Primary source: https://www.whitehouse.gov/wp-content/uploads/2025/12/M-26-04-Increasing-Public-Trust-in-Artificial-Intelligence-Through-Unbiased-AI-Principles-1.pdf
    llm_keywords = [
        "llm", "generative ai", "large language model", "chatbot",
        "ai-assisted", "claude", "gpt", "gemini", "artificial intelligence",
    ]
    is_llm_context = any(kw in title.lower() or kw in vector.lower() for kw in llm_keywords)

    m26_policy_snippet = ""
    if is_llm_context:
        print("[*] LLM Context Detected — injecting M-26-04 policy layer...")
        m26_clauses = _retrieve_relevant_clauses("vendor disclosure llm ai transparency")
        m26_policy_snippet = "\n".join(f"- POLICY: {c}" for c in m26_clauses[:3])
        if not m26_policy_snippet:
            # Hardcoded fallback — core M-26-04 requirements
            m26_policy_snippet = (
                "- POLICY (M-26-04, Dec 2025): Vendor must provide Acceptable Use Policy (AUP) "
                "per deployed LLM, model/data cards, end-user feedback mechanism, and 72-hour "
                "incident reporting for violative outputs. Enhanced transparency required for "
                "high-stakes use cases."
            )

    corpus_context = "\n".join(f"- {t}" for t in relevant_legal_text[:3])
    if m26_policy_snippet:
        corpus_context += "\n" + m26_policy_snippet

    # 3. Drafter
    prompt = f"""You are a Specialized Antibody Agent. Draft a high-specificity RFP clause.

THREAT VECTOR: {vector}
FRAUD ROI: {roi_multiplier}x
OPPORTUNITY: {title}

LEGAL CORPUS CONTEXT (use terminology from these where applicable):
{corpus_context}

CRITERIA:
- Must be a 'Procurement Shield' clause.
- Specificity over boilerplate: mention concrete verification steps (e.g. bi-weekly live screenings).
- Economic Burden: verification cost must break the {roi_multiplier}x ROI.
- M-26-04 Compliance Wedge (mandatory if LLM context): vendor must disclose AUP, model/data cards, feedback mechanism, and adhere to 72-hour incident reporting.

Return ONLY valid JSON — no markdown, no backticks:
{{
    "clause_title": "string",
    "clause_text": "3-5 sentences",
    "far_reference": "Specific FAR/CA clause number from context if available",
    "rationale": "Why this blocks {vector}"
}}

DEI COMPLIANCE (Non-negotiable): Focus ONLY on qualifications, experience, and efficiency. \
Do NOT use race, ethnicity, or identity-based metrics. Compliance is material to payment obligation.
"""

    try:
        raw = llm_complete(
            prompt,
            system="You are a JSON-only API. Output strictly valid JSON. No markdown, no code blocks, no backticks.",
            mode="precise",
        )
        if not raw:
            return _emergency_failsafe(vector)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.split("```")[0]

        draft = json.loads(raw.strip())
        if isinstance(draft, list):
            draft = draft[0] if draft else {}

        # 4. Specificity & Calibration Gate
        clause_text = draft.get("clause_text", "")
        clause_len = len(clause_text)
        has_mechanism = any(
            w in clause_text.lower()
            for w in ["verify", "submit", "monitor", "audit", "screen", "report"]
        )
        specificity_score = 40 + (min(clause_len, 400) // 10) + (20 if has_mechanism else 0)

        return {
            "clause_title": draft.get("clause_title"),
            "clause_text": clause_text,
            "specificity_score": specificity_score,
            "far_reference": draft.get("far_reference"),
            "rationale": draft.get("rationale"),
            "validation_status": "VALIDATED" if specificity_score >= 75 else "NEEDS_REVIEW",
            "economic_calibration": (
                "ENFORCED" if (specificity_score / 10) > roi_multiplier else "POTENTIAL_BLEED"
            ),
        }

    except Exception as e:
        import traceback
        error_msg = f"[!] Antibody Generation Error: {e}\n{traceback.format_exc()}"
        log_path = os.path.join(BASE_DIR, "antibody_agent_error.log")
        with open(log_path, "a") as log:
            log.write(error_msg + "\n" + "=" * 40 + "\n")
        return _emergency_failsafe(vector)


def _emergency_failsafe(vector: str) -> Dict[str, Any]:
    return {
        "clause_title": "Emergency Default Antibody",
        "clause_text": (
            f"Contractor must prove work authorship via live periodic audit sessions for {vector}. "
            "All deliverables must be accompanied by documented human-in-the-loop verification evidence."
        ),
        "specificity_score": 50,
        "validation_status": "EMERGENCY_FAILSAFE",
        "far_reference": "FAR 52.203-13",
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_opp = {"title": "AI-Assisted Procurement Analysis Services"}
    test_threat = {
        "primary_vector": "Template Farming & Gig Platform Outsourcing",
        "cost_of_fraud_roi": {"roi_multiplier": 8},
    }
    print(json.dumps(generate(test_opp, test_threat), indent=2))
