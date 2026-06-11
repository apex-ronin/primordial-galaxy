"""
Health check — verifies live dependencies before pipeline runs.

GCP / Vertex / Gemini checks removed 2026-06-06 (all projects deleted).
Local-primary architecture: Anthropic API + SAM.gov + CSDA + local corpus.

Critical checks abort the run. Non-critical checks warn and continue.
"""

import glob
import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "legal_corpus")

# Local nomic-embed FAISS retrieval (mirrors antibody_agent / prism_tools config).
INDEX_DIR = Path(os.environ.get("RONIN_INDEX_DIR", r"G:\AI-Models\indexes"))
EMBED_URL = os.environ.get(
    "LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"
).rstrip("/") + "/embeddings"


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


def check_local_embedder():
    """Advisory — antibody semantic retrieval needs the local nomic-embed endpoint.

    If LM Studio is down, the antibody agent silently falls back to keyword
    matching (degraded). This surfaces that as a visible WARN in the run log so a
    cold/failed embedder doesn't quietly cripple retrieval on an unattended run.
    """
    print("[*] Checking local embedder (nomic via LM Studio)...")
    manifest_path = INDEX_DIR / "index_manifest.json"
    if not manifest_path.exists():
        return False, f"Index manifest not found at {manifest_path} — retrieval will use keyword fallback"
    try:
        embedder = json.loads(manifest_path.read_text(encoding="utf-8"))["legal_corpus"]["embedder"]
    except Exception as e:
        return False, f"Could not read embedder from manifest: {e}"
    try:
        resp = requests.post(
            EMBED_URL,
            json={"model": embedder, "input": ["search_query: health check"]},
            timeout=8,
        )
        if resp.status_code != 200:
            return False, f"Status {resp.status_code} — antibody falls back to keyword retrieval"
        dims = len(resp.json()["data"][0]["embedding"])
        return True, f"OK ({embedder}, {dims}-dim)"
    except Exception as e:
        return False, f"Unreachable at {EMBED_URL} ({e}) — antibody falls back to keyword retrieval"


# Checks marked True are CRITICAL — pipeline exits if they fail.
# Checks marked False are advisory — pipeline continues with degraded output.
CHECKS = [
    ("Anthropic API",      check_anthropic_api,      False),  # advisory — keyword fallback exists
    ("SAM.gov",            check_sam_api,             False),  # advisory — other sources still run
    ("CSDA (Honey Pot)",   check_csda_clearinghouse,  False),  # advisory
    ("Local Corpus",       check_local_corpus,        True),   # critical — antibody agent needs this
    ("Local Embedder",     check_local_embedder,      False),  # advisory — degrades to keyword retrieval
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
