# Catalogue Tools for RentBasket WhatsApp Bot
# Tools for browsing, filtering, and comparing the full product catalogue
# Display pricing: 12-month rate with 10% upfront discount (original data untouched)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import tool
from typing import Optional
from data.products import (
    id_to_name,
    id_to_price,
    category_to_id,
    get_products_by_category,
    get_all_categories,
    get_product_by_id,
    calculate_rent,
    apply_discount,
    format_price_comparison,
    TRENDING_PRODUCTS,
)


# ========================================
# PRICING HELPERS (display-only, never modifies original data)
# ========================================

UPFRONT_DISCOUNT = 0.30  # Flat 30% discount

def _best_price(product_id: int) -> int:
    """
    Calculate the best display price: 30% flat + 10% additional upfront.
    """
    prices = id_to_price.get(product_id)
    if not prices:
        return 0
    twelve_month_rate = prices[-1]
    return apply_discount(twelve_month_rate, upfront=True)


def _format_price(amount: int, is_original: bool = False) -> str:
    """Format price with rupee symbol. If amount is original, we just format it simply."""
    if is_original:
        return f"₹{amount:,}"
    # This is a bit tricky since _format_price is used in many tools.
    # We want the '~Old~ New Rs +GST' format.
    # However, some tools only pass the NEW amount.
    # To be safe, we'll try to find the original if only amount is given, or just show New Rs +GST.
    return f"₹{amount:,} +GST"


def _category_product_count(category: str) -> int:
    """Get number of products in a category."""
    return len(category_to_id.get(category, []))


# ========================================
# CATALOGUE TOOLS
# ========================================

@tool
def get_full_catalogue_overview_tool() -> str:
    """
    Get a complete overview of all RentBasket product categories.
    Shows category names, product count, and starting price (best price with upfront discount).
    Use this when the customer asks "What do you offer?", "What products do you have?",
    "Show me your catalogue", or similar general browsing questions.
    
    Returns:
        Formatted catalogue overview with all categories and starting prices
    """
    categories = get_all_categories()
    
    lines = ["🏠 *RentBasket Complete Catalogue*\n"]
    lines.append("Here's everything we offer for rent:\n")
    
    # Group categories logically
    groups = {
        "🛋️ Furniture": ["bed", "sofa", "mattress", "dining table", "center table", 
                          "coffee table", "study table", "study chair", "bookshelf", "sofa chair"],
        "📺 Appliances": ["fridge", "tv", "washing machine", "ac", "water purifier", 
                          "microwave", "geyser", "chimney", "gas stove"],
        "🔋 Power": ["inverter"],
    }
    
    for group_name, cats in groups.items():
        lines.append(f"\n{group_name}")
        for cat in cats:
            if cat not in category_to_id:
                continue
            product_ids = category_to_id[cat]
            # Find the lowest best-price in this category
            min_price = min(_best_price(pid) for pid in product_ids)
            count = len(product_ids)
            variant_text = f"({count} option{'s' if count > 1 else ''})"
            lines.append(f"  • {cat.title()} — starting {_format_price(min_price)}/mo {variant_text}")
    
    lines.append(f"📦 Total: {len(id_to_name)} products across {len(get_all_categories())} categories")
    lines.append(f"\n💡 All prices shown are *starting prices* with 12-month commitment + 10% upfront discount.")
    lines.append(f"\nWant to explore a specific category? Just ask! 😊")
    
    return "\n".join(lines)


@tool
def browse_category_tool(category: str) -> str:
    """
    Browse all products in a specific category with detailed pricing.
    Shows each product with its best price (12-month + 10% upfront discount).
    Use this when customer wants to see all options in a category like "show me beds" or "what sofas do you have?"
    
    Args:
        category: Product category to browse (e.g., "bed", "sofa", "fridge", "ac", "tv")
    
    Returns:
        All products in the category with best prices
    """
    cat_key = category.lower().strip()
    
    # Try to match category (including aliases)
    if cat_key not in category_to_id:
        # Try partial matching
        for key in category_to_id:
            if cat_key in key or key in cat_key:
                cat_key = key
                break
        else:
            available = ", ".join(get_all_categories())
            return f"Category '{category}' not found. Available categories: {available}"
    
    products = get_products_by_category(cat_key)
    if not products:
        return f"No products found in '{category}'."
    
    lines = [f"📋 *{cat_key.title()}* — All Options\n"]
    
    # Find trending product for this category
    trending_id = TRENDING_PRODUCTS.get(cat_key)
    
    for p in products:
        twelve_rate = p["prices"][-1]  # Get the longest duration (12m+) rate
        price_display = format_price_comparison(twelve_rate, 12, "months")
        trending_badge = " 🔥 *Popular*" if p["id"] == trending_id else ""
        lines.append(f"  • *{p['name']}*{trending_badge}")
        lines.append(f"    Starting Price: {price_display} (12-month plan)")
        lines.append("")
    
    lines.append(f"💡 *Starting prices* include a flat 30% discount on the 12-month plan.")
    lines.append(f"Want to compare any of these? Or check prices for a different duration?")
    
    return "\n".join(lines)


@tool
def compare_products_tool(product_ids: str, duration_months: int = 12) -> str:
    """
    Compare 2-3 products side by side with pricing.
    Default comparison uses 12-month pricing. Only use different duration if customer explicitly asks.
    
    Args:
        product_ids: Comma-separated product IDs to compare (e.g., "1042,18")
        duration_months: Duration for price comparison (default 12 months, change only if customer asks)
    
    Returns:
        Side-by-side comparison of the products
    """
    try:
        ids = [int(pid.strip()) for pid in product_ids.split(",")]
    except ValueError:
        return "Invalid product IDs. Please provide comma-separated numbers like '1042,18'"
    
    if len(ids) < 2:
        return "Please provide at least 2 product IDs to compare."
    if len(ids) > 3:
        ids = ids[:3]  # Limit to 3
    
    products = []
    for pid in ids:
        p = get_product_by_id(pid)
        if p:
            products.append(p)
    
    if len(products) < 2:
        return "Could not find enough valid products to compare. Please search for products first."
    
    lines = [f"⚖️ *Product Comparison* ({duration_months}-month plan)\n"]
    
    for p in products:
        orig_rent = calculate_rent(p["id"], duration_months)
        price_display = format_price_comparison(orig_rent, duration_months)
        lines.append(f"┌─ *{p['name']}*")
        lines.append(f"│  {duration_months}-month rate: {price_display}")
        lines.append(f"└────────────────")
        lines.append("")
    
    # Placeholder Quality Comparison (Hardcoded for now as requested)
    # Check if we are comparing sofas (ids 18, 1039, 1041, 1042, 1043, 1048, 1049, 1020)
    sofa_ids = [18, 1020, 1039, 1041, 1042, 1043, 1048, 1049]
    has_sofa = any(p["id"] in sofa_ids for p in products)
    
    if has_sofa:
        lines.append("🛋️ *Quick Quality Check*")
        lines.append("• *Capacity*: 5-Seater sets allow 5 people to sit comfortably, while 3-Seater sofas are perfect for 3 people.")
        lines.append("• *Comfort*: All our sofas feature high-density foam for long-lasting comfort.")
        lines.append("• *Material*: Premium fabric upholstery that is easy to clean.")
        lines.append("")

    # Show savings comparison
    if len(products) >= 2:
        lines.append(f"🏷️ Prices include a flat **30% Discount** across all items!")
    
    return "\n".join(lines)


@tool
def get_room_package_tool(room_type: str) -> str:
    """
    Get curated room package suggestions.
    NOTE: This is currently a placeholder — combo pricing is coming soon.
    Use this when customer asks about furnishing a room, e.g., "furnish my bedroom", "living room setup"
    
    Args:
        room_type: Type of room (bedroom, living_room, kitchen, full_home, work_from_home)
    
    Returns:
        Package suggestion (currently placeholder with contact info)
    """
    room_type_lower = room_type.lower().strip().replace(" ", "_")
    
    # Room package definitions (products only, pricing is placeholder)
    ROOM_PACKAGES = {
        "bedroom": {
            "name": "Bedroom Package",
            "emoji": "🛏️",
            "items": ["Double Bed", "Mattress", "Side Table", "Dressing Table"],
        },
        "living_room": {
            "name": "Living Room Package",
            "emoji": "🛋️",
            "items": ["Sofa Set", "Center Table", "SMART LED TV", "Side Table"],
        },
        "kitchen": {
            "name": "Kitchen Package",
            "emoji": "🍳",
            "items": ["Fridge", "Microwave", "Water Purifier", "Gas Stove"],
        },
        "full_home": {
            "name": "Full Home Package",
            "emoji": "🏠",
            "items": ["Bed", "Mattress", "Sofa", "Fridge", "Washing Machine", "TV", "Dining Table", "Center Table"],
        },
        "work_from_home": {
            "name": "Work From Home Package",
            "emoji": "💻",
            "items": ["Study Table", "Study Chair", "Book Shelf"],
        },
    }
    
    # Match room type
    package = ROOM_PACKAGES.get(room_type_lower)
    if not package:
        # Try partial matching
        for key, val in ROOM_PACKAGES.items():
            if room_type_lower in key or key in room_type_lower:
                package = val
                break
    
    if not package:
        available = ", ".join(ROOM_PACKAGES.keys())
        return f"Room type '{room_type}' not found. Available packages: {available}"
    
    lines = [f"{package['emoji']} *{package['name']}*\n"]
    lines.append("Includes:")
    for item in package["items"]:
        lines.append(f"  • {item}")
    
    lines.append(f"\n🚧 *Combo pricing coming soon!*")
    lines.append(f"For special combo deals, contact our sales team:")
    lines.append(f"  📞 Gurgaon: +91 9958187021")
    lines.append(f"  📞 Noida: +91 9958440038")
    lines.append(f"\nIn the meantime, I can show you individual product prices for any of these items! 😊")
    
    return "\n".join(lines)


@tool
def filter_by_budget_tool(max_budget: int, min_budget: int = 0) -> str:
    """
    Filter products that fit within a monthly budget range.
    Uses 12-month best price (with 10% upfront discount) for filtering.
    Use when customer says things like "what can I get under 3000?" or "products between 500 and 1000"
    
    Args:
        max_budget: Maximum monthly budget in rupees
        min_budget: Minimum monthly budget in rupees (default 0)
    
    Returns:
        Products that fit within the budget, grouped by category
    """
    if max_budget <= 0:
        return "Please provide a valid budget amount in rupees."
    
    results = {}  # category -> list of (product_name, best_price)
    
    for cat in get_all_categories():
        products = get_products_by_category(cat)
        for p in products:
            best = _best_price(p["id"])
            if min_budget <= best <= max_budget:
                if cat not in results:
                    results[cat] = []
                results[cat].append((p["name"], best, p["id"]))
    
    if not results:
        return f"No products found in the {_format_price(min_budget)} - {_format_price(max_budget)}/month range. Try increasing your budget range."
    
    # Count total
    total = sum(len(v) for v in results.values())
    
    lines = [f"💰 *Products in your budget* ({_format_price(min_budget)} - {_format_price(max_budget)}/mo)\n"]
    lines.append(f"Found {total} products:\n")
    
    for cat, products in sorted(results.items()):
        lines.append(f"*{cat.title()}*")
        for name, price, pid in sorted(products, key=lambda x: x[1]):
            lines.append(f"  • {name} — {_format_price(price)}/mo")
        lines.append("")
    
    lines.append(f"💡 Prices shown are *starting prices* (12mo + 10% upfront discount)")
    lines.append(f"Want details on any of these? I can compare products or create a quote!")
    
    return "\n".join(lines)
