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


def generate_completion(
    messages: List[dict],
    system_prompt: str,
    max_tokens: int = 1024,
) -> str:
    """Generate completion using the active LLM provider (Groq or Anthropic)."""
    provider = get_active_provider()

    if provider == "groq":
        client = get_groq_client()
        groq_messages = [{"role": "system", "content": system_prompt}] + messages
        model_name = os.environ.get("GROQ_MODEL") or GROQ_MODEL or "openai/gpt-oss-120b"
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=groq_messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            # Fallback if specific model is not enabled on this Groq account
            if "model_not_found" in str(exc) or "does not exist" in str(exc):
                fallback_model = "openai/gpt-oss-120b"
                if model_name != fallback_model:
                    response = client.chat.completions.create(
                        model=fallback_model,
                        messages=groq_messages,
                        max_tokens=max_tokens,
                    )
                else:
                    raise exc
            else:
                raise exc
        choice = response.choices[0]
        return choice.message.content or ""

    if provider == "anthropic":
        client = get_anthropic_client()
        response = client.messages.create(
            model=os.environ.get("CLAUDE_MODEL", CLAUDE_MODEL),
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    raise RuntimeError(f"Unsupported LLM provider: {provider}")
