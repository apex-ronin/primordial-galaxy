"""
Unified LLM client — local → Venice → Anthropic fallback chain.

Provider priority:
  1. Local Ollama     (free, CPU-only, gemma4:12b on RAZZOR-FACCE, native API)
  2. Venice AI        (paid credits, OpenAI-compatible, https://api.venice.ai/api/v1)
  3. Anthropic API    (paid credits, direct SDK)

Set LLM_MODE in .env to override:
  LLM_MODE=local    — local only, no fallback
  LLM_MODE=venice   — Venice only
  LLM_MODE=anthropic — Anthropic only
  LLM_MODE=auto     — full cascade (default)

Usage:
    from llm_client import complete
    result = complete(prompt, system="...", mode="fast")   # bulk analysis
    result = complete(prompt, system="...", mode="precise") # precision drafting

Local tier rewired 2026-08-11 (Jay's directive, after catching the cascade
running 100% Venice with the local tier silently dead since the 2026-08-10
LM Studio removal). Now hits Ollama's NATIVE /api/chat directly (same
precedent as observatory/embed_corpus.py's embedding calls) rather than the
OpenAI-compat shim, specifically so the resource caps below are reliably
honored rather than hoped-for through a compatibility layer:
  - num_gpu=24 (of gemma4:12b's 48 layers -- 50%), num_thread=~50% of logical
    cores. Jay's standing rule as of 2026-08-11: he's since gone back through
    the physical hardware himself and confirmed it; cap both CPU and GPU at
    50% and otherwise run normally, don't add extra caution beyond the cap.
    History for context (see [[hardware-crash-under-local-compute]]): the box
    hard-crashed under sustained local inference in both GPU (15-20 min) and
    CPU-only (40 min) modes on 2026-06-30, and separately an RX580
    display-driver TDR was root-caused on 2026-06-21 (GPU offload contends
    with the display driver since the RX580 is this box's sole display GPU).
    Both were live concerns until Jay's hardware pass; the 50% cap is the
    current standing rule, not a substitute for it.
"""

import os
import socket
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "").strip()
VENICE_API_KEY     = os.getenv("VENICE_API_KEY", "").strip()
LOCAL_BASE_URL     = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434")
VENICE_BASE_URL    = "https://api.venice.ai/api/v1"
LLM_MODE           = os.getenv("LLM_MODE", "auto").lower()

# Jay's 2026-08-11 standing rule: local compute capped at 50% CPU and 50% GPU
# (see module docstring). 24 = half of gemma4:12b's 48 layers -- recompute if
# the local model changes (`ollama show <model>` -> model_info block_count).
# Override via env if the box's core count or the rule itself changes; do not
# silently raise either cap.
LOCAL_CPU_THREAD_CAP = int(os.getenv("LOCAL_CPU_THREAD_CAP", max(1, (os.cpu_count() or 2) // 2)))
LOCAL_NUM_GPU = int(os.getenv("LOCAL_NUM_GPU", "24"))

# Last provider that successfully served a completion, e.g. "local (gemma4:12b)".
# Read via get_last_provider() so callers can report the actual serving tier.
LAST_PROVIDER = None

# Model assignments
# "fast"    — bulk analysis (gemini_analyst.py — name is legacy, no Gemini): cheap + quick
# "precise" — legal drafting (antibody_agent.py): higher quality floor
LOCAL_MODEL_FAST    = os.getenv("LOCAL_MODEL_FAST",    "gemma4:12b")
LOCAL_MODEL_PRECISE = os.getenv("LOCAL_MODEL_PRECISE", "gemma4:12b")
VENICE_MODEL_FAST   = os.getenv("VENICE_MODEL_FAST",   "llama-3.3-70b")
VENICE_MODEL_PRECISE= os.getenv("VENICE_MODEL_PRECISE","llama-3.3-70b")
ANTHROPIC_MODEL     = os.getenv("ANTHROPIC_MODEL",     "claude-sonnet-4-6")


def _local_available() -> bool:
    """Quick TCP check — is Ollama listening?"""
    try:
        host_port = LOCAL_BASE_URL.split("://", 1)[-1]
        host, port = host_port.split(":")
        with socket.create_connection((host, int(port.rstrip("/"))), timeout=1):
            return True
    except Exception:
        return False


def _try_local(prompt: str, system: str | None, mode: str) -> str | None:
    try:
        import requests
        model = LOCAL_MODEL_PRECISE if mode == "precise" else LOCAL_MODEL_FAST
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_gpu": LOCAL_NUM_GPU, "num_thread": LOCAL_CPU_THREAD_CAP},
        }
        resp = requests.post(f"{LOCAL_BASE_URL}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        global LAST_PROVIDER
        LAST_PROVIDER = f"local ({model})"
        print(f"    [LLM] local ({model}, num_gpu={LOCAL_NUM_GPU}, num_thread={LOCAL_CPU_THREAD_CAP})")
        return text
    except Exception as e:
        print(f"    [LLM] local failed: {e}")
        return None


def _try_venice(prompt: str, system: str | None, mode: str) -> str | None:
    if not VENICE_API_KEY:
        return None
    try:
        from openai import OpenAI
        model = VENICE_MODEL_PRECISE if mode == "precise" else VENICE_MODEL_FAST
        client = OpenAI(api_key=VENICE_API_KEY, base_url=VENICE_BASE_URL)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
        )
        text = response.choices[0].message.content.strip()
        global LAST_PROVIDER
        LAST_PROVIDER = f"venice ({model})"
        print(f"    [LLM] venice ({model})")
        return text
    except Exception as e:
        print(f"    [LLM] venice failed: {e}")
        return None


def _try_anthropic(prompt: str, system: str | None) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        kwargs = {"model": ANTHROPIC_MODEL, "max_tokens": 4096,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        text = response.content[0].text.strip()
        global LAST_PROVIDER
        LAST_PROVIDER = f"anthropic ({ANTHROPIC_MODEL})"
        print(f"    [LLM] anthropic ({ANTHROPIC_MODEL})")
        return text
    except Exception as e:
        print(f"    [LLM] anthropic failed: {e}")
        return None


def get_last_provider() -> str | None:
    """Tier that served the most recent successful complete(), e.g. 'local (qwen3-8b)'."""
    return LAST_PROVIDER


def complete(prompt: str, system: str | None = None, mode: str = "fast") -> str | None:
    """
    Send a prompt through the provider cascade and return the raw text response.

    Args:
        prompt:  User message content.
        system:  Optional system prompt.
        mode:    "fast" (bulk) or "precise" (legal drafting).

    Returns:
        Raw text string, or None if all providers fail.
    """
    if LLM_MODE == "local":
        return _try_local(prompt, system, mode)

    if LLM_MODE == "venice":
        return _try_venice(prompt, system, mode)

    if LLM_MODE == "anthropic":
        return _try_anthropic(prompt, system)

    # auto — full cascade
    if _local_available():
        result = _try_local(prompt, system, mode)
        if result:
            return result

    result = _try_venice(prompt, system, mode)
    if result:
        return result

    return _try_anthropic(prompt, system)


if __name__ == "__main__":
    print("Provider status:")
    print(f"  Local available : {_local_available()} ({LOCAL_BASE_URL})")
    print(f"  Venice key set  : {bool(VENICE_API_KEY)}")
    print(f"  Anthropic key   : {bool(ANTHROPIC_API_KEY)}")
    print(f"  Mode            : {LLM_MODE}")
    print()
    result = complete("Say 'LLM client working' and nothing else.", mode="fast")
    print(f"Response: {result}")
