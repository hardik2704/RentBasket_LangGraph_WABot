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
    Get the rental price for a specific product for any duration.
    Use this when the customer asks for the rent/price of a specific item.
    
    Args:
        product_id: The product ID (use search_products_tool to find IDs)
        duration: Rental duration value
        unit: Unit of duration ("days" or "months"). Default is "months".
    
    Returns:
        Product name and rental price details
    """
    product = get_product_by_id(product_id)
    if not product:
        return f"Product with ID {product_id} not found. Please search for products first."
    
    # Try fetching effective price from Supabase first
    effective_data = None
    if unit == "months":
        try:
            from utils.db import is_db_available, execute_query_one
            if is_db_available():
                query = "SELECT calculate_effective_price(%s, %s)"
                result = execute_query_one(query, (product_id, duration))
                if result and result[0]:
                    effective_data = result[0]
                    if "error" in effective_data:
                        effective_data = None
        except Exception as e:
            print(f"⚠️ Pricing Engine Error: {e}")
            effective_data = None

    if effective_data:
        # Use DB data (with discounts and formatting (~))
        rent_display = effective_data.get('display_text')
        rent_value = effective_data.get('final_price')
        source = effective_data.get('discount_source', 'none')
        discount_percent = effective_data.get('discount_percent', 0)
    else:
        # Fallback to local math
        rent_value = calculate_rent(product_id, duration, unit)
        rent_display = f"₹{rent_value}/month" if unit == "months" else f"₹{rent_value}"

    # Get prices for all durations for comparison
    def _get_formatted_price(pid, dur):
        if unit != "months":
            val = calculate_rent(pid, dur, unit)
            return f"₹{val}"
        
        try:
            from utils.db import is_db_available, execute_query_one
            if is_db_available():
                query = "SELECT calculate_effective_price(%s, %s)"
                res = execute_query_one(query, (pid, dur))
                if res and res[0] and "error" not in res[0]:
                    return res[0].get('display_text', f"₹{res[0]['final_price']}/month")
        except:
            pass
        val = calculate_rent(pid, dur, unit)
        return f"₹{val}/month"

    # Pricing help text based on structure [0:1d, 1:8d, 2:15d, 3:30d, 4:60d, 5:3m, 6:6m, 7:9m, 8:12m+]
    if unit == "months":
        price_info = f"""
Additional Pricing Options (Live Rates):
• 1 Month: {_get_formatted_price(product_id, 1)}
• 3 Months: {_get_formatted_price(product_id, 3)}
• 6 Months: {_get_formatted_price(product_id, 6)}
• 12+ Months: {_get_formatted_price(product_id, 12)}
"""
    else:
        prices = product['prices']
        price_info = "\n".join([f"• Option {i+1}: ₹{p}" for i, p in enumerate(prices)])

    return f"""
*{product['name']}*
Rent for {duration} {unit}: {rent_display}

{price_info}
💡 Tip: Longer durations often result in better monthly rates!
"""


@tool
def create_quote_tool(product_ids: str, duration: int = 6, unit: str = "months") -> str:
    """
    Create a rental quote for multiple products (bundle/package).
    Use this when the customer asks for multiple items together.
    
    Args:
        product_ids: Comma-separated product IDs (e.g., "17,11,18" for bed, fridge, sofa)
        duration: Rental duration value
        unit: Unit of duration ("days" or "months"). Default is "months".
    
    Returns:
        Itemized quote with total monthly rent and security deposit
    """
    try:
        # Parse product IDs
        ids = [int(pid.strip()) for pid in product_ids.split(",")]
    except ValueError:
        return "Invalid product IDs. Please provide comma-separated numbers like '17,11,18'"
    
    # Validate at least some products exist
    valid_ids = [pid for pid in ids if pid in id_to_name]
    if not valid_ids:
        return "None of the provided product IDs are valid. Please search for products first."
    
    # Try using Supabase for effective bundle pricing
    items_data = []
    total_rent = 0
    use_db = False
    
    if unit == "months":
        try:
            from utils.db import is_db_available, execute_query_one
            if is_db_available():
                use_db = True
                for pid in valid_ids:
                    # Call RPC with cart context (valid_ids) to detect combo discounts
                    query = "SELECT calculate_effective_price(%s, %s, %s)"
                    result = execute_query_one(query, (pid, duration, valid_ids))
                    
                    if result and result[0] and "error" not in result[0]:
                        data = result[0]
                        total_rent += data['final_price']
                        items_data.append({
                            "name": data['product_name'],
                            "display": data['display_text']
                        })
                    else:
                        # Item-specific fallback
                        rent = calculate_rent(pid, duration, unit)
                        total_rent += rent
                        items_data.append({
                            "name": id_to_name.get(pid, f"Product {pid}"),
                            "display": f"₹{rent}/month"
                        })
        except Exception as e:
            print(f"⚠️ Pricing Engine Error in bundle: {e}")
            use_db = False

    if not use_db:
        # Complete fallback to local logic
        quote = create_bundle_quote(valid_ids, duration)
        total_rent = quote['total_monthly_rent']
        items_str = "\n".join([f"  • {item['product']}: ₹{item['monthly_rent']}/month" for item in quote['items']])
    else:
        items_str = "\n".join([f"  • {item['name']}: {item['display']}" for item in items_data])
        
    security = min(total_rent * 2, 15000)
    
    return f"""
📋 **RENTAL QUOTE** ({duration} months)

{items_str}

━━━━━━━━━━━━━━━━━━
**Total Monthly Rent: ₹{total_rent}**
**Security Deposit: ₹{security}** (refundable)
━━━━━━━━━━━━━━━━━━

✅ Free delivery & installation
✅ Free maintenance included
✅ Easy returns after minimum period

Would you like to proceed? Share your pincode for delivery availability.
"""


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
        try:
            from utils.db import is_db_available, execute_query_one
            if is_db_available():
                query = "SELECT calculate_effective_price(%s, %s)"
                result = execute_query_one(query, (pid, dur))
                if result and result[0] and "error" not in result[0]:
                    return result[0]['display_text']
        except:
            pass
        rent = calculate_rent(pid, dur)
        return f"₹{rent}/month"

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
