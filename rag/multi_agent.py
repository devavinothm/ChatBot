import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .chat import answer_question
from .guidance import answer_guidance
from .llm import generate_completion
from .solution import answer_solution
from .store_data import (
    get_guidance_store_summary,
    get_single_metric_summary,
    get_solution_store_summary,
    get_utility_store_summary,
)
from .utility import answer_utility
from .vector_store import VectorStore

AGENT_REGISTRY = {
    "information_escort": {
        "id": "information_escort",
        "name": "Information Escort",
        "icon": "📚",
        "tab_id": "information-escort",
        "role": "Policy & Compliance (Tier 1 • Lowest Cost)",
        "cost_tier": "tier1",
        "cost_badge": "$",
        "description": "Lowest cost tier. Grounds answers in merchant agreements, commission tiers, SLAs, and perishable return rules without metric database overhead.",
    },
    "guidance_guru": {
        "id": "guidance_guru",
        "name": "Guidance Guru",
        "icon": "🧭",
        "tab_id": "guidance-guru",
        "role": "Single-Metric Coaching (Tier 2 • Mid Cost)",
        "cost_tier": "tier2",
        "cost_badge": "$$",
        "description": "Specializes strictly in single-metric analysis (e.g. Conversion Rate in isolation, Revenue gap, or AOV) using a lean context slice to optimize token cost.",
    },
    "solution_mate": {
        "id": "solution_mate",
        "name": "Solution Mate",
        "icon": "💡",
        "tab_id": "solution-mate",
        "role": "Multi-Metric Diagnostic (Tier 3 • Primary Engine)",
        "cost_tier": "tier3",
        "cost_badge": "$$$",
        "description": "Primary flagship engine deployed when accessing more than two metrics, historical 6-month trends, channel ROAS/CAC tradeoffs, and what-if simulations.",
    },
    "utility_minion": {
        "id": "utility_minion",
        "name": "Utility Minion",
        "icon": "🛠️",
        "tab_id": "utility-minion",
        "role": "Creative Execution & Copywriting (Tier 1 • Low Cost)",
        "cost_tier": "tier1",
        "cost_badge": "$",
        "description": "Generates marketing copy, abandoned cart email flows, product descriptions, and image creative briefs.",
    },
}

METRIC_REGISTRY = {
    "revenue": {
        "id": "revenue",
        "name": "Monthly Revenue",
        "keywords": [
            "revenue", "sales", "monthly sales", "monthly revenue", "$50k", "$50,000",
            "$24.8k", "$24,850", "revenue gap", "$25,150", "topline", "gross sales",
            "plateaued", "plateau", "revenue target"
        ],
        "current": "$24,850.00/mo",
        "target": "$50,000.00/mo",
    },
    "conversion_rate": {
        "id": "conversion_rate",
        "name": "Conversion Rate",
        "keywords": [
            "conversion rate", "conversion rates", "conversion", "checkout abandonment",
            "abandonment rate", "abandonment rates", "funnel leak", "checkout leak",
            "add-to-cart", "add to cart", "checkout conversion", "1.80%", "2.80%", "cr"
        ],
        "current": "1.80%",
        "target": "2.80% (Benchmark)",
    },
    "orders": {
        "id": "orders",
        "name": "Monthly Orders",
        "keywords": [
            "orders", "order volume", "monthly orders", "number of orders",
            "order count", "order impact", "380 orders", "760 orders", "units sold"
        ],
        "current": "380 orders/mo",
        "target": "760 orders/mo",
    },
    "average_order_value": {
        "id": "average_order_value",
        "name": "Average Order Value (AOV)",
        "keywords": [
            "aov", "average order value", "order value", "basket size",
            "ticket size", "bundle", "bundling", "$65.40", "$74.50"
        ],
        "current": "$65.40",
        "target": "$74.50",
    },
    "traffic": {
        "id": "traffic",
        "name": "Store Traffic / Sessions",
        "keywords": [
            "traffic", "sessions", "visitors", "store sessions", "store traffic",
            "page views", "site visitors", "21,100", "21100"
        ],
        "current": "21,100 sessions/mo",
        "target": "30,000 sessions/mo",
    },
    "cac": {
        "id": "cac",
        "name": "Customer Acquisition Cost (CAC)",
        "keywords": [
            "cac", "customer acquisition cost", "acquisition cost", "cost per customer",
            "cost to acquire", "$22.50", "$27.60", "$16.20"
        ],
        "current": "$22.50 blended",
        "target": "$16.00 target",
    },
    "roas": {
        "id": "roas",
        "name": "Return on Ad Spend (ROAS)",
        "keywords": [
            "roas", "return on ad spend", "ad spend", "ad budget", "google shopping",
            "meta ads", "advertising spend", "3.11x", "4.91x", "3.8x"
        ],
        "current": "3.8x blended",
        "target": "4.4x target",
    },
    "retention": {
        "id": "retention",
        "name": "Repeat Rate / Retention",
        "keywords": [
            "repeat customer", "repeat rate", "retention", "customer lifetime value",
            "clv", "ltv", "reorder", "craving flow", "24% repeat"
        ],
        "current": "24.0%",
        "target": "30.0%",
    },
    "margin": {
        "id": "margin",
        "name": "Product Gross Margin",
        "keywords": [
            "gross margin", "gross margins", "margin", "margins", "profit margin",
            "highest margin", "unit economics", "68%", "54%", "42%"
        ],
        "current": "42% - 68%",
        "target": ">60% blended",
    },
    "return_rate": {
        "id": "return_rate",
        "name": "Return Rate",
        "keywords": [
            "return rate", "return rates", "returns", "refund rate", "refunds",
            "thawing complaints", "problem child", "7.4%"
        ],
        "current": "4.2%",
        "target": "<2.5%",
    },
}


def detect_metrics(question: str) -> List[Dict[str, Any]]:
    """Scan query text and identify all mentioned or implied performance metrics."""
    q_lower = question.lower()
    matched = []
    for m_id, meta in METRIC_REGISTRY.items():
        found = False
        for kw in meta["keywords"]:
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if re.search(pattern, q_lower):
                found = True
                break
        if found:
            matched.append(meta)
    return matched


def build_thinking_flow(
    question: str,
    agent_id: str,
    detected_metrics: List[Dict[str, Any]],
    reasoning: str,
    intent: str,
) -> Dict[str, Any]:
    """Construct an explainable thinking & routing flow trace for user transparency."""
    metric_count = len(detected_metrics)
    metric_names = [m["name"] for m in detected_metrics]
    primary_metric = detected_metrics[0]["id"] if detected_metrics else None

    # Determine cost tier details
    if agent_id == "information_escort" or agent_id == "orchestrator" or agent_id == "utility_minion":
        tier_key = "tier1"
        tier_name = "Tier 1: Lowest Cost"
        tier_badge = "$"
        tier_model = "openai/gpt-oss-20b"
        token_budget = "450 max tokens"
        cost_reason = "Lowest cost tier. Zero store metric data loaded; pure document/policy or creative prompt to minimize token burn."
    elif agent_id == "guidance_guru":
        tier_key = "tier2"
        tier_name = "Tier 2: Mid-Level Cost (Single Metric)"
        tier_badge = "$$"
        tier_model = "openai/gpt-oss-20b"
        token_budget = "750 max tokens"
        cost_reason = f"Client Rule: Single metric ({metric_names[0] if metric_names else 'Revenue'}). Loaded lean single-metric context slice rather than entire metric catalog."
    elif agent_id == "solution_mate":
        tier_key = "tier3"
        tier_name = "Tier 3: Flagship Primary (Multi-Metric)"
        tier_badge = "$$$"
        tier_model = "openai/gpt-oss-120b"
        token_budget = "1400 max tokens"
        cost_reason = f"Client Rule: Multi-metric cross-analysis ({metric_count} metrics: {', '.join(metric_names)}). Deployed flagship reasoning with 6-month trends and what-if simulation."
    else:  # collaborative
        tier_key = "tier3"
        tier_name = "Tier 3: Multi-Agent Synthesis"
        tier_badge = "$$$"
        tier_model = "openai/gpt-oss-120b"
        token_budget = "1400 max tokens"
        cost_reason = "Cross-domain collaborative synthesis coordinating multiple specialist agents."

    # Human-readable scope label
    if metric_count == 1:
        metric_scope = f"Single Metric: {metric_names[0]} ({detected_metrics[0]['current']})"
    elif metric_count >= 2:
        metric_scope = f"Multi-Metric Cross-Analysis ({metric_count} metrics: {', '.join(metric_names)})"
    else:
        metric_scope = "Non-Metric Scope (0 Performance Metrics)"

    agent_info = AGENT_REGISTRY.get(agent_id, {
        "name": "Orchestrator" if agent_id == "orchestrator" else "Multi-Agent Collaboration",
        "icon": "🤖" if agent_id == "orchestrator" else "🤝",
    })

    # Build 4-step pipeline trace
    step1_detail = (
        f"Scanned question for business performance metrics: found {metric_count} metric(s) "
        f"({', '.join(metric_names) if metric_names else 'No store metrics detected; policy or creative scope'})."
    )
    step1_badge = f"{metric_count} Metric" if metric_count == 1 else (f"{metric_count} Metrics" if metric_count > 1 else "0 Metrics")

    if metric_count == 1:
        step2_detail = (
            f"Client Rule Applied: Single metric detected ({metric_names[0]}). "
            f"Routed to Guidance Guru (Tier 2 Cost) for focused coaching without multi-metric overhead."
        )
        step2_badge = "Guidance Guru (Tier 2)"
        step3_detail = (
            f"Injected lean single-metric context slice for {metric_names[0]} "
            f"(current: {detected_metrics[0]['current']} vs target: {detected_metrics[0]['target']}). "
            "Omitted 6-month historical tables and other channel rows to save tokens."
        )
        step3_badge = "Lean Single Slice"
        step4_detail = (
            f"Formulated concrete sequential milestone and immediate execution step "
            f"to move {metric_names[0]} toward target."
        )
        pipeline = ["User Query", f"Metric Analyzer [1: {metric_names[0]}]", "Tier 2 Cost Router", "Guidance Guru 🧭", "Lean Context Slice", "Next Step Output"]
    elif metric_count >= 2:
        step2_detail = (
            f"Client Rule Applied: {metric_count} interacting metrics detected ({', '.join(metric_names)}). "
            f"Routed to Solution Mate (Tier 3 Flagship Engine) for multi-dimensional diagnostic."
        )
        step2_badge = "Solution Mate (Tier 3)"
        step3_detail = (
            "Assembled comprehensive multi-metric matrix: 6-month historical plateau trends, "
            "channel ROAS/CAC unit economics, and full product catalog margin tables."
        )
        step3_badge = "Full Multi-Metric Matrix"
        step4_detail = (
            "Conducted root-cause diagnosis and what-if sensitivity modeling across the interacting levers "
            "with confidence ratings."
        )
        pipeline = ["User Query", f"Metric Analyzer [{metric_count} Metrics]", "Tier 3 Primary Router", "Solution Mate 💡", "Comprehensive Matrix", "Strategic Model"]
    elif agent_id == "information_escort":
        step2_detail = (
            "Client Rule Applied: Zero performance metrics detected. Question is grounded in enterprise policies, "
            "SLAs, or platform rules. Routed to Information Escort (Tier 1 Lowest Cost)."
        )
        step2_badge = "Information Escort (Tier 1)"
        step3_detail = (
            "Retrieved top matching excerpts from policy documents via vector store. "
            "Zero store metric tables loaded, minimizing prompt cost."
        )
        step3_badge = "Policy Chunks Only"
        step4_detail = (
            "Grounded compliance answer strictly in retrieved document clauses with source citations."
        )
        pipeline = ["User Query", "Policy Intent Detector [0 Metrics]", "Tier 1 Lowest Cost", "Information Escort 📚", "Vector Store RAG", "Grounded Citation"]
    elif agent_id == "utility_minion":
        step2_detail = (
            "Creative copy or marketing brief request identified. Routed to Utility Minion (Tier 1 Low Cost)."
        )
        step2_badge = "Utility Minion (Tier 1)"
        step3_detail = "Loaded brand tone guidelines and top hero product references."
        step3_badge = "Brand Brief"
        step4_detail = "Drafted high-converting copywriting and execution template."
        pipeline = ["User Query", "Creative Intent Detector", "Tier 1 Low Cost", "Utility Minion 🛠️", "Brand Voice Context", "Ready-to-Use Copy"]
    else:  # greeting or collaborative
        step2_detail = f"Routed to {agent_info['name']}."
        step2_badge = tier_name
        step3_detail = "Context coordinated dynamically for the query intent."
        step3_badge = "Adaptive Context"
        step4_detail = "Completed conversational greeting or coordinated multi-agent brief."
        pipeline = ["User Query", "Dispatcher", agent_info["name"], "Execution Output"]

    flow_steps = [
        {"step": 1, "title": "Metric Analysis & Scope Detection", "detail": step1_detail, "badge": step1_badge},
        {"step": 2, "title": "Cost Tier & Agent Selection", "detail": step2_detail, "badge": step2_badge},
        {"step": 3, "title": "Context Assembly & Optimization", "detail": step3_detail, "badge": step3_badge},
        {"step": 4, "title": "Reasoning & Analytical Output", "detail": step4_detail, "badge": "Completed"},
    ]

    return {
        "detected_metrics": metric_names,
        "metric_count": metric_count,
        "metric_scope": metric_scope,
        "primary_metric": primary_metric,
        "routed_agent": agent_id,
        "routed_agent_name": agent_info.get("name", agent_id),
        "routed_agent_icon": agent_info.get("icon", "🤖"),
        "cost_tier": {
            "tier": tier_key,
            "name": tier_name,
            "badge": tier_badge,
            "model": tier_model,
            "token_budget": token_budget,
            "cost_reason": cost_reason,
        },
        "pipeline_path": pipeline,
        "flow_steps": flow_steps,
        "reasoning_summary": reasoning,
        "intent": intent,
    }


def handle_orchestrator_greeting(question: str, history: list) -> str:
    """Provide a warm, concise conversational response without unprompted data dumps."""
    system_prompt = (
        "You are the friendly Multi-Agent Assistant for Giri's Fried Chicken on the Gimbll e-commerce platform.\n"
        "You coordinate specialist agents across 3 cost-optimized tiers:\n"
        "1. Information Escort (Tier 1 Lowest Cost: policies, commission tiers, SLAs, returns)\n"
        "2. Guidance Guru (Tier 2 Mid Cost: single-metric tracking, sequential milestone execution)\n"
        "3. Solution Mate (Tier 3 Flagship Engine: multi-metric cross-analysis, root cause diagnostics, what-if modeling)\n"
        "4. Utility Minion (Tier 1 Low Cost: product descriptions, email recovery flows, marketing copy)\n\n"
        "Guidelines:\n"
        "- Respond warmly, politely, and conversationally in 2-3 short sentences.\n"
        "- Welcome the user and ask how you can help them today with Giri's Fried Chicken.\n"
        "- Do NOT output large data tables, financial spreadsheets, or unprompted diagnostics for simple greetings.\n"
    )
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": question})
    return generate_completion(messages=messages, system_prompt=system_prompt, tier="tier1", max_tokens=250)


def classify_question(question: str) -> Dict[str, Any]:
    """Classify the question according to the client's updated rules:
    - 0 metrics / Policy / SLA -> Information Escort (Tier 1 Lowest Cost)
    - 1 metric (Single Metric) -> Guidance Guru (Tier 2 Mid Cost, lean slice)
    - >= 2 metrics (Multi-Metric Cross-Analysis) -> Solution Mate (Tier 3 Flagship Engine)
    - Creative Copywriting -> Utility Minion (Tier 1 Low Cost)
    """
    q_lower = question.lower().strip()
    detected_metrics = detect_metrics(question)
    metric_count = len(detected_metrics)

    # 0. Greetings & Casual conversational messages
    q_stripped = re.sub(r"[^\w\s]", "", q_lower).strip()
    greeting_tokens = {
        "hi", "hello", "hey", "hiya", "howdy", "good morning", "good afternoon",
        "good evening", "greetings", "hi there", "hello there", "hey there",
        "whats up", "what's up", "sup", "yo", "help", "who are you",
        "what can you do", "thank you", "thanks", "test", "testing",
    }
    words = q_stripped.split()
    if q_stripped in greeting_tokens or (len(words) <= 3 and any(w in ["hi", "hello", "hey", "hiya", "howdy", "sup", "yo"] for w in words)):
        flow = build_thinking_flow(question, "orchestrator", [], "Conversational greeting and welcome.", "Welcome & Assistance")
        return {
            "primary_agent": "orchestrator",
            "secondary_agents": [],
            "reasoning": "Conversational greeting and welcome.",
            "intent": "Welcome & Assistance",
            "thinking_flow": flow,
        }

    # Intent detection
    has_policy = any(k in q_lower for k in [
        "policy", "sla", "commission tier", "restocking fee", "freshness guarantee",
        "return rule", "returns", "operating agreement", "dispatch window", "compliance", "agreement"
    ])
    has_creative = any(k in q_lower for k in [
        "draft an email", "write an email", "email sequence", "write copy", "product description",
        "ad headline", "write an ad", "creative brief", "image prompt", "social caption", "draft a response", "template"
    ])
    has_strategy_words = any(k in q_lower for k in [
        "what if", "why did our sales plateau", "why did sales plateau", "diagnose root cause",
        "root cause", "model the outcome", "financial impact", "scenario", "trade-off", "tradeoff", "sensitivity"
    ])

    # 1. Collaborative combinations:
    if has_policy and (has_creative or has_strategy_words or metric_count >= 2):
        collabs = ["information_escort"]
        if has_strategy_words or metric_count >= 2:
            collabs.append("solution_mate")
        if has_creative:
            collabs.append("utility_minion")
        reasoning = f"Cross-domain synthesis combining policy verification ({collabs[0]}) with {collabs[1]}."
        flow = build_thinking_flow(question, "collaborative", detected_metrics, reasoning, "Policy & Multi-Domain Synthesis")
        return {
            "primary_agent": "collaborative",
            "secondary_agents": collabs,
            "reasoning": reasoning,
            "intent": "Policy & Multi-Domain Synthesis",
            "thinking_flow": flow,
        }

    if has_creative and not (has_strategy_words or metric_count >= 2):
        reasoning = "Creative copywriting request. Routed to Utility Minion (Tier 1 Low Cost)."
        flow = build_thinking_flow(question, "utility_minion", detected_metrics, reasoning, "Creative Execution & Copywriting")
        return {
            "primary_agent": "utility_minion",
            "secondary_agents": [],
            "reasoning": reasoning,
            "intent": "Marketing & Content Generation",
            "thinking_flow": flow,
        }

    # Policy takes precedence when asking about agreements/SLAs/rules and no strategic modeling requested
    if has_policy and not has_strategy_words and metric_count <= 1:
        reasoning = "Inquiry regarding operational policies, commission tiers, SLAs, or merchant terms (Tier 1 Lowest Cost)."
        flow = build_thinking_flow(question, "information_escort", [], reasoning, "Policy & Compliance Check")
        return {
            "primary_agent": "information_escort",
            "secondary_agents": [],
            "reasoning": reasoning,
            "intent": "Policy & Compliance Check",
            "thinking_flow": flow,
        }

    # 2. CLIENT UPDATED RULE: Metrics Count Differentiation
    # Rule A: If it accesses more than two metrics (or multi-metric cross-analysis / strategic modeling) -> Solution Bot (Tier 3 Flagship)
    if metric_count >= 2 or has_strategy_words:
        metric_str = ", ".join(m["name"] for m in detected_metrics) if detected_metrics else "Cross-Metric Strategic Modeling"
        reasoning = (
            f"Client Rule: Query accesses multiple interacting metrics ({metric_count} detected: {metric_str}). "
            "Routed to Solution Mate (Tier 3 Flagship Primary Engine) for multi-dimensional causal analysis and what-if simulation."
        )
        flow = build_thinking_flow(question, "solution_mate", detected_metrics, reasoning, "Multi-Metric Strategic Diagnostic")
        return {
            "primary_agent": "solution_mate",
            "secondary_agents": [],
            "reasoning": reasoning,
            "intent": "Multi-Metric Strategic Diagnostic",
            "thinking_flow": flow,
        }

    # Rule B: If the agent only works on a single metric -> Guidance Bot (Tier 2 Mid Cost)
    if metric_count == 1:
        single_metric_name = detected_metrics[0]["name"]
        reasoning = (
            f"Client Rule: Query focuses strictly on a single metric ({single_metric_name}). "
            "Routed to Guidance Guru (Tier 2 Cost) with lean context slice to optimize token cost."
        )
        flow = build_thinking_flow(question, "guidance_guru", detected_metrics, reasoning, f"Single-Metric Guidance: {single_metric_name}")
        return {
            "primary_agent": "guidance_guru",
            "secondary_agents": [],
            "reasoning": reasoning,
            "intent": f"Single-Metric Guidance ({single_metric_name})",
            "thinking_flow": flow,
        }

    # Fallback when 0 metrics detected:
    # If general goal/progress language ("milestone", "roadmap", "next step", "are we there yet")
    if any(k in q_lower for k in ["milestone", "roadmap", "goal", "target state", "are we there yet", "on track"]):
        reasoning = "Single goal tracking inquiry. Routed to Guidance Guru (Tier 2 Cost)."
        flow = build_thinking_flow(question, "guidance_guru", [], reasoning, "Goal & Milestone Guidance")
        return {
            "primary_agent": "guidance_guru",
            "secondary_agents": [],
            "reasoning": reasoning,
            "intent": "Goal & Milestone Guidance",
            "thinking_flow": flow,
        }

    # General business intelligence fallback -> Solution Mate
    reasoning = "General strategic business intelligence evaluated across business dimensions."
    flow = build_thinking_flow(question, "solution_mate", [], reasoning, "General Business Intelligence")
    return {
        "primary_agent": "solution_mate",
        "secondary_agents": [],
        "reasoning": reasoning,
        "intent": "General Business Intelligence",
        "thinking_flow": flow,
    }


def handle_collaborative_workflow(
    store: VectorStore,
    question: str,
    history: list,
    agents: List[str],
    session_state: dict,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """Coordinate multiple agents to synthesize an authoritative collaborative answer."""
    pieces = []
    sources = []
    meta = {}

    if "information_escort" in agents:
        ans, srcs = answer_question(store, question, [])
        sources.extend(srcs)
        pieces.append(f"### 📚 Information Escort (Policy Grounding • Tier 1 Lowest Cost)\n{ans}")

    if "guidance_guru" in agents:
        ans, goal, srcs = answer_guidance(store, question, [], session_state.get("goal_state"))
        if goal:
            meta["goal_state"] = goal
        sources.extend(srcs)
        pieces.append(f"### 🧭 Guidance Guru (Single-Metric Coaching • Tier 2)\n{ans}")

    if "solution_mate" in agents:
        ans, analysis, srcs = answer_solution(store, question, [], session_state.get("solution_analysis"))
        if analysis:
            meta["solution_analysis"] = analysis
        sources.extend(srcs)
        pieces.append(f"### 💡 Solution Mate (Multi-Metric Diagnostic • Tier 3 Primary)\n{ans}")

    if "utility_minion" in agents:
        ans, draft = answer_utility(question, [], session_state.get("utility_draft"))
        if draft:
            meta["utility_draft"] = draft
        pieces.append(f"### 🛠️ Utility Minion (Creative Execution • Tier 1)\n{ans}")

    synthesis_prompt = (
        "You are the Multi-Agent Coordinator for Giri's Fried Chicken. Multiple specialist agents provided their findings "
        "for the merchant query below. Synthesize their contributions into a cohesive, beautifully structured "
        "executive response with clear headings and seamless handoffs.\n\n"
        f"Original User Question: {question}\n\n"
        f"Specialist Agent Inputs:\n" + "\n\n".join(pieces)
    )

    synthesized_answer = generate_completion(
        messages=[{"role": "user", "content": synthesis_prompt}],
        system_prompt="Synthesize the multi-agent outputs cleanly and comprehensively.",
        tier="tier3",
        max_tokens=1400,
    )

    return synthesized_answer, sorted(set(sources)), meta


def orchestrate_multi_agent(
    store: VectorStore,
    question: str,
    history: list,
    session_state: dict,
) -> Dict[str, Any]:
    """Main Multi-Agent orchestrator entry point: classifies query by metric scope, delegates, and returns thinking flow."""
    routing = classify_question(question)
    primary = routing.get("primary_agent", "solution_mate")
    reasoning = routing.get("reasoning", "Dispatched to specialist agent.")
    intent = routing.get("intent", "Merchant Inquiry")
    thinking_flow = routing.get("thinking_flow", {})

    # 1. Direct Orchestrator Greeting & General Assistance
    if primary == "orchestrator":
        answer_text = handle_orchestrator_greeting(question, history)
        return {
            "answer": answer_text,
            "agent": "orchestrator",
            "agent_name": "Multi-Agent Orchestrator",
            "agent_icon": "🤖",
            "agent_role": "Unified Assistant",
            "tab_id": "multi-agent",
            "reasoning": reasoning,
            "intent": intent,
            "thinking_flow": thinking_flow,
            "collaborating_agents": [],
            "sources": [],
            "metadata": {},
        }

    # 2. Collaborative Flow
    if primary == "collaborative":
        collaborators = routing.get("secondary_agents", ["information_escort", "solution_mate"])
        if len(collaborators) < 2:
            collaborators = ["information_escort", "solution_mate"]

        ans_text, sources, meta = handle_collaborative_workflow(
            store, question, history, collaborators, session_state
        )

        collab_info = [
            {
                "id": cid,
                "name": AGENT_REGISTRY.get(cid, {}).get("name", cid),
                "icon": AGENT_REGISTRY.get(cid, {}).get("icon", "🤖"),
                "role": AGENT_REGISTRY.get(cid, {}).get("role", ""),
                "cost_badge": AGENT_REGISTRY.get(cid, {}).get("cost_badge", "$"),
            }
            for cid in collaborators
            if cid in AGENT_REGISTRY
        ]

        return {
            "answer": ans_text,
            "agent": "collaborative",
            "agent_name": "Multi-Agent Collaboration",
            "agent_icon": "🤝",
            "agent_role": "Coordinated Multi-Agent Synthesis (Tier 3)",
            "reasoning": reasoning,
            "intent": intent,
            "thinking_flow": thinking_flow,
            "collaborating_agents": collab_info,
            "sources": sources,
            "metadata": meta,
        }

    # 3. Individual Agent Delegation
    agent_info = AGENT_REGISTRY.get(primary, AGENT_REGISTRY["solution_mate"])
    sources = []
    meta = {}

    if primary == "information_escort":
        answer_text, sources = answer_question(store, question, history)
    elif primary == "guidance_guru":
        current_goal = session_state.get("goal_state")
        primary_metric = thinking_flow.get("primary_metric") if thinking_flow else None
        answer_text, goal, sources = answer_guidance(
            store, question, history, current_goal, metric_key=primary_metric
        )
        if goal:
            meta["goal_state"] = goal
    elif primary == "solution_mate":
        current_scenario = session_state.get("solution_analysis")
        answer_text, analysis, sources = answer_solution(store, question, history, current_scenario)
        if analysis:
            meta["solution_analysis"] = analysis
    elif primary == "utility_minion":
        current_draft = session_state.get("utility_draft")
        answer_text, draft = answer_utility(question, history, current_draft)
        if draft:
            meta["utility_draft"] = draft
    else:
        answer_text, sources = answer_question(store, question, history)

    return {
        "answer": answer_text,
        "agent": agent_info["id"],
        "agent_name": agent_info["name"],
        "agent_icon": agent_info["icon"],
        "agent_role": agent_info["role"],
        "tab_id": agent_info["tab_id"],
        "reasoning": reasoning,
        "intent": intent,
        "thinking_flow": thinking_flow,
        "collaborating_agents": [],
        "sources": sources,
        "metadata": meta,
    }
