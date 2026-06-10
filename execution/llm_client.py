"""
Unified LLM client — local → Venice → Anthropic fallback chain.

Provider priority:
  1. Local LM Studio  (free, instant, Qwen3-8b on RAZZOR-FACCE, OpenAI-compatible)
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
"""

import os
import socket
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "").strip()
VENICE_API_KEY     = os.getenv("VENICE_API_KEY", "").strip()
LOCAL_BASE_URL     = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
VENICE_BASE_URL    = "https://api.venice.ai/api/v1"
LLM_MODE           = os.getenv("LLM_MODE", "auto").lower()

# Last provider that successfully served a completion, e.g. "local (qwen3-8b)".
# Read via get_last_provider() so callers can report the actual serving tier.
LAST_PROVIDER = None

# Model assignments
# "fast"    — bulk analysis (gemini_analyst.py): cheap + quick
# "precise" — legal drafting (antibody_agent.py): higher quality floor
LOCAL_MODEL_FAST    = os.getenv("LOCAL_MODEL_FAST",    "qwen3-8b")
LOCAL_MODEL_PRECISE = os.getenv("LOCAL_MODEL_PRECISE", "qwen3-8b")
VENICE_MODEL_FAST   = os.getenv("VENICE_MODEL_FAST",   "llama-3.3-70b")
VENICE_MODEL_PRECISE= os.getenv("VENICE_MODEL_PRECISE","llama-3.3-70b")
ANTHROPIC_MODEL     = os.getenv("ANTHROPIC_MODEL",     "claude-sonnet-4-6")


def _local_available() -> bool:
    """Quick TCP check — is LM Studio listening on localhost:1234?"""
    try:
        host, port = LOCAL_BASE_URL.replace("http://", "").replace("/v1", "").split(":")
        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except Exception:
        return False


def _try_local(prompt: str, system: str | None, mode: str) -> str | None:
    try:
        from openai import OpenAI
        model = LOCAL_MODEL_PRECISE if mode == "precise" else LOCAL_MODEL_FAST
        client = OpenAI(api_key="not-needed", base_url=LOCAL_BASE_URL)
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
        LAST_PROVIDER = f"local ({model})"
        print(f"    [LLM] local ({model})")
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
