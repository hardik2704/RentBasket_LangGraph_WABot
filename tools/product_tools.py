# Product Tools for RentBasket WhatsApp Bot
# Tools for searching products, getting prices, and creating quotes

from langchain_core.tools import tool
from typing import List, Optional
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.products import (
    get_products_by_category,
    search_products_by_name,
    calculate_rent,
    get_product_by_id,
    apply_discount,
    format_price_comparison,
    create_bundle_quote,
    id_to_name,
    category_to_id,
    TRENDING_PRODUCTS
)


@tool
def search_products_tool(query: str, category: Optional[str] = None) -> str:
    """
    Search for rental products by name or category.
    Use this to find products when the customer asks about a specific item or category.
    
    Args:
        query: Product name or keyword to search (e.g., "sofa", "dining table", "AC")
        category: Optional specific category to filter by (e.g., "bed", "fridge", "ac", "sofa")
    
    Returns:
        List of matching products with their IDs
    """
    results = []
    
    # First try category search if category provided
    if category:
        cat_key = category.lower().strip()
        if cat_key in category_to_id:
            products = get_products_by_category(cat_key)
            for p in products[:8]:  # Limit to 8 items
                results.append(f"• {p['name']} (ID: {p['id']})")
    
    # Also search by name
    if query:
        name_results = search_products_by_name(query)
        for p in name_results[:8]:
            item = f"• {p['name']} (ID: {p['id']})"
            if item not in results:
                results.append(item)
    
    if not results:
        # User searched for something strictly not in our DB (like Curtains)
        categories = list(set(category_to_id.keys()))[:10]
        return f"""
Nothing found matching '{query}'.
INSTRUCTION FOR AGENT: Do NOT say "Not Available" coldly.
Instead, pivot elegantly: "We don't carry {query} right now, but if you're setting up your home, we have premium beds, wardrobes, and appliances available!"
Available categories: {', '.join(categories)}
"""
    
    # If we found results, we add a smart instructional hint for the agent.
    # For example, if they searched L-shape sofa and we found 7-seater sofas.
    prompt_hint = ""
    if query and len(query) > 3 and not category:
        prompt_hint = f"\nINSTRUCTION FOR AGENT: If these aren't exact matches for '{query}' (e.g., matching 7-seater for L-shape), present them as the CLOSEST ALTERNATIVES. Do NOT say 'We do not have {query}'. Instead say: 'I may not have that exact listing right now, but I do have great options that are closest to what you need:' and list the products below."
        
    return f"Found {len(results)} products matching intent for '{query}':\n" + "\n".join(results[:10]) + prompt_hint


@tool
def get_price_tool(product_id: int, duration: int = 6, unit: str = "months") -> str:
    """
    Get the rental price with 30% flat and 10% upfront layered discounts.
    """
    product = get_product_by_id(product_id)
    if not product:
        return f"Product with ID {product_id} not found."
    
    orig_rent = calculate_rent(product_id, duration, unit)
    rent_display = format_price_comparison(orig_rent, duration, unit)
    
    if unit == "months":
        prices = [1, 3, 6, 12]
        opts = [f" • {d}mo: {format_price_comparison(calculate_rent(product_id, d), d)}" for d in prices]
        price_info = "\n".join(opts)
    else:
        price_info = "Daily rates vary by tenure."

    return f"""
*{product['name']}*
Rent for {duration} {unit}: {rent_display}

{unit == "months" and "*Duration Options (30% Flat Discount applied):*" or ""}
{price_info}

*Note:* The *Upfront Deal* applies an additional *10% discount* when you pay the full amount in advance.
"""


@tool
def create_quote_tool(product_ids: str, duration: int = 12, unit: str = "months") -> str:
    """
    Create a full Order Confirmation-style rental quote with 30% discount and 18% GST.
    Mirrors the RentBasket website Order Confirmation screen.
    Duplicate product IDs count as multiple units (e.g. "28,28" = 2x product 28).
    Appends [SEND_CART_BUTTONS] at the end — the webhook renders Reserve / Modify / Expert buttons.
    """
    try:
        ids = [int(pid.strip()) for pid in product_ids.split(",")]
    except ValueError:
        return "Invalid IDs format."

    from collections import Counter
    qty_map = Counter(pid for pid in ids if pid in id_to_name)
    if not qty_map:
        return "No valid products found."

    order_lines = []
    total_original = 0
    total_discounted = 0
    total_savings = 0
    unit_str = "/mo" if unit == "months" else ""

    for pid, qty in qty_map.items():
        orig_per_unit = calculate_rent(pid, duration, unit)
        if orig_per_unit is None:
            continue
        disc_per_unit = apply_discount(orig_per_unit)
        name = id_to_name[pid]

        total_savings += (orig_per_unit - disc_per_unit) * qty
        total_original += orig_per_unit * qty
        total_discounted += disc_per_unit * qty

        qty_label = f"{qty}x" if qty > 1 else "1x"
        order_lines.append(
            f"• {qty_label} {name} ({duration} {unit})\n"
            f"  ~₹{orig_per_unit:,}{unit_str}~ *₹{disc_per_unit:,}{unit_str}* + GST"
        )

    if not order_lines:
        return "No valid products found."

    # ── Monthly Rent section ──────────────────────────────
    gst = int(round(total_discounted * 0.18))
    net_monthly = total_discounted + gst

    # ── One Time section ──────────────────────────────────
    transport = 400
    transport_disc = -400          # Free delivery promo
    security = min(int(round(total_discounted * 2)), 15000)
    net_first_month = security + net_monthly   # transport nets to 0

    sep = "━━━━━━━━━━━━━━━━━━━━"

    cart_text = (
        f"*Order Confirmation*\n"
        f"{sep}\n\n"

        f"*Order Details*\n"
        + "\n".join(order_lines) +

        f"\n\n{sep}\n"
        f"*Monthly Rent*\n"
        f"Rent          ₹{total_discounted:,}/mo\n"
        f"GST (18%)     ₹{gst:,}/mo\n"
        f"*Net Monthly  ₹{net_monthly:,}/mo*\n\n"

        f"{sep}\n"
        f"*One Time Charges*\n"
        f"Security Deposit   ₹{security:,} _(refundable)_\n"
        f"Delivery           ₹{transport:,}\n"
        f"Delivery Discount  -₹{abs(transport_disc):,}\n"
        f"*Net Payable (1st Month)   ₹{net_first_month:,}*\n\n"

        f"{sep}\n"
        f"You save *₹{total_savings:,}/month* x {duration} months = *₹{total_savings * duration:,}* on this cart!\n\n"

        f"*Terms & Conditions*\n"
        f"• Products are in mint condition\n"
        f"• Standard maintenance included\n"
        f"• Free shipping & standard installation\n"
        f"• Complete KYC before delivery\n\n"

        f"[SEND_CART_BUTTONS]"
    )

    return cart_text


@tool 
def get_trending_products_tool(category: Optional[str] = None) -> str:
    """
    Get trending/recommended products for quick suggestions.
    Use this for bundle deals or when customer wants recommendations.
    
    Args:
        category: Optional category to get trending product for
    
    Returns:
        List of trending products with prices
    """
    def _get_price_helper(pid, dur):
        orig = calculate_rent(pid, dur)
        return format_price_comparison(orig, dur)

    if category and category.lower() in TRENDING_PRODUCTS:
        pid = TRENDING_PRODUCTS[category.lower()]
        product = get_product_by_id(pid)
        rent_display = _get_price_helper(pid, 6)
        return f"Trending in {category}: {product['name']} - {rent_display} (6mo)"

    # Return all trending products
    results = ["*Trending Products:*\n"]
    for cat, pid in TRENDING_PRODUCTS.items():
        product = get_product_by_id(pid)
        if product:
            rent_display = _get_price_helper(pid, 6)
            results.append(f"• {cat.title()}: {product['name']} - {rent_display} (6mo)")
    
    return "\n".join(results)
