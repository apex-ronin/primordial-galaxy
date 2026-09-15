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
  - num_gpu=31 (of gemma4:12b's 48 layers -- 65%), num_thread=~65% of logical
    cores. History same day (2026-08-30): 50% ran clean (sequential, zero
    crash/TDR) after the CPU fan replacement + GTX760 display-offload +
    GGML_VK_VISIBLE_DEVICES=1 fix (see [[hardware-crash-under-local-compute]]
    for the full 08-24/08-29/08-30 retest history). Raised to 85% -> produced
    a real amdwddmg TDR (event 4101) ~14min into a SEQUENTIAL-ONLY test, no
    concurrency involved, and generation output silently degraded (fast,
    truncated) for the rest of the run without the API erroring -- worse than
    a clean failure, since a caller would trust the bad output. Dropped to
    65% as a deliberate midpoint, not yet validated. Also notable: the TDR
    happened on compute-only load (GTX760 handles display now) -- the
    original "RX580=display-GPU=TDR-risk" theory was incomplete; heavy
    Vulkan compute alone can still trigger amdwddmg. The concurrent-load test
    for the separate suspected PSU/power-delivery mechanism still hasn't been
    re-run since the hardware fixes -- don't conflate the two failure modes.
  - timeout=450s (was 180s, raised same session): the original 180s ceiling
    was cutting off legitimate slow generations under the 50% cap, not actual
    hangs -- one successful 847-char response took 176s, right at the old
    edge. 3 of 8 sequential test calls failed this way before the fix; that
    was a timeout-too-short bug, not a hardware/GPU stability finding.
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

# Jay's 2026-08-30 65%-CPU/GPU cap (LOCAL_NUM_GPU=31, [[hardware-crash-under-local-compute]])
# was a response to a real amdwddmg TDR crash on RAZZOR-FACCE's RX580 under sustained
# local generation -- that's the old Taichi X370 box's discrete GPU. 2026-09:
# migrated to the primordial-galaxy node, which has no discrete GPU at all (Intel
# UHD 630 integrated only) -- the TDR failure mode this cap guarded against doesn't
# exist on this hardware, so the throttle is lifted here. Unset (None) -> the key
# is omitted from the request options below so Ollama auto-tunes; set either env
# var to a positive int to force a specific cap again if a future box needs it.
LOCAL_CPU_THREAD_CAP = int(os.environ["LOCAL_CPU_THREAD_CAP"]) if os.getenv("LOCAL_CPU_THREAD_CAP") else None
LOCAL_NUM_GPU = int(os.environ["LOCAL_NUM_GPU"]) if os.getenv("LOCAL_NUM_GPU") else None

# 2026-09-10: found live via observatory/procurement_watch.py extraction calls --
# a prompt complex enough to need real judgment (gemma4 spends tokens on a
# separate "thinking" field before ever writing the actual answer) returned
# HTTP 200 with an EMPTY content field, done_reason "length", eval_count stuck
# at ~925 regardless of num_predict -- a silent-success failure, not an
# exception a caller would notice without checking the actual text.
# num_predict was NOT the cause (raising it to 8192 changed nothing, eval_count
# stayed at 925) -- verified live it's Ollama's default num_ctx (context
# window), too small to hold the ~3.2K-token prompt plus a real response.
# Explicit num_ctx=16384 fixed it: done_reason "stop", eval_count 3457, real
# content. The model's own max is 131K; 16384 is a generous-but-not-max
# default, override via env for a specific request shape if ever needed.
LOCAL_NUM_PREDICT = int(os.environ["LOCAL_NUM_PREDICT"]) if os.getenv("LOCAL_NUM_PREDICT") else 8192
LOCAL_NUM_CTX = int(os.environ["LOCAL_NUM_CTX"]) if os.getenv("LOCAL_NUM_CTX") else 16384

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


def _try_local(prompt: str, system: str | None, mode: str, json_mode: bool = False) -> str | None:
    try:
        import requests
        model = LOCAL_MODEL_PRECISE if mode == "precise" else LOCAL_MODEL_FAST
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        options = {"num_predict": LOCAL_NUM_PREDICT, "num_ctx": LOCAL_NUM_CTX}
        if LOCAL_NUM_GPU is not None:
            options["num_gpu"] = LOCAL_NUM_GPU
        if LOCAL_CPU_THREAD_CAP is not None:
            options["num_thread"] = LOCAL_CPU_THREAD_CAP
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if json_mode:
            # 2026-09-06 fix: a live 65-item pipeline run found 7/65 (11%) of scoring
            # calls silently degrading to the keyword-fallback placeholder path, all
            # from the identical "Expecting ',' delimiter" json.loads error -- the
            # small local model (gemma4:e2b) occasionally emits an unescaped quote
            # inside a JSON string field. Prompt instructions ("output strictly valid
            # JSON") only make this less likely; Ollama's grammar-constrained decoding
            # (this flag) makes malformed JSON structurally impossible instead of just
            # less probable -- it's the actual fix, not a retry/repair band-aid.
            payload["format"] = "json"
        resp = requests.post(f"{LOCAL_BASE_URL}/api/chat", json=payload, timeout=450)
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        global LAST_PROVIDER
        LAST_PROVIDER = f"local ({model})"
        capped = LOCAL_NUM_GPU is not None or LOCAL_CPU_THREAD_CAP is not None
        cap_note = f", num_gpu={LOCAL_NUM_GPU}, num_thread={LOCAL_CPU_THREAD_CAP}" if capped else ", uncapped"
        print(f"    [LLM] local ({model}{cap_note})")
        return text
    except Exception as e:
        print(f"    [LLM] local failed: {e}")
        return None


def _try_venice(prompt: str, system: str | None, mode: str, json_mode: bool = False) -> str | None:
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
        kwargs = {"model": model, "messages": messages, "max_tokens": 4096}
        if json_mode:
            # Same fix as _try_local's format="json" -- OpenAI-compatible constrained
            # decoding, so a Venice-served call gets the same JSON-validity guarantee.
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
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


def complete(prompt: str, system: str | None = None, mode: str = "fast",
             json_mode: bool = False) -> str | None:
    """
    Send a prompt through the provider cascade and return the raw text response.

    Args:
        prompt:    User message content.
        system:    Optional system prompt.
        mode:      "fast" (bulk) or "precise" (legal drafting).
        json_mode: True forces grammar-constrained JSON output on local (Ollama
                   format="json") and Venice (OpenAI-compat response_format).
                   Pass True for every JSON-schema caller (gemini_analyst,
                   antibody_agent, red_team_simulation) -- prompt instructions
                   alone ("output strictly valid JSON") only make malformed JSON
                   less likely; this makes it structurally impossible on the
                   tiers that support it. Leave False for prose callers (aaas_poc).
                   Anthropic has no equivalent flag here; unaffected either way.

    Returns:
        Raw text string, or None if all providers fail.
    """
    if LLM_MODE == "local":
        return _try_local(prompt, system, mode, json_mode)

    if LLM_MODE == "venice":
        return _try_venice(prompt, system, mode, json_mode)

    if LLM_MODE == "anthropic":
        return _try_anthropic(prompt, system)

    # auto — full cascade
    if _local_available():
        result = _try_local(prompt, system, mode, json_mode)
        if result:
            return result

    result = _try_venice(prompt, system, mode, json_mode)
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
