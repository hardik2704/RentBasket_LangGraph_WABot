# RentBasket Product Catalog
# All product data, pricing, and utility functions

from typing import Optional, List, Dict, Any

# ========================================
# PRODUCT ID TO NAME MAPPING
# ========================================
id_to_name = {
    10: "Geyser 20Ltr",
    11: "Fridge 190 Ltr",
    12: "SMART LED 32\"",
    13: "Fully Automatic Washing M/c",
    14: "Window AC",
    15: "Water Purifier",
    16: "Microwave Solo 20Ltr",
    17: "Double Bed King Non-Storage Basic",
    18: "5 Seater Fabric Sofa with Center table",
    21: "Mattress Pair 4 Inches",
    24: "Inverter, Single Battery",
    28: "Wooden Single Bed 6x3 Basic",
    29: "Center Table",
    34: "Gas Stove 2 Burner",
    36: "Double Door Fridge",
    37: "Semi Automatic Washing M/c",
    40: "Study Table",
    41: "Study Chair Premium",
    42: "Book Shelf",
    44: "Mattress Pair 5 Inches",
    45: "Inverter Double Battery",
    49: "Gas Stove 3 Burner",
    50: "SMART LED 40\"",
    51: "Side Table Glass Top",
    53: "Coffee Table",
    56: "Inverter Battery",
    60: "Split AC 1.5 Ton",
    1005: "Upholstered Double Bed King Storage",
    1008: "SMART LED 43\"",
    1010: "Geyser 6 Ltr",
    1011: "SMART LED 48\"",
    1015: "Chimney",
    1017: "Double Bed Queen Non-Storage Basic",
    1018: "QS Mattress Pair 6X5X6",
    1019: "Mattress Pair 6 Inches ( 6X6X6 )",
    1020: "4 Seater Canwood Sofa",
    1023: "Std Double Bed  Kings 6X6 Storage",
    1024: "Upholstered Double Bed King Non-Storage",
    1025: "Upholstered Double Bed Queen Storage",
    1026: "Upholstered Double Bed Queen Non Storage",
    1027: "Std Queens Double Bed 6X5 storage",
    1031: "Upholstered Single Bed Non-Storage 6X3",
    1033: "6 Seater Dining Table Sheesham Wood",
    1034: "4 Seater Dining Table Sheesham Wood",
    1035: "6 Seater Dining Table Glass Top",
    1036: "6 Seater Dining Table Sheesham Wood Cushion",
    1037: "4 Seater Dining Table Sheesham Wood Cushion",
    1039: "3+1+1 Fabric Sofa",
    1041: "Fabric Green Sofa Set with 2 Puffies & CT",
    1042: "3 Seater Fabric Sofa",
    1043: "2 Seater Fabric Sofa",
    1044: "Std Dressing Table",
    1046: "Water Purifier UTC",
    1047: "Sofa Chair P",
    1048: "Fabric Grey Sofa Set with 2 Puffies & CT",
    1049: "Fabric Beige Sofa Set with 2 Puffies & CT",
    1050: "QS Mattress One Piece 6 Inches ( 6X5X6 )",
    1051: "QS Mattress One Piece 5 Inches ( 6X5X5 )",
    1052: "QS Mattress Pair 6 Inches ( 6X5X6 )",
    1053: "Premium Upholstered Double Bed King Storage",
    1054: "Premium Upholstered Double Bed Queen Storage",
    1055: "Side Table",
    1057: "Mattress Single 4 Inches",
    1058: "Study Chair ",
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
    10: [882, 1411, 2016, 2646, 3717, 1260, 980, 840, 700],
    11: [1481, 2221, 3173, 4160, 5200, 1763, 1371, 1313, 1273],
    12: [1294, 1940, 2772, 1848, 4543, 1540, 1260, 1050, 980],
    13: [1275, 1639, 2341, 1561, 3837, 1301, 1147, 1147, 979],
    14: [2586, 3879, 5542, 3694, 9083, 3079, 2099, 1399, 1260],
    15: [940, 1409, 2014, 1342, 3301, 1119, 839, 839, 769],
    16: [411, 616, 880, 586, 1442, 489, 405, 405, 377],
    17: [1028, 1233, 1762, 1174, 2888, 979, 769, 728, 699],
    18: [1763, 2644, 3778, 2518, 6192, 2099, 1959, 1819, 1679],
    21: [587, 880, 1258, 838, 2062, 699, 699, 559, 490],
    24: [1881, 2821, 4030, 2686, 6605, 2239, 1679, 1539, 1399],
    28: [588, 882, 1260, 840, 2065, 700, 560, 420, 420],
    29: [470, 705, 1008, 672, 1652, 560, 420, 420, 280],
    34: [470, 705, 1008, 672, 1652, 560, 420, 350, 350],
    36: [1920, 2468, 3526, 2350, 5779, 1959, 1539, 1539, 1469],
    37: [588, 882, 1260, 840, 2065, 700, 700, 700, 630],
    40: [528, 792, 1132, 754, 1855, 629, 419, 391, 349],
    41: [587, 880, 1258, 838, 2062, 699, 489, 405, 391],
    42: [685, 545, 545, 349],
    44: [764, 1145, 1636, 1090, 2681, 909, 769, 629, 559],
    45: [2714, 4071, 5815, 3877, 9531, 3231, 2961, 2456, 2258],
    49: [470, 705, 1008, 672, 1652, 560, 490, 420, 420],
    50: [2351, 2644, 3778, 2518, 6192, 2099, 1679, 1539, 1399],
    51: [293, 439, 628, 418, 1029, 349, 265, 223, 209],
    53: [1269, 1903, 2719, 1813, 4457, 1511, 1413, 1259, 1119],
    56: [1881, 2821, 4030, 2686, 6605, 2239, 1679, 1539, 1399],
    60: [4703, 7054, 10078, 6718, 16517, 5599, 4199, 2799, 2099],
    1005: [1763, 2644, 3778, 2518, 6192, 2099, 1679, 1469, 1399],
    1008: [2351, 2644, 3778, 2518, 6192, 2099, 1679, 1539, 1399],
    1010: [1058, 1587, 2268, 1512, 3717, 1260, 980, 840, 700],
    1011: [2998, 2997, 4282, 2854, 7018, 2379, 2239, 2099, 1959],
    1015: [2799, 1119, 979, 910],
    1017: [1096, 1233, 1762, 1174, 2888, 979, 769, 728, 699],
    1018: [1175, 1762, 2518, 1678, 4127, 1399, 979, 839, 769],
    1019: [1175, 1762, 2518, 1678, 4127, 1399, 979, 839, 769],
    1020: [1058, 1586, 2266, 1510, 3714, 1259, 979, 839, 699],
    1023: [1410, 2115, 3022, 2014, 4953, 1679, 1259, 1189, 1119],
    1024: [1175, 1409, 2014, 1342, 3301, 1119, 839, 812, 769],
    1025: [1763, 2644, 3778, 2518, 6192, 2099, 1679, 1469, 1399],
    1026: [1175, 1409, 2014, 1342, 3301, 1119, 839, 812, 769],
    1027: [1763, 2115, 3022, 2014, 4953, 1679, 1259, 1189, 1119],
    1031: [705, 1057, 1510, 1006, 2475, 839, 629, 559, 489],
    1033: [3267, 2556, 3652, 2434, 5985, 2029, 1749, 1749, 1679],
    1034: [1939, 1939, 2770, 1846, 4540, 1539, 1259, 1189, 1119],
    1035: [1881, 2821, 4030, 2686, 6605, 2239, 1679, 1399, 1259],
    1036: [3340, 2732, 3904, 2602, 6398, 2169, 1889, 1819, 1749],
    1037: [2155, 1939, 2770, 1846, 4540, 1539, 1399, 1329, 1259],
    1039: [2469, 3703, 5290, 3526, 8670, 2939, 2450, 2170, 1750],
    1041: [2939, 3526, 5038, 3358, 8257, 2799, 2519, 2099, 1959],
    1042: [1729, 1728, 2469, 1646, 4047, 1372, 1259, 1119, 979],
    1043: [1103, 1323, 1890, 1260, 3097, 1050, 979, 910, 839],
    1044: [528, 792, 1132, 754, 1855, 629, 559, 489, 419],
    1046: [1175, 1762, 2518, 1678, 4127, 1399, 1119, 1049, 979],
    1047: [419, 391, 349, 321],
    1048: [2939, 3526, 5038, 3358, 8257, 2799, 2519, 2099, 1959],
    1049: [2939, 3526, 5038, 3358, 8257, 2799, 2519, 2099, 1959],
    1050: [1175, 1762, 2518, 1678, 4127, 1399, 979, 839, 769],
    1051: [827, 1145, 1636, 1090, 2681, 909, 769, 629, 559],
    1052: [1175, 1762, 2518, 1678, 4127, 1399, 979, 839, 769],
    1053: [2351, 2821, 4030, 2686, 6605, 2239, 1959, 1749, 1679],
    1054: [2351, 2821, 4030, 2686, 6605, 2239, 1959, 1749, 1679],
    1055: [199, 210, 300, 200, 492, 167, 125, 119, 111],
    1057: [470, 704, 1006, 670, 1649, 559, 419, 349, 279],
    1058: [489, 349, 335, 321],
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
    "clothes washer", "washing m/c"
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
  1048: ["7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set"],
  1041: ["7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set"],
  1049: ["7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set"]

}

# Duration to price index mapping
# Index map for duration keys:
# 0: 1 day, 1: 8 days, 2: 15 days, 3: 30 days, 4: 60 days
# 5: 3 months, 6: 6 months, 7: 9 months, 8: 12 months+
duration_dict = {
    "1d": 0, "8d": 1, "15d": 2, "30d": 3, "60d": 4,
    3: 5, 6: 6, 8: 6, 9: 7, 12: 8, 18: 8, 24: 8
}

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


def calculate_rent(product_id: int, duration: int, unit: str = "months") -> Optional[int]:
    """
    Calculate rent for a product based on duration.
    Handle Short-term (days) and Long-term (months).
    """
    if product_id not in id_to_price:
        return None
    
    prices = id_to_price[product_id]
    
    if unit == "days":
        if duration < 8:
            idx = 0  # 1 day rate (1-7 days)
        elif duration < 15:
            idx = 1  # 8 day rate (8-14 days)
        elif duration < 30:
            idx = 2  # 15 day rate (15-29 days)
        elif duration < 60:
            idx = 3  # 30 day rate (30-59 days)
        else:
            idx = 4  # 60 day rate
    else:
        # Months
        if duration < 3:
            idx = 3  # Fallback to 30d short term if < 3 months requested in months
        elif duration < 6:
            idx = 5  # 3 month rate
        elif duration < 9:
            idx = 6  # 6 month rate (includes 8 months per requirement)
        elif duration < 12:
            idx = 7  # 9 month rate
        else:
            idx = 8  # 12+ month rate (up to 24 months)
            
    # Safety check for list length (if legacy data exists)
    if idx < len(prices):
        return prices[idx]
    return prices[-1]


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


def create_bundle_quote(product_ids: List[int], duration: int, unit: str = "months") -> Dict[str, Any]:
    """Create a quote for multiple products."""
    items = []
    total_rent = 0
    
    for pid in product_ids:
        product = get_product_by_id(pid)
        if product:
            rent = calculate_rent(pid, duration, unit)
            items.append({
                "product": product["name"],
                "monthly_rent" if unit == "months" else "total_rent": rent
            })
            total_rent += rent
    
    # Estimate security (roughly 2x monthly rent, capped)
    # For daily rentals, security might be different, but let's keep it simple for now or use a heuristic.
    security = min(total_rent * 2, 15000)
    
    return {
        "items": items,
        "total_monthly_rent" if unit == "months" else "total_rent": total_rent,
        "security_deposit": security,
        "duration": duration,
        "unit": unit
    }
