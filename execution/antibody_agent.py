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
import re
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from llm_client import complete as llm_complete
from typing import Dict, Any, List, Tuple

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "legal_corpus")

# --- Semantic retrieval config (mirrors ronin/app/agents/prism_tools.py) ---
# Local nomic-embed FAISS index built by data-arsenal/pipeline/build_local_indexes.py.
# Sovereign: no network beyond localhost LM Studio, no GCP. Index dir overridable
# via RONIN_INDEX_DIR; query embedder served at LOCAL_LLM_BASE_URL.
INDEX_DIR = Path(os.environ.get("RONIN_INDEX_DIR", r"G:\AI-Models\indexes"))
EMBED_URL = os.environ.get(
    "LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"
).rstrip("/") + "/embeddings"
LEGAL_INDEX = "legal_corpus"


@lru_cache(maxsize=1)
def _load_legal_index():
    """Load (manifest_entry, faiss_index, metadata_rows) for the legal corpus, cached.

    faiss is imported lazily so a missing dependency degrades to the keyword
    fallback instead of crashing module import in the unattended scanner.
    """
    import faiss  # lazy

    manifest = json.loads((INDEX_DIR / "index_manifest.json").read_text(encoding="utf-8"))
    entry = manifest[LEGAL_INDEX]
    index = faiss.read_index(str(INDEX_DIR / entry["index_file"]))
    meta = [
        json.loads(line)
        for line in (INDEX_DIR / entry["metadata_sidecar"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    return entry, index, meta


def _retrieve_semantic_records(vector: str, k: int = 5) -> List[Dict[str, str]]:
    """Semantic retrieval over the local nomic-embed FAISS index.

    Mirrors ronin/app/agents/prism_tools.py: embeds the query with the same
    embedder the index was built with (manifest-driven), cosine via an
    L2-normalized IndexFlatIP. Returns {id, clause_text} records, best score
    first — reaching all 104 corpus clauses, not just the JSONs on disk.
    """
    import faiss  # lazy
    import numpy as np  # lazy
    import requests  # lazy

    entry, index, meta = _load_legal_index()
    resp = requests.post(EMBED_URL, json={
        "model": entry["embedder"],
        "input": [entry["query_prefix"] + vector],
    }, timeout=120)
    resp.raise_for_status()
    vec = np.array([resp.json()["data"][0]["embedding"]], dtype=np.float32)
    faiss.normalize_L2(vec)

    scores, ids = index.search(vec, k)
    out = []
    for i in ids[0]:
        if i < 0:
            continue
        rec = meta[i]
        text = rec.get("clause_text", "")
        if text:
            out.append({"id": rec.get("id", ""), "clause_text": text})
    return out


def _retrieve_keyword_records(vector: str) -> List[Dict[str, str]]:
    """Legacy lexical retrieval — substring + word-overlap on the 'vector' field.

    Retained only as a safety net for when the local embedder (LM Studio) or the
    FAISS index is unavailable, so the unattended pipeline never hard-fails.
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
                rec = {"id": clause.get("id", ""), "clause_text": clause_text}
                if vector_lower in clause_vector or clause_vector in vector_lower:
                    direct_matches.append(rec)
                elif vector_words & set(clause_vector.split()):
                    fuzzy_matches.append(rec)
        except Exception:
            continue

    return (direct_matches + fuzzy_matches)[:5]


def _retrieve_records(vector: str) -> List[Dict[str, str]]:
    """Retrieve {id, clause_text} records most relevant to a threat vector.

    Primary path: semantic search over the local nomic-embed FAISS index — the
    same sovereign index ronin's prism queries (intelligent retrieval, not 1990s
    keyword matching). Falls back to lexical matching only if the embedder/index
    is unreachable, so the unattended scanner degrades gracefully.
    """
    try:
        hits = _retrieve_semantic_records(vector)
        if hits:
            return hits[:5]
    except Exception as e:
        print(f"[antibody] semantic retrieval unavailable ({e}); falling back to keyword match")
    return _retrieve_keyword_records(vector)


def _retrieve_relevant_clauses(vector: str) -> List[str]:
    """Clause-text-only view of _retrieve_records (preserves the original contract)."""
    return [r["clause_text"] for r in _retrieve_records(vector)]


def _is_grounded(far_reference: str, corpus_ids: List[str]) -> bool:
    """True only if the drafter's cited reference matches a clause actually retrieved.

    Guards against hallucinated citations: 'VALIDATED' should mean the clause is
    anchored in the corpus context the model was given, not merely long enough.
    Whitespace/case-insensitive and substring-tolerant (e.g. 'DFARS 252.204-7021'
    matches a retrieved id of '252.204-7021'). Note: the DFARS 252.204-7020/7021
    series was renumbered in Feb 2026 — use current numbering for live citations.
    """
    if not far_reference:
        return False
    ref = "".join(far_reference.upper().split())
    for cid in corpus_ids:
        c = "".join(str(cid).upper().split())
        if c and (c in ref or ref in c):
            return True
    return False


# --- Specificity rubric (replaces the old `40 + len//10 + 20` verbosity proxy) ---
# Each pattern is a concrete marker of an *enforceable* clause, not a long one.
_CADENCE_RE = re.compile(
    r"\b(bi-?weekly|weekly|monthly|quarterly|semi-?annual(?:ly)?|annual(?:ly)?|daily|"
    r"per\s+(?:week|month|quarter|year)|every\s+\d+\s+(?:hour|day|week|month)s?|"
    r"within\s+\d+\s+(?:hour|day|business\s+day)s?)\b", re.I)
_QUANTITY_RE = re.compile(
    r"(\$\s?\d|\d+\s?%|\b\d+\s+(?:hours?|days?|months?|years?)\b|"
    r"\bNIST\s+SP\s+\d|\b\d{2,}\b)", re.I)
_ACTOR_RE = re.compile(
    r"\b(contracting\s+officer(?:'?s\s+representative)?|\bCOR\b|c3pao|"
    r"third[-\s]party\s+assessor|independent\s+(?:auditor|assessor|reviewer)|"
    r"inspector\s+general|\bDCAA\b|\bSPRS\b)", re.I)
_TEETH_RE = re.compile(
    r"\b(terminat|penalt|withhold|breach|debar|liquidated\s+damages|suspension|"
    r"forfeit|annul|recover\b|material\s+to\s+(?:payment|the\s+contract))", re.I)


def _score_specificity(clause_text: str, grounded: bool) -> Tuple[int, Dict[str, int]]:
    """Score how *specific and enforceable* a clause is — not how long it is.

    Replaces the old length-based proxy, which rewarded verbosity (any wordy
    clause with the substring 'audit' scored 100). Each signal is a concrete
    marker of an enforceable obligation:
      grounded (30) — cited reference matches a clause actually retrieved
      cadence  (20) — names a verification frequency / deadline
      quantity (15) — names a measurable threshold ($ / % / time / standard)
      actor    (15) — names who verifies or enforces
      teeth    (20) — names a consequence for non-compliance
    Ungrounded clauses cap at 70, so they cannot reach the VALIDATED line (75).
    """
    text = clause_text or ""
    breakdown = {
        "grounded": 30 if grounded else 0,
        "cadence": 20 if _CADENCE_RE.search(text) else 0,
        "quantity": 15 if _QUANTITY_RE.search(text) else 0,
        "actor": 15 if _ACTOR_RE.search(text) else 0,
        "teeth": 20 if _TEETH_RE.search(text) else 0,
    }
    return sum(breakdown.values()), breakdown


def generate(opportunity: Dict[str, Any], threat_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    The main interface for the Antibody Agent. Implements Session B Pipeline.

    Returns a dict with clause_title, clause_text, specificity_score, far_reference,
    validation_status, and economic_calibration.
    """
    vector = threat_assessment.get("primary_vector", "General Fraud")
    roi_multiplier = threat_assessment.get("cost_of_fraud_roi", {}).get("roi_multiplier", 5)
    title = opportunity.get("title", "Unknown Project")

    # 1. Retrieval Gate — local semantic corpus (records carry clause ids for grounding)
    records = _retrieve_records(vector)
    relevant_legal_text = [r["clause_text"] for r in records]
    corpus_ids = [r["id"] for r in records if r.get("id")]

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
        m26_records = _retrieve_records("vendor disclosure llm ai transparency")
        corpus_ids += [r["id"] for r in m26_records if r.get("id")]
        m26_policy_snippet = "\n".join(f"- POLICY: {r['clause_text']}" for r in m26_records[:3])
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
        # Grounding: the cited reference must match a clause actually retrieved,
        # not a number the drafter invented. The specificity rubric scores
        # enforceable substance (cadence/quantity/actor/teeth), not length.
        # VALIDATED therefore reflects a grounded, enforceable clause.
        clause_text = draft.get("clause_text", "")
        far_reference = draft.get("far_reference")
        grounded = _is_grounded(far_reference or "", corpus_ids)
        specificity_score, specificity_breakdown = _score_specificity(clause_text, grounded)

        return {
            "clause_title": draft.get("clause_title"),
            "clause_text": clause_text,
            "specificity_score": specificity_score,
            "specificity_breakdown": specificity_breakdown,
            "far_reference": far_reference,
            "grounded": grounded,
            "rationale": draft.get("rationale"),
            "validation_status": "VALIDATED" if (specificity_score >= 75 and grounded) else "NEEDS_REVIEW",
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
