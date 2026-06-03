# OMB M-26-04 (Dec 11 2025, implementing EO 14319) — Unbiased AI Principles disclosure
# Primary source: https://www.whitehouse.gov/omb/memoranda/m-26-04/
# Required on any procurement-facing output. Stamp with stamp_disclosure() before submission.

_DISCLOSURE = """\
--- AI DISCLOSURE (OMB M-26-04) ---
This output was produced with AI assistance and is subject to human review before use in any
procurement or contract action.

1. Conformance: This system is designed to operate in accordance with OMB M-26-04's two
   Unbiased AI Principles — truth-seeking (outputs reflect evidence, not desired conclusions)
   and ideological neutrality (no partisan slant introduced by model or prompt design).

2. Model transparency: Built on Vertex AI / Google Gemini and Anthropic Claude via Vertex.
   No proprietary training data from end-user interactions is used.

3. Acceptable use: Output is provided for analytical support only. It does not constitute
   legal advice, a binding compliance determination, or an agency decision.

4. Feedback: To report a biased, inaccurate, or non-compliant output contact the system
   owner directly. [CONTACT_PLACEHOLDER — replace with jay@apexronin.com once domain live]
--- END DISCLOSURE ---
"""


def stamp_disclosure(artifact: str) -> str:
    """Append the M-26-04 disclosure block to any procurement-facing artifact."""
    return artifact.rstrip() + "\n\n" + _DISCLOSURE
