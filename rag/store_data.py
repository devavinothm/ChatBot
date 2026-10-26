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


def get_guidance_store_summary() -> str:
    """Format store data specifically for Guidance Guru (Current vs Target, Milestones, Funnel leak)."""
    data = get_store_analytics()
    if not data:
        return ""

    info = data.get("store_info", {})
    kpis = data.get("current_kpis", {})
    funnel = data.get("conversion_funnel", {})
    milestones = data.get("active_milestones", [])
    products = data.get("product_catalog_performance", [])

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== ACTIVE STORE PROFILE: {store_name} ===",
        f"Category: {info.get('domain')} | Platform: {info.get('platform')}",
        f"Overall Goal: {info.get('target_goal')}",
        "",
        "--- Current Store KPIs vs Target ---",
        f"• Current Monthly Revenue: ${kpis.get('monthly_revenue', 0):,.2f}",
        f"• Target Monthly Revenue: ${kpis.get('target_monthly_revenue', 0):,.2f}",
        f"• Monthly Revenue Gap: ${kpis.get('revenue_gap', 0):,.2f} to reach target",
        f"• Monthly Orders: {kpis.get('monthly_orders')} orders | AOV: ${kpis.get('average_order_value', 0):.2f}",
        f"• Store Traffic: {kpis.get('store_sessions'):,} monthly sessions",
        f"• Conversion Rate: {kpis.get('conversion_rate_pct')}% (Industry benchmark: {kpis.get('industry_benchmark_conversion_pct')}%)",
        f"• Customer Acquisition Cost (CAC): ${kpis.get('customer_acquisition_cost', 0):.2f} | 30-Day Repeat Rate: {kpis.get('repeat_customer_rate_pct')}%",
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
    kpis = data.get("current_kpis", {})
    past_trend = data.get("past_performance_trend", [])
    channels = data.get("marketing_channels", [])
    products = data.get("product_catalog_performance", [])
    funnel = data.get("conversion_funnel", {})

    store_name = info.get("store_name") or DEFAULT_STORE_NAME
    lines = [
        f"=== REAL E-COMMERCE BUSINESS CONTEXT: {store_name} ===",
        f"Category: {info.get('domain')} | Reporting Period: {info.get('reporting_period')}",
        f"Current Revenue: ${kpis.get('monthly_revenue', 0):,.2f}/mo | Target: ${kpis.get('target_monthly_revenue', 0):,.2f}/mo",
        f"Orders: {kpis.get('monthly_orders')} | AOV: ${kpis.get('average_order_value', 0):.2f} | Sessions: {kpis.get('store_sessions'):,} | CR: {kpis.get('conversion_rate_pct')}%",
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
    kpis = data.get("current_kpis", {})
    return {
        "store_name": data.get("store_info", {}).get("store_name", "Giri's Fried Chicken"),
        "current_revenue": f"${kpis.get('monthly_revenue', 24850):,.0f}/mo",
        "target_revenue": f"${kpis.get('target_monthly_revenue', 50000):,.0f}/mo",
        "conversion_rate": f"{kpis.get('conversion_rate_pct', 1.8)}%",
    }
