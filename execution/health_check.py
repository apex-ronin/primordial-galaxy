"""
Health check — verifies live dependencies before pipeline runs.

GCP / Vertex / Gemini checks removed 2026-06-06 (all projects deleted).
Local-primary architecture: Anthropic API + SAM.gov + CSDA + local corpus.

Critical checks abort the run. Non-critical checks warn and continue.
"""

import glob
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "legal_corpus")


def check_anthropic_api():
    """Critical — AI analysis falls back to keywords if key missing, but log it clearly."""
    print("[*] Checking Anthropic API key...")
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return False, "ANTHROPIC_API_KEY not set — analysis will use keyword fallback only"
    if not key.startswith("sk-ant-"):
        return False, "ANTHROPIC_API_KEY format unexpected (expected sk-ant-...)"
    return True, "OK"


def check_sam_api():
    print("[*] Checking SAM.gov API...")
    api_key = os.getenv("SAM_API_KEY")
    if not api_key:
        return False, "Missing SAM_API_KEY"
    url = "https://api.sam.gov/opportunities/v2/search"
    params = {
        "api_key": api_key,
        "limit": 1,
        "postedFrom": "01/01/2026",
        "postedTo": "01/02/2026",
        "active": "true",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return True, "OK"
        return False, f"Status {response.status_code} — {response.text[:100]}"
    except Exception as e:
        return False, str(e)


def check_csda_clearinghouse():
    print("[*] Checking CSDA Clearinghouse...")
    try:
        response = requests.get(
            "https://www.csda.net/career-center/rfp-clearinghouse", timeout=10
        )
        if response.status_code == 200:
            return True, "OK"
        return False, f"Status {response.status_code}"
    except Exception as e:
        return False, str(e)


def check_local_corpus():
    """Verify legal corpus source files are on disk — corpus is local-only post-GCP teardown."""
    print("[*] Checking local legal corpus...")
    files = glob.glob(os.path.join(CORPUS_DIR, "*.json"))
    if not files:
        return False, f"No corpus JSON files found in {CORPUS_DIR}"
    return True, f"{len(files)} corpus files present"


# Checks marked True are CRITICAL — pipeline exits if they fail.
# Checks marked False are advisory — pipeline continues with degraded output.
CHECKS = [
    ("Anthropic API",      check_anthropic_api,      False),  # advisory — keyword fallback exists
    ("SAM.gov",            check_sam_api,             False),  # advisory — other sources still run
    ("CSDA (Honey Pot)",   check_csda_clearinghouse,  False),  # advisory
    ("Local Corpus",       check_local_corpus,        True),   # critical — antibody agent needs this
]


def run_all_checks() -> bool:
    """
    Run all health checks. Returns True only if no CRITICAL checks failed.
    Advisory failures are printed but do not affect the return value.
    """
    print("=" * 40)
    print("     SYSTEM HEALTH CHECK")
    print("=" * 40)

    critical_failed = False
    for name, fn, is_critical in CHECKS:
        passed, msg = fn()
        tag = "[PASS]" if passed else ("[CRITICAL]" if is_critical else "[WARN] ")
        print(f"{tag} | {name}: {msg}")
        if not passed and is_critical:
            critical_failed = True

    print("-" * 40)
    if critical_failed:
        print("[!!!] CRITICAL check(s) failed — aborting pipeline.")
    return not critical_failed

if __name__ == "__main__":
    run_all_checks()
