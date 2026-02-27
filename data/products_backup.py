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

# ========================================
# CHAT SYNONYMS AND VARIANTS
# ========================================

PRODUCT_SYNONYMS = {
  "geyser": [
    "geyser", "geaser", "giser", "gijar", "water heater", "heater",
    "hot water", "hotwater", "bathroom heater", "bath geyser",
    "20 litre geyser", "20l geyser", "20l", "20 ltr",
    "6 litre geyser", "6l geyser", "6l", "6 ltr",
    "instant geyser", "storage geyser"
  ],

  "fridge": [
    "fridge", "freeze", "freez", "refrigerator", "refridgerator",
    "ref", "cooler fridge", "single door fridge", "1 door fridge",
    "double door fridge", "2 door fridge", "2door", "dd fridge",
    "190 ltr fridge", "190l fridge", "190 litre", "small fridge",
    "big fridge"
  ],

  "tv": [
    "tv", "television", "smart tv", "android tv", "led", "led tv",
    "smart led", "32 inch tv", "32in", "32\"", "40 inch tv", "40in", "40\"",
    "43 inch tv", "43in", "43\"", "48 inch tv", "48in", "48\"",
    "screen", "flat tv"
  ],

  "washing machine": [
    "washing machine", "washing", "washer", "wm", "wash machine",
    "fully automatic", "full automatic", "automatic washer",
    "semi automatic", "semi-auto", "semi auto",
    "top load", "topload", "top loading", "top-loader",
    "clothes washer"
  ],

  "ac": [
    "ac", "a/c", "aircon", "air con", "air conditioner", "air conditioning",
    "window ac", "window", "split ac", "split",
    "1.5 ton", "1.5t", "1.5ton", "one and half ton",
    "cooling", "need ac", "room ac"
  ],

  "water purifier": [
    "water purifier", "purifier", "ro", "r/o", "aqua guard", "aquaguard",
    "kent", "livpure", "filter", "water filter", "drinking water machine",
    "uv", "uf", "ro+uv", "ro uv"
  ],

  "microwave": [
    "microwave", "micro wave", "oven", "mw", "solo microwave",
    "microwave oven", "heat food machine", "reheat", "re-heater"
  ],

  "bed": [
    "bed", "double bed", "single bed", "king bed", "queen bed",
    "cot", "palang", "bed frame", "bedframe",
    "storage bed", "box bed", "hydraulic bed",
    "non storage", "non-storage", "without storage",
    "6x6", "6 x 6", "6x5", "6 x 5", "6x3", "6 x 3"
  ],

  "mattress": [
    "mattress", "gadda", "gadde", "foam mattress", "spring mattress",
    "double mattress", "single mattress", "king mattress", "queen mattress",
    "4 inch", "4in", "4\"", "5 inch", "5in", "5\"", "6 inch", "6in", "6\"",
    "pair mattress", "two mattress", "1 piece mattress", "one piece"
  ],

  "sofa": [
    "sofa", "couch", "settee", "l couch", "l-shape", "sofa set",
    "3 seater", "3-seater", "two seater", "2 seater", "1 seater",
    "3+1+1", "sofa with table", "sofa with center table",
    "puffy", "puffies", "pouffe", "ottoman", "center table"
  ],

  "sofa chair": [
    "sofa chair", "single sofa", "1 seater sofa", "accent chair",
    "lounge chair", "arm chair", "armchair", "reading chair"
  ],

  "dining table": [
    "dining table", "dinner table", "table for dining",
    "4 seater dining", "4-seater dining", "6 seater dining", "6-seater dining",
    "dining set", "dining with chairs", "dining table set"
  ],

  "center table": [
    "center table", "centre table", "sofa table", "living table",
    "drawing room table", "hall table"
  ],

  "coffee table": [
    "coffee table", "tea table", "small table", "low table",
    "coffee/center table"
  ],

  "side table": [
    "side table", "bedside table", "night table", "nightstand",
    "lamp table", "corner table"
  ],

  "study table": [
    "study table", "study desk", "desk", "work desk", "office desk",
    "computer table", "laptop table", "table for work", "workstation"
  ],

  "study chair": [
    "study chair", "office chair", "computer chair", "desk chair",
    "chair for study", "work chair", "ergonomic chair"
  ],

  "bookshelf": [
    "bookshelf", "book shelf", "book rack", "rack", "shelf",
    "storage rack", "bookstand"
  ],

  "inverter": [
    "inverter", "power backup", "backup", "ups", "u p s",
    "battery backup", "light backup", "home inverter",
    "single battery", "double battery"
  ],

  "inverter battery": [
    "inverter battery", "battery", "ups battery", "backup battery",
    "tubular battery", "exide battery", "amaron battery"
  ],

  "gas stove": [
    "gas stove", "stove", "gas chulha", "chulha", "cooktop",
    "2 burner", "2-burner", "two burner", "3 burner", "3-burner", "three burner",
    "hob", "gas top"
  ],

  "chimney": [
    "chimney", "kitchen chimney", "exhaust", "exhaust chimney",
    "chimni", "cooker hood", "range hood"
  ],

  "dressing table": [
    "dressing table", "dresser", "mirror table", "makeup table",
    "vanity", "vanity table"
  ],
}

PRODUCT_VARIANTS = {
  10: ["geyser 20", "20l geyser", "20 litre geyser", "20 ltr geyser", "big geyser", "storage geyser 20"],
  1010: ["geyser 6", "6l geyser", "6 litre geyser", "6 ltr geyser", "small geyser", "instant geyser 6"],

  11: ["fridge 190", "190l fridge", "single door fridge", "1 door fridge", "small fridge"],
  36: ["double door fridge", "2 door fridge", "dd fridge", "big fridge", "family fridge"],

  12: ["32 inch tv", "32in tv", "32\" tv", "smart led 32", "led 32"],
  50: ["40 inch tv", "40in tv", "40\" tv", "smart led 40", "led 40"],
  1008: ["43 inch tv", "43in tv", "43\" tv", "smart led 43", "led 43"],
  1011: ["48 inch tv", "48in tv", "48\" tv", "smart led 48", "led 48"],

  13: ["fully automatic washing machine", "automatic wm", "top load automatic", "top load wm"],
  37: ["semi automatic washing machine", "semi auto wm", "semi-automatic"],

  14: ["window ac", "window a/c", "ac window"],
  60: ["split ac", "split a/c", "1.5 ton split", "1.5t split", "one and half ton split"],

  15: ["water purifier", "ro", "ro purifier", "ro+uv", "drinking water purifier"],
  1046: ["utc water purifier", "utc ro", "ro utc", "premium purifier"],

  16: ["microwave", "solo microwave", "mw", "oven (microwave)"],

  34: ["2 burner stove", "two burner stove", "2-burner gas", "gas chulha 2"],
  49: ["3 burner stove", "three burner stove", "3-burner gas", "gas chulha 3"],

  40: ["study table", "study desk", "computer table", "work desk"],
  41: ["premium study chair", "office chair premium", "ergonomic chair premium"],
  1058: ["study chair", "office chair", "desk chair"],

  42: ["bookshelf", "book shelf", "book rack", "rack"],

  1015: ["chimney", "kitchen chimney", "exhaust chimney", "range hood"],

  1047: ["sofa chair", "accent chair", "arm chair", "single sofa chair"],
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
