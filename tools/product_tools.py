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
⚠️ INSTRUCTION FOR AGENT: Do NOT say "Not Available" coldly.
Instead, pivot elegantly: "We don't carry {query} right now, but if you're setting up your home, we have premium beds, wardrobes, and appliances available!"
Available categories: {', '.join(categories)}
"""
    
    # If we found results, we add a smart instructional hint for the agent.
    # For example, if they searched L-shape sofa and we found 7-seater sofas.
    prompt_hint = ""
    if query and len(query) > 3 and not category:
        prompt_hint = f"\n💡 INSTRUCTION FOR AGENT: If these aren't exact matches for '{query}' (e.g., matching 7-seater for L-shape), present them as the CLOSEST ALTERNATIVES. Do NOT say 'We do not have {query}'. Instead say: 'I may not have that exact listing right now, but I do have fantastic options that are closest to what you need:' and list the products below."
        
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

{unit == "months" and "📅 *Duration Options (30% Flat Discount applied):*" or ""}
{price_info}

💡 *Note:* The 🚀 *Upfront Deal* applies an additional **10% discount** when you pay the full amount in advance.
"""


@tool
def create_quote_tool(product_ids: str, duration: int = 12, unit: str = "months") -> str:
    """
    Create a rental quote with 30% discount and 18% GST.
    Duplicate product IDs count as multiple units (e.g. "28,28" = 2x product 28).
    """
    try:
        ids = [int(pid.strip()) for pid in product_ids.split(",")]
    except ValueError:
        return "Invalid IDs format."

    # Count quantities by tallying duplicates
    from collections import Counter
    qty_map = Counter(pid for pid in ids if pid in id_to_name)
    if not qty_map:
        return "No valid products found."

    line_items = []
    total_original = 0
    total_discounted = 0
    total_savings = 0

    for pid, qty in qty_map.items():
        orig_per_unit = calculate_rent(pid, duration, unit)
        if orig_per_unit is None:
            continue
        disc_per_unit = apply_discount(orig_per_unit)
        name = id_to_name[pid]

        line_savings = (orig_per_unit - disc_per_unit) * qty
        line_orig_total = orig_per_unit * qty
        line_disc_total = disc_per_unit * qty

        total_original += line_orig_total
        total_discounted += line_disc_total
        total_savings += line_savings

        qty_prefix = f"{qty}x" if qty > 1 else "1x"
        unit_str = "/mo" if unit == "months" else ""
        line_items.append(
            f"• {qty_prefix} {name} : ~₹{orig_per_unit:,}{unit_str}~ ₹{disc_per_unit:,}{unit_str} + GST"
        )

    if not line_items:
        return "No valid products found."

    items_str = "\n".join(line_items)
    security = min(int(round(total_discounted * 2)), 15000)

    return (
        f"🛒 *Your Cart:*\n\n"
        f"{items_str}\n\n"
        f"💰 *Total: ₹{total_discounted:,}/month + GST*\n"
        f"🎉 *Total Savings: ₹{total_savings:,}/month*\n\n"
        f"🔒 Security Deposit: ₹{security:,} (refundable)\n"
        f"✅ Free delivery, maintenance & returns."
    )


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
        return f"🔥 Trending in {category}: {product['name']} - {rent_display} (6mo)"
    
    # Return all trending products
    results = ["🔥 **Trending Products:**\n"]
    for cat, pid in TRENDING_PRODUCTS.items():
        product = get_product_by_id(pid)
        if product:
            rent_display = _get_price_helper(pid, 6)
            results.append(f"• {cat.title()}: {product['name']} - {rent_display} (6mo)")
    
    return "\n".join(results)
