import json
from pathlib import Path
from typing import Any, Dict

from .config import DATA_DIR

STORE_DATA_PATH = DATA_DIR / "store_analytics.json"

DEFAULT_STORE_NAME = "Giri's Fried Chicken"


def get_store_analytics() -> Dict[str, Any]:
    if not STORE_DATA_PATH.exists():
        return {}
    with open(STORE_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_single_metric_summary(metric_key: str = "revenue") -> str:
    """Format a focused, lean single-metric context for Guidance Guru (Tier 2 Cost Optimization)."""
    data = get_store_analytics()
    if not data:
        return ""

    info = data.get("store_info", {})
    metrics = data.get("current_metrics") or data.get("current_kpis", {})
    funnel = data.get("conversion_funnel", {})

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== SINGLE METRIC FOCUSED CONTEXT: {store_name} ===",
        f"Target Goal: {info.get('target_goal')}",
        "",
    ]

    key = (metric_key or "").lower()
    if any(k in key for k in ["conversion", "checkout", "cart", "abandonment", "cr"]):
        lines.extend([
            "--- Focused Metric: Conversion Rate (Single Metric Focus) ---",
            f"• Current Conversion Rate: {metrics.get('conversion_rate_pct', 1.8)}%",
            f"• Industry Benchmark: {metrics.get('industry_benchmark_conversion_pct', 2.8)}%",
            f"• Store Sessions: {funnel.get('total_store_sessions', 21100):,} -> Completed Orders: {funnel.get('completed_orders', 380)}",
            f"• Checkout Abandonment Rate: {funnel.get('checkout_abandonment_rate_pct', 66.6)}%",
            f"• Primary Bottleneck: {funnel.get('primary_leak')}",
            "",
            "--- Mapped Single-Metric Milestone ---",
            "• [MS-01] Fix Checkout Friction: Free shipping threshold ($75) & 1-click checkout (lift CR from 1.80% to 2.30%, +$6,900/mo)",
        ])
    elif "order" in key:
        lines.extend([
            "--- Focused Metric: Monthly Orders (Single Metric Focus) ---",
            f"• Current Monthly Orders: {metrics.get('monthly_orders', 380)} orders",
            "• Target Monthly Orders: 760 orders (needed to achieve $50K target at $65.40 AOV)",
            f"• Average Order Value: ${metrics.get('average_order_value', 65.40):.2f}",
            "",
            "--- Mapped Single-Metric Milestone ---",
            "• [MS-01 & MS-03] Double order volume via checkout fix (+105 orders) and abandoned cart reorder (+104 orders)",
        ])
    elif any(k in key for k in ["aov", "basket", "bundle", "order value"]):
        lines.extend([
            "--- Focused Metric: Average Order Value (AOV) (Single Metric Focus) ---",
            f"• Current AOV: ${metrics.get('average_order_value', 65.40):.2f}",
            "• Target AOV: $74.50 (+$9.10 lift needed)",
            "",
            "--- Mapped Single-Metric Milestone ---",
            "• [MS-04] Launch Signature Bucket + Sauce Trio Bundle ($89 bundle vs $68 solo) to boost storewide AOV to $74.50 (+ $6,650/mo)",
        ])
    elif any(k in key for k in ["traffic", "session", "visitor"]):
        lines.extend([
            "--- Focused Metric: Store Traffic / Sessions (Single Metric Focus) ---",
            f"• Current Monthly Sessions: {metrics.get('store_sessions', 21100):,}",
            "• Traffic Trend: Steady (~21,000 sessions/mo over past 3 months)",
            "• Key Traffic Observation: Traffic is consistent; sales plateau is caused by conversion and AOV rather than visitor drop.",
        ])
    elif any(k in key for k in ["cac", "acquisition cost"]):
        lines.extend([
            "--- Focused Metric: Customer Acquisition Cost (CAC) (Single Metric Focus) ---",
            f"• Current Blended CAC: ${metrics.get('customer_acquisition_cost', 22.50):.2f}",
            f"• 30-Day Repeat Customer Rate: {metrics.get('repeat_customer_rate_pct', 24.0)}%",
            f"• Customer Lifetime Value (CLV): ${metrics.get('customer_lifetime_value', 148.00):.2f}",
            "",
            "--- Mapped Single-Metric Milestone ---",
            "• [MS-02] Shift $1,500/mo ad spend from Meta ($27.60 CAC) to Google Shopping ($16.20 CAC) to lower blended CAC",
        ])
    elif any(k in key for k in ["roas", "ad spend"]):
        lines.extend([
            "--- Focused Metric: Return on Ad Spend (ROAS) (Single Metric Focus) ---",
            "• Current Blended ROAS: 3.8x",
            "• Channel Disparity: Google Shopping (4.91x ROAS) vs Meta Ads (3.11x ROAS)",
            "",
            "--- Mapped Single-Metric Milestone ---",
            "• [MS-02] Reallocate $1,500/mo budget to Google Shopping to increase blended ROAS to 4.4x",
        ])
    elif any(k in key for k in ["margin", "profit"]):
        lines.extend([
            "--- Focused Metric: Product Gross Margin (Single Metric Focus) ---",
            "• Highest Margin Item: Giri's Signature Crispy Jumbo Bucket (68.0% margin, $8,370/mo rev)",
            "• Second Margin Item: Giri's Gourmet Hot Sauce Trio (54.0% margin, $6,256/mo rev)",
            "• Lowest Margin Item: Frozen Oven-Ready Strip Pack (42.0% margin, 7.4% return rate)",
        ])
    elif any(k in key for k in ["return", "refund"]):
        lines.extend([
            "--- Focused Metric: Return Rate (Single Metric Focus) ---",
            f"• Overall Store Return Rate: {metrics.get('return_rate_pct', 4.2)}%",
            "• Outlier SKU: Frozen Oven-Ready Strip Pack (7.4% return rate due to transit thawing complaints)",
            "• Star SKU: Signature Jumbo Bucket (2.1% return rate, stable)",
        ])
    else:
        lines.extend([
            "--- Focused Metric: Monthly Revenue & Gap (Single Metric Focus) ---",
            f"• Current Monthly Revenue: ${metrics.get('monthly_revenue', 24850.00):,.2f}",
            f"• Target Monthly Revenue: ${metrics.get('target_monthly_revenue', 50000.00):,.2f}",
            f"• Monthly Revenue Gap: ${metrics.get('revenue_gap', 25150.00):,.2f}",
            f"• Progress to Target: 49.7% of $50,000 Q4 goal achieved",
            "",
            "--- Primary Revenue Milestones ---",
            "• [MS-01] Eliminate Shipping Shock: +$6,900/mo",
            "• [MS-02] Reallocate Ad Spend: +$4,800/mo",
            "• [MS-03] Email Cart Recovery: +$6,800/mo",
            "• [MS-04] Product Bundling: +$6,650/mo",
            "• Combined Total Impact: +$25,150/mo (Closes the exact revenue gap)",
        ])

    return "\n".join(lines)


def get_guidance_store_summary() -> str:
    """Format store data specifically for Guidance Guru (Current vs Target, Milestones, Funnel leak)."""
    data = get_store_analytics()
    if not data:
        return ""

    info = data.get("store_info", {})
    metrics = data.get("current_metrics") or data.get("current_kpis", {})
    funnel = data.get("conversion_funnel", {})
    milestones = data.get("active_milestones", [])
    products = data.get("product_catalog_performance", [])

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== ACTIVE STORE PROFILE: {store_name} ===",
        f"Category: {info.get('domain')} | Platform: {info.get('platform')}",
        f"Overall Goal: {info.get('target_goal')}",
        "",
        "--- Current Store Performance Metrics vs Target ---",
        f"• Current Monthly Revenue: ${metrics.get('monthly_revenue', 0):,.2f}",
        f"• Target Monthly Revenue: ${metrics.get('target_monthly_revenue', 0):,.2f}",
        f"• Monthly Revenue Gap: ${metrics.get('revenue_gap', 0):,.2f} to reach target",
        f"• Monthly Orders: {metrics.get('monthly_orders')} orders | AOV: ${metrics.get('average_order_value', 0):.2f}",
        f"• Store Traffic: {metrics.get('store_sessions'):,} monthly sessions",
        f"• Conversion Rate: {metrics.get('conversion_rate_pct')}% (Industry benchmark: {metrics.get('industry_benchmark_conversion_pct')}%)",
        f"• Customer Acquisition Cost (CAC): ${metrics.get('customer_acquisition_cost', 0):.2f} | 30-Day Repeat Rate: {metrics.get('repeat_customer_rate_pct')}%",
        "",
        "--- Conversion Funnel & Immediate Bottleneck ---",
        f"• Sessions: {funnel.get('total_store_sessions'):,} -> Add-to-Cart: {funnel.get('add_to_cart_sessions'):,} (9.0%) -> Checkout: {funnel.get('reached_checkout_sessions'):,} (5.4%) -> Orders: {funnel.get('completed_orders')} (1.80%)",
        f"• Main Funnel Leak: {funnel.get('primary_leak')}",
        "",
        "--- Top Products in Catalog ---",
    ]

    for p in products[:3]:
        lines.append(
            f"• {p.get('product_name')}: ${p.get('monthly_revenue'):,.2f}/mo ({p.get('monthly_units_sold')} units, margin: {p.get('gross_margin_pct')}%, return rate: {p.get('return_rate_pct')}%) - {p.get('performance_tier')}"
        )

    lines.append("")
    lines.append("--- Active Roadmap Milestones ---")
    for m in milestones:
        lines.append(
            f"[{m.get('id')}] {m.get('title')} -> Action: {m.get('action')} | Impact: {m.get('estimated_revenue_lift')} | Status: {m.get('status')}"
        )

    return "\n".join(lines)


def get_solution_store_summary() -> str:
    """Format full store data for Solution Mate (Historical trends, channel ROAS, sensitivity)."""
    data = get_store_analytics()
    if not data:
        return ""

    info = data.get("store_info", {})
    metrics = data.get("current_metrics") or data.get("current_kpis", {})
    past_trend = data.get("past_performance_trend", [])
    channels = data.get("marketing_channels", [])
    products = data.get("product_catalog_performance", [])
    funnel = data.get("conversion_funnel", {})

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== REAL E-COMMERCE BUSINESS CONTEXT: {store_name} ===",
        f"Category: {info.get('domain')} | Reporting Period: {info.get('reporting_period')}",
        f"Current Revenue: ${metrics.get('monthly_revenue', 0):,.2f}/mo | Target: ${metrics.get('target_monthly_revenue', 0):,.2f}/mo",
        f"Orders: {metrics.get('monthly_orders')} | AOV: ${metrics.get('average_order_value', 0):.2f} | Sessions: {metrics.get('store_sessions'):,} | CR: {metrics.get('conversion_rate_pct')}%",
        "",
        "--- Historical 6-Month Past Performance (Why we stalled) ---",
    ]

    for t in past_trend:
        lines.append(
            f"• {t.get('month')}: ${t.get('revenue'):,.2f} rev, {t.get('orders')} orders, AOV ${t.get('aov')}, CR {t.get('conversion_rate_pct')}%, Ad Spend: ${t.get('ad_spend')}, CAC: ${t.get('cac')} -> {t.get('notes')}"
        )

    lines.append("")
    lines.append("--- Marketing Channel Unit Economics & ROAS ---")
    for ch in channels:
        lines.append(
            f"• {ch.get('channel')}: Spend ${ch.get('monthly_spend'):,.2f} | Rev ${ch.get('revenue_generated'):,.2f} | ROAS {ch.get('roas')}x | CAC ${ch.get('cac')} | Orders {ch.get('orders')} -> {ch.get('status')}"
        )

    lines.append("")
    lines.append("--- Funnel Metrics & Conversion Bottleneck ---")
    lines.append(
        f"• Sessions ({funnel.get('total_store_sessions'):,}) -> Add to Cart ({funnel.get('add_to_cart_sessions'):,}, 9%) -> Checkout Reached ({funnel.get('reached_checkout_sessions'):,}, 5.4%) -> Orders ({funnel.get('completed_orders')}, 1.8%)"
    )
    lines.append(f"• Checkout Abandonment Rate: {funnel.get('checkout_abandonment_rate_pct')}%")
    lines.append(f"• Diagnostic Root Cause: {funnel.get('primary_leak')}")

    lines.append("")
    lines.append("--- Full Product Catalog Economics ---")
    for p in products:
        lines.append(
            f"• {p.get('product_name')} ({p.get('sku')}): Price ${p.get('retail_price'):.2f} | Rev ${p.get('monthly_revenue'):,.2f} | Margin {p.get('gross_margin_pct')}% | CR {p.get('conversion_rate_pct')}% | Returns {p.get('return_rate_pct')}% -> {p.get('performance_tier')}"
        )

    return "\n".join(lines)


def get_utility_store_summary() -> str:
    """Format store data for Utility Minion (Brand voice, products, promotion angles, and copy briefs)."""
    data = get_store_analytics()
    if not data:
        return ""

    info = data.get("store_info", {})
    products = data.get("product_catalog_performance", [])
    funnel = data.get("conversion_funnel", {})
    milestones = data.get("active_milestones", [])

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== BRAND & STORE CONTEXT: {store_name} ===",
        f"Domain: {info.get('domain')} | Platform: {info.get('platform')}",
        "Brand Voice: Irresistible, mouth-watering, Southern artisanal craft, crispy perfection, bold & craving-inducing.",
        "Signature Differentiators: 24-hr buttermilk brine, 11-spice secret crust, flash-frozen dry-ice insulated shipping.",
        "",
        "--- Top Catalog Items Available for Copy & Promotion ---",
    ]

    for p in products:
        lines.append(
            f"• {p.get('product_name')} ({p.get('sku')}): Retail ${p.get('retail_price'):.2f} | Category: {p.get('category')} | Role: {p.get('performance_tier')}"
        )

    lines.append("")
    lines.append("--- Active Campaigns & Immediate Conversion Levers ---")
    lines.append(f"• Cart Recovery Goal: {funnel.get('primary_leak')}")
    for m in milestones:
        lines.append(f"• [{m.get('id')}] {m.get('title')}: {m.get('action')}")

    return "\n".join(lines)


def get_store_badge_info() -> Dict[str, Any]:
    data = get_store_analytics()
    if not data:
        return {
            "store_name": "Giri's Fried Chicken",
            "current_revenue": "$24,850/mo",
            "target_revenue": "$50,000/mo",
            "conversion_rate": "1.80%",
        }
    metrics = data.get("current_metrics") or data.get("current_kpis", {})
    return {
        "store_name": data.get("store_info", {}).get("store_name", "Giri's Fried Chicken"),
        "current_revenue": f"${metrics.get('monthly_revenue', 24850):,.0f}/mo",
        "target_revenue": f"${metrics.get('target_monthly_revenue', 50000):,.0f}/mo",
        "conversion_rate": f"{metrics.get('conversion_rate_pct', 1.8)}%",
    }
