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
        # Suggest available categories
        categories = list(set(category_to_id.keys()))[:10]
        return f"No products found matching '{query}'. Available categories: {', '.join(categories)}"
    
    return f"Found {len(results)} products:\n" + "\n".join(results[:10])


@tool
def get_price_tool(product_id: int, duration_months: int = 6) -> str:
    """
    Get the rental price for a specific product.
    Use this when the customer asks for the rent/price of a specific item.
    
    Args:
        product_id: The product ID (use search_products_tool to find IDs)
        duration_months: Rental duration in months (minimum 3, any duration accepted). If Duration is less than 3 months, redirect them to the "RentBasket Mini".
                        Pricing is tiered: 3-5mo=3mo rate, 6-8mo=6mo rate, 9-11mo=9mo rate, 12+mo=12mo rate.
    
    Returns:
        Product name and monthly rental price
    """
    product = get_product_by_id(product_id)
    if not product:
        return f"Product with ID {product_id} not found. Please search for products first."
    
    # Redirect to RentBasket Mini for short-term rentals
    if duration_months < 3:
        return f"""
⚡ **RentBasket Mini** - Short-Term Rentals!

For rentals under 3 months, we have **RentBasket Mini** - our special short-term rental service!

📞 **Contact our sales team to know more:**
• Gurgaon: +91 9958187021
• Noida: +91 9958440038

They'll help you with 1-2 month rental options. 😊
"""
    
    rent = calculate_rent(product_id, duration_months)
    
    # Get prices for all durations for comparison
    prices = product['prices']
    
    return f"""
**{product['name']}**
Monthly rent for {duration_months} months: ₹{rent}/month

All duration options:
• 3 months: ₹{prices[0]}/month
• 6 months: ₹{prices[1]}/month  
• 9 months: ₹{prices[2]}/month
• 12 months: ₹{prices[3]}/month

💡 Tip: Longer duration = lower monthly rent!
"""


@tool
def create_quote_tool(product_ids: str, duration_months: int = 6) -> str:
    """
    Create a rental quote for multiple products (bundle/package).
    Use this when the customer asks for multiple items together.
    
    Args:
        product_ids: Comma-separated product IDs (e.g., "17,11,18" for bed, fridge, sofa)
        duration_months: Rental duration in months. Default is 6 months.
    
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
    
    # Create quote
    quote = create_bundle_quote(valid_ids, duration_months)
    
    # Format response
    items_list = "\n".join([
        f"  • {item['product']}: ₹{item['monthly_rent']}/month" 
        for item in quote['items']
    ])
    
    return f"""
📋 **RENTAL QUOTE** ({quote['duration_months']} months)

{items_list}

━━━━━━━━━━━━━━━━━━
**Total Monthly Rent: ₹{quote['total_monthly_rent']}**
**Security Deposit: ₹{quote['security_deposit']}** (refundable)
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
    if category and category.lower() in TRENDING_PRODUCTS:
        pid = TRENDING_PRODUCTS[category.lower()]
        product = get_product_by_id(pid)
        rent_6mo = calculate_rent(pid, 6)
        return f"🔥 Trending in {category}: {product['name']} - ₹{rent_6mo}/month (6mo)"
    
    # Return all trending products
    results = ["🔥 **Trending Products:**\n"]
    for cat, pid in TRENDING_PRODUCTS.items():
        product = get_product_by_id(pid)
        if product:
            rent = calculate_rent(pid, 6)
            results.append(f"• {cat.title()}: {product['name']} - ₹{rent}/mo")
    
    return "\n".join(results)
