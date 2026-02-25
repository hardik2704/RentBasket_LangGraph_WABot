# RentBasket Product Catalog
# All product data, pricing, and utility functions

from typing import Optional, List, Dict, Any

# ========================================
# PRODUCT ID TO NAME MAPPING
# ========================================
id_to_name = {
    10: "Geyser 20Ltr",
    1010: "Geyser 6 Ltr",
    11: "Fridge 190 Ltr",
    36: "Double Door Fridge",
    12: "SMART LED 32",
    50: "SMART LED 40",
    1008: "SMART LED 43",
    1011: "SMART LED 48",
    13: "Fully Automatic Washing Machine",
    37: "Semi Automatic Washing Machine",
    14: "Window AC",
    60: "Split AC 1.5 Ton",
    15: "Water Purifier",
    1046: "Water Purifier UTC",
    16: "Microwave Solo",
    17: "Double Bed King Non-Storage Basic",
    28: "Wooden Single Bed 6x3 Basic",
    1005: "Upholstered Double Bed King Storage",
    1017: "Double Bed Queen Non-Storage Basic",
    1023: "Std Double Bed Kings 6X6 Storage",
    1024: "Upholstered Double Bed King Non-Storage",
    1025: "Upholstered Double Bed Queen Storage",
    1026: "Upholstered Double Bed Queen Non Storage",
    1027: "Std Queens Double Bed 6X5 storage",
    1031: "Upholstered Single Bed Non-Storage 6X3",
    1053: "Premium Upholstered Double Bed King Storage",
    1054: "Premium Upholstered Double Bed Queen Storage",
    18: "5 Seater Fabric Sofa with Center table",
    1020: "4 Seater Canwood Sofa",
    1039: "3+1+1 Fabric Sofa",
    1041: "Fabric Green Sofa Set with 2 Puffies & CT",
    1042: "3 Seater Fabric Sofa",
    1043: "2 Seater Fabric Sofa",
    1048: "Fabric Grey Sofa Set with 2 Puffies & CT",
    1049: "Fabric Beige Sofa Set with 2 Puffies & CT",
    21: "Mattress Pair 4 Inches",
    44: "Mattress Pair 5 Inches",
    1018: "QS Mattress Pair 6X5X6",
    1019: "Mattress Pair 6 Inches ( 6X6X6 )",
    1050: "QS Mattress One Piece 6 Inches ( 6X5X6 )",
    1051: "QS Mattress One Piece 5 Inches ( 6X6X5 )",
    1052: "QS Mattress Pair 6 Inches ( 6X5X6 )",
    1057: "Mattress Single 4 Inches",
    24: "Inverter, Single Battery",
    45: "Inverter Double Battery",
    56: "Inverter Battery",
    29: "Center Table",
    51: "Side Table Glass Top",
    53: "Coffee Table",
    1033: "6 Seater Dining Table Sheesham Wood",
    1034: "4 Seater Dining Table Sheesham Wood",
    1035: "6 Seater Dining Table Glass Top",
    1036: "6 Seater Dining Table Sheesham Wood Cushion",
    1037: "4 Seater Dining Table Sheesham Wood Cushion",
    1044: "Std Dressing Table",
    1055: "Side Table",
    34: "Gas Stove 2 Burner",
    49: "Gas Stove 3 Burner",
    40: "Study Table",
    41: "Study Chair Premium",
    1058: "Study Chair",
    42: "Book Shelf",
    1015: "Chimney",
    1047: "Sofa Chair P"
}

# ========================================
# CATEGORY TO PRODUCT ID MAPPING
# ========================================
category_to_id = {
    "geyser": [10, 1010],
    "fridge": [11, 36],
    "led": [12, 50, 1008, 1011],
    "tv": [12, 50, 1008, 1011],  # Alias for LED
    "washing machine": [13, 37],
    "ac": [14, 60],
    "air conditioner": [14, 60],  # Alias for AC
    "water purifier": [15, 1046],
    "ro": [15, 1046],  # Alias for water purifier
    "microwave": [16],
    "bed": [17, 28, 1005, 1017, 1023, 1024, 1025, 1026, 1027, 1031, 1053, 1054],
    "sofa": [18, 1020, 1039, 1041, 1042, 1043, 1048, 1049],
    "mattress": [21, 44, 1018, 1019, 1050, 1051, 1052, 1057],
    "inverter": [24, 45, 56],
    "table": [29, 51, 53, 1033, 1034, 1035, 1036, 1037, 1044, 1055],
    "dining table": [1033, 1034, 1035, 1036, 1037],
    "center table": [29],
    "coffee table": [53],
    "gas stove": [34, 49],
    "study": [40, 41, 1058],
    "study table": [40],
    "study chair": [41, 1058],
    "shelf": [42],
    "bookshelf": [42],
    "chimney": [1015],
    "sofa chair": [1047]
}

# ========================================
# PRODUCT ID TO PRICE (3/6/9/12 months)
# ========================================
id_to_price = {
    10: [900, 700, 600, 500],
    1010: [900, 700, 600, 500],
    11: [899, 699, 670, 649],
    36: [1399, 1099, 1099, 1049],
    12: [1100, 900, 750, 700],
    50: [1499, 1199, 1099, 999],
    1008: [1499, 1199, 1099, 999],
    1011: [1699, 1599, 1499, 1399],
    13: [929, 819, 819, 699],
    37: [500, 500, 500, 450],
    14: [1999, 1499, 999, 900],
    60: [3999, 2999, 1999, 1499],
    15: [799, 599, 599, 549],
    1046: [999, 799, 749, 699],
    16: [349, 289, 289, 269],
    17: [699, 549, 520, 499],
    28: [500, 400, 300, 300],
    1005: [1499, 1199, 1049, 999],
    1017: [699, 549, 520, 499],
    1023: [1199, 899, 849, 799],
    1024: [799, 599, 580, 549],
    1025: [1499, 1199, 1049, 999],
    1026: [799, 599, 580, 549],
    1027: [1199, 899, 849, 799],
    1031: [599, 449, 399, 349],
    1053: [1599, 1399, 1249, 1199],
    1054: [1599, 1399, 1249, 1199],
    18: [1499, 1399, 1299, 1199],
    1020: [799, 699, 599, 499],
    1039: [2099, 1750, 1550, 1250],
    1041: [1999, 1799, 1499, 1399],
    1042: [980, 899, 799, 699],
    1043: [750, 699, 650, 599],
    1048: [1999, 1799, 1499, 1399],
    1049: [1999, 1799, 1499, 1399],
    21: [499, 499, 399, 350],
    44: [649, 549, 449, 399],
    1018: [999, 699, 599, 549],
    1019: [999, 699, 599, 549],
    1050: [999, 699, 599, 549],
    1051: [649, 549, 449, 399],
    1052: [999, 699, 599, 549],
    1057: [399, 299, 249, 199],
    24: [1599, 1199, 1099, 999],
    45: [2308, 2115, 1754, 1613],
    56: [1599, 1199, 1099, 999],
    29: [400, 300, 300, 200],
    51: [249, 189, 159, 149],
    53: [1079, 1009, 899, 799],
    1033: [1449, 1249, 1249, 1199],
    1034: [1099, 899, 849, 799],
    1035: [1599, 1199, 999, 899],
    1036: [1549, 1349, 1299, 1249],
    1037: [1099, 999, 949, 899],
    1044: [449, 399, 349, 299],
    1055: [119, 89, 85, 79],
    34: [400, 300, 250, 250],
    49: [400, 350, 300, 300],
    40: [449, 299, 279, 249],
    41: [499, 349, 289, 279],
    1058: [349, 249, 239, 229],
    42: [489, 389, 389, 249],
    1015: [1999, 799, 699, 650],
    1047: [299, 279, 249, 229]
}

# Duration to price index mapping
duration_dict = {3: 0, 6: 1, 9: 2, 12: 3, 18: 3, 24: 3}

# Trending products per category (for bundle recommendations)
TRENDING_PRODUCTS = {
    "sofa": 1042,      # 3 Seater Fabric Sofa
    "bed": 1017,       # Double Bed Queen Non-Storage Basic
    "fridge": 11,      # Fridge 190 Ltr (single door)
    "washing machine": 13,  # Fully Automatic
    "ac": 14,          # Window AC
    "mattress": 44,    # Mattress Pair 5 Inches
    "dining table": 1034,  # 4 Seater Dining Table
    "tv": 1008,        # SMART LED 43
}




# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Get product details by ID."""
    if product_id not in id_to_name:
        return None
    return {
        "id": product_id,
        "name": id_to_name[product_id],
        "prices": id_to_price.get(product_id, [0, 0, 0, 0])
    }


def get_products_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all products in a category."""
    category = category.lower().strip()
    if category not in category_to_id:
        return []
    
    products = []
    for pid in category_to_id[category]:
        product = get_product_by_id(pid)
        if product:
            products.append(product)
    return products


def calculate_rent(product_id: int, duration_months: int) -> Optional[int]:
    """Calculate monthly rent for a product and duration."""
    if product_id not in id_to_price:
        return None
    
    # Map duration to price index
    if duration_months < 6:
        idx = 0  # 3 month rate
    elif duration_months < 9:
        idx = 1  # 6 month rate
    elif duration_months < 12:
        idx = 2  # 9 month rate
    else:
        idx = 3  # 12+ month rate
    
    return id_to_price[product_id][idx]


def get_all_categories() -> List[str]:
    """Get list of all product categories."""
    # Return main categories only (no aliases)
    main_categories = [
        "geyser", "fridge", "tv", "washing machine", "ac", 
        "water purifier", "microwave", "bed", "sofa", "mattress",
        "inverter", "dining table", "center table", "coffee table",
        "gas stove", "study table", "study chair", "bookshelf", "chimney"
    ]
    return main_categories


def search_products_by_name(query: str) -> List[Dict[str, Any]]:
    """Search products by name (partial match)."""
    query = query.lower().strip()
    results = []
    
    for pid, name in id_to_name.items():
        if query in name.lower():
            product = get_product_by_id(pid)
            if product:
                results.append(product)
    
    return results


def format_product_for_display(product: Dict[str, Any], duration: int = 6) -> str:
    """Format product info for WhatsApp display."""
    rent = calculate_rent(product["id"], duration)
    return f"• {product['name']}: ₹{rent}/month ({duration}mo)"


def create_bundle_quote(product_ids: List[int], duration: int) -> Dict[str, Any]:
    """Create a quote for multiple products."""
    items = []
    total_rent = 0
    
    for pid in product_ids:
        product = get_product_by_id(pid)
        if product:
            rent = calculate_rent(pid, duration)
            items.append({
                "product": product["name"],
                "monthly_rent": rent
            })
            total_rent += rent
    
    # Estimate security (roughly 2x monthly rent, capped)
    security = min(total_rent * 2, 15000)
    
    return {
        "items": items,
        "total_monthly_rent": total_rent,
        "security_deposit": security,
        "duration_months": duration
    }
