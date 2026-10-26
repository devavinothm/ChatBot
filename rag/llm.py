import os
from typing import List, Optional

from dotenv import load_dotenv

from .config import CLAUDE_MODEL, GROQ_MODEL, LLM_PROVIDER

_cached_groq_key = None
_groq_client = None

_cached_anthropic_key = None
_anthropic_client = None

PLACEHOLDER_KEYS = {
    "",
    "your-anthropic-api-key-here",
    "your-groq-api-key-here",
}


def _is_valid_key(val: Optional[str]) -> bool:
    return bool(val and val.strip() and val.strip() not in PLACEHOLDER_KEYS)


def get_active_provider() -> str:
    # Always reload .env so edits to .env take effect immediately without server restart
    load_dotenv(override=True)
    provider = (os.environ.get("LLM_PROVIDER") or LLM_PROVIDER or "auto").strip().lower()
    if provider in ("groq", "anthropic"):
        return provider

    # Auto detection: check for populated API keys
    groq_key = os.environ.get("GROQ_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if _is_valid_key(groq_key):
        return "groq"
    if _is_valid_key(anthropic_key):
        return "anthropic"

    # Default fallback when neither has a valid key
    return "groq" if groq_key is not None else "anthropic"


def get_anthropic_client():
    global _anthropic_client, _cached_anthropic_key
    load_dotenv(override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not _is_valid_key(api_key):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set or contains a placeholder. "
            "Add your valid Anthropic API key to .env, or use Groq by setting GROQ_API_KEY."
        )
    if _anthropic_client is None or _cached_anthropic_key != api_key:
        from anthropic import Anthropic

        _anthropic_client = Anthropic(api_key=api_key)
        _cached_anthropic_key = api_key
    return _anthropic_client


def get_groq_client():
    global _groq_client, _cached_groq_key
    load_dotenv(override=True)
    api_key = os.environ.get("GROQ_API_KEY")
    if not _is_valid_key(api_key):
        raise RuntimeError(
            "GROQ_API_KEY is not set or contains a placeholder. "
            "Add your valid Groq API key to .env, or set LLM_PROVIDER=anthropic."
        )
    if _groq_client is None or _cached_groq_key != api_key:
        from groq import Groq

        _groq_client = Groq(api_key=api_key)
        _cached_groq_key = api_key
    return _groq_client


COST_TIERS = {
    "tier1": {
        "id": "tier1",
        "name": "Tier 1: Lowest Cost",
        "badge": "$",
        "groq_model": "openai/gpt-oss-20b",
        "claude_model": "claude-3-haiku-20240307",
        "default_max_tokens": 450,
        "description": "Minimal token overhead. Zero metric data loaded; pure document/policy grounding.",
    },
    "tier2": {
        "id": "tier2",
        "name": "Tier 2: Mid-Level Cost (Single Metric)",
        "badge": "$$",
        "groq_model": "openai/gpt-oss-20b",
        "claude_model": "claude-3-5-haiku-20241022",
        "default_max_tokens": 750,
        "description": "Cost-optimized single-metric slice. Injects only the active metric to minimize input tokens.",
    },
    "tier3": {
        "id": "tier3",
        "name": "Tier 3: Flagship Primary (Multi-Metric)",
        "badge": "$$$",
        "groq_model": "openai/gpt-oss-120b",
        "claude_model": "claude-sonnet-5",
        "default_max_tokens": 1400,
        "description": "Full multi-metric analytical engine with historical 6-month trends and what-if simulation.",
    },
}


def generate_completion(
    messages: List[dict],
    system_prompt: str,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    tier: Optional[str] = None,
) -> str:
    """Generate completion using the active LLM provider (Groq or Anthropic) with tiered cost optimization."""
    provider = get_active_provider()
    tier_info = COST_TIERS.get(tier, {}) if tier else {}

    if max_tokens is None:
        max_tokens = tier_info.get("default_max_tokens", 1024)

    if provider == "groq":
        client = get_groq_client()
        groq_messages = [{"role": "system", "content": system_prompt}] + messages
        model_name = (
            model
            or tier_info.get("groq_model")
            or os.environ.get("GROQ_MODEL")
            or GROQ_MODEL
            or "openai/gpt-oss-120b"
        )
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=groq_messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            # Fallback if specific model is not enabled on this Groq account
            fallback_model = "openai/gpt-oss-120b"
            if model_name != fallback_model:
                response = client.chat.completions.create(
                    model=fallback_model,
                    messages=groq_messages,
                    max_tokens=max_tokens,
                )
            else:
                raise exc
        choice = response.choices[0]
        return choice.message.content or ""

    if provider == "anthropic":
        client = get_anthropic_client()
        claude_model_name = (
            model
            or tier_info.get("claude_model")
            or os.environ.get("CLAUDE_MODEL", CLAUDE_MODEL)
        )
        response = client.messages.create(
            model=claude_model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    raise RuntimeError(f"Unsupported LLM provider: {provider}")
