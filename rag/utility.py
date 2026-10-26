import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .llm import generate_completion
from .store_data import get_utility_store_summary

UTILITY_SYSTEM_PROMPT = """You are Utility Minion, the creative execution and content generation specialist for Giri's Fried Chicken and Gimbll merchants.
Your role is to craft high-converting e-commerce copy, product descriptions, marketing campaigns, email sequences, ad creatives, and image generation specifications.

Core Capabilities:
1. Product & Content Copywriting:
   - Compelling, sensory-rich product titles, bullets, and long descriptions.
   - 3-step abandoned checkout email & SMS sequences.
   - High-ROAS Google Shopping headlines and Meta ad copy.
2. Formatted & Editable Drafts:
   - Provide copy in ready-to-use, clean blocks with Subject lines, Preview text, and Body.
3. Multi-Channel & Ad Sizing Specs:
   - Specify aspect ratios (e.g. 1:1 Square Feed, 9:16 Story/Reels, 1.91:1 Google/Landscape) and image generation prompts when visual assets are requested.
4. Brand Consistency:
   - Maintain Giri's Fried Chicken voice: mouth-watering, artisanal, crispy, confident, appetizing, and compliant with food handling policies.

Always conclude your output with this exact metadata block when a creative draft is produced:
```utility_draft
{
  "content_type": "Email Sequence" | "Product Description" | "Ad Campaign" | "Image Prompt" | "General Copy",
  "target_channel": "Email / SMS / Shopify / Meta / Google",
  "headline": "Short title of the draft",
  "word_count_estimate": 150
}
```
"""

DRAFT_PATTERN = re.compile(
    r"```(?:utility_draft|json)?\s*(\{[\s\S]*?\"content_type\"[\s\S]*?\})\s*```", re.DOTALL
)


def extract_utility_draft(text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extract and parse the utility_draft JSON block from LLM output."""
    match = DRAFT_PATTERN.search(text)
    if match:
        json_str = match.group(1)
        clean_text = DRAFT_PATTERN.sub("", text).strip()
        try:
            draft_data = json.loads(json_str)
            return clean_text, draft_data
        except Exception:
            pass
    return text, None


def answer_utility(
    question: str,
    history: list,
    current_draft: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Generate marketing, product copy, or image creative draft using Utility Minion."""
    store_summary = get_utility_store_summary()

    context_prompt = (
        f"{store_summary}\n\n"
        f"Active Draft Context: {json.dumps(current_draft) if current_draft else 'None'}\n\n"
        f"Merchant Request: {question}"
    )

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": context_prompt})

    raw_answer = generate_completion(
        messages=messages,
        system_prompt=UTILITY_SYSTEM_PROMPT,
        max_tokens=1400,
    )

    clean_answer, draft_data = extract_utility_draft(raw_answer)
    return clean_answer, draft_data
