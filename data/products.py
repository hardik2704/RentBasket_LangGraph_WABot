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
    1041: "7 Seater Fabric Green Sofa Set with 2 Puffies & CT",
    1042: "3 Seater Fabric Sofa",
    1043: "2 Seater Fabric Sofa",
    1044: "Std Dressing Table",
    1046: "Water Purifier UTC",
    1047: "Sofa Chair P",
    1048: "7 Seater Fabric Grey Sofa Set with 2 Puffies & CT",
    1049: "7 Seater Fabric Beige Sofa Set with 2 Puffies & CT",
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
    "pair mattress", "two mattress", "1 piece mattress", "one piece",
    "bed mattress", "bed with mattress", "bed + mattress"
  ],

  "sofa": [
    "sofa", "couch", "settee", "l couch", "l-shape", "sofa set",
    "3 seater", "3-seater", "two seater", "2 seater", "1 seater",
    "3+1+1", "sofa with table", "sofa with center table",
    "puffy", "puffies", "pouffe", "ottoman", "center table",
    "l shape sofa", "l-shape sofa", "l shaped sofa", "sectional sofa", "corner sofa"
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
  # ── GEYSERS ──
  10: [
    "geyser 20", "20l geyser", "20 litre geyser", "20 ltr geyser", "big geyser",
    "storage geyser 20", "storage geyser", "large geyser", "20 litre water heater",
    "bathroom geyser", "geyser for bathroom", "20l water heater", "tank geyser"
  ],
  1010: [
    "geyser 6", "6l geyser", "6 litre geyser", "6 ltr geyser", "small geyser",
    "instant geyser 6", "instant geyser", "kitchen geyser", "geyser for kitchen",
    "6 litre water heater", "6l water heater", "mini geyser", "compact geyser",
    "instant water heater", "point of use geyser"
  ],

  # ── FRIDGES ──
  11: [
    "fridge 190", "190l fridge", "single door fridge", "1 door fridge", "small fridge",
    "190 litre fridge", "190 ltr fridge", "compact fridge", "mini fridge",
    "basic fridge", "standard fridge", "direct cool fridge", "single door refrigerator",
    "fridge for bachelor", "bachelor fridge", "1 door refrigerator", "190l refrigerator"
  ],
  36: [
    "double door fridge", "2 door fridge", "dd fridge", "big fridge", "family fridge",
    "double door refrigerator", "frost free fridge", "2 door refrigerator",
    "large fridge", "fridge for family", "two door fridge", "two door refrigerator",
    "dd refrigerator", "spacious fridge", "convertible fridge"
  ],

  # ── TVs / LEDs ──
  12: [
    "32 inch tv", "32in tv", "32\" tv", "smart led 32", "led 32",
    "32 inch led", "32 inch smart tv", "32\" led", "32\" smart tv",
    "small tv", "bedroom tv", "basic tv", "32 inch television",
    "hd tv 32", "hd led 32", "compact tv"
  ],
  50: [
    "40 inch tv", "40in tv", "40\" tv", "smart led 40", "led 40",
    "40 inch led", "40 inch smart tv", "40\" led", "40\" smart tv",
    "medium tv", "living room tv 40", "40 inch television",
    "full hd tv 40", "full hd led 40"
  ],
  1008: [
    "43 inch tv", "43in tv", "43\" tv", "smart led 43", "led 43",
    "43 inch led", "43 inch smart tv", "43\" led", "43\" smart tv",
    "43 inch television", "full hd tv 43", "full hd led 43",
    "standard tv", "living room tv", "hall tv"
  ],
  1011: [
    "48 inch tv", "48in tv", "48\" tv", "smart led 48", "led 48",
    "48 inch led", "48 inch smart tv", "48\" led", "48\" smart tv",
    "big tv", "large tv", "48 inch television", "premium tv",
    "4k tv", "large screen tv", "drawing room tv"
  ],

  # ── WASHING MACHINES ──
  13: [
    "fully automatic washing machine", "automatic wm", "top load automatic", "top load wm",
    "fully automatic", "automatic washing machine", "full auto washing machine",
    "top load washing machine", "top loader", "top loading washing machine",
    "auto wm", "automatic washer", "fully auto wm"
  ],
  37: [
    "semi automatic washing machine", "semi auto wm", "semi-automatic",
    "semi auto washing machine", "twin tub", "twin tub washing machine",
    "semi automatic", "semi washer", "semi wm", "manual washing machine",
    "budget washing machine", "cheap washing machine"
  ],

  # ── ACs ──
  14: [
    "window ac", "window a/c", "ac window", "window air conditioner",
    "window type ac", "basic ac", "affordable ac", "budget ac",
    "non inverter ac", "window cooler", "room ac window"
  ],
  60: [
    "split ac", "split a/c", "1.5 ton split", "1.5t split", "one and half ton split",
    "split air conditioner", "wall mounted ac", "inverter ac", "1.5 ton ac",
    "split type ac", "1.5 ton air conditioner", "premium ac", "energy efficient ac",
    "silent ac", "bedroom ac split"
  ],

  # ── WATER PURIFIERS ──
  15: [
    "water purifier", "ro", "ro purifier", "ro+uv", "drinking water purifier",
    "ro water purifier", "water filter", "ro filter", "ro uv purifier",
    "basic water purifier", "standard water purifier", "aquaguard",
    "kent", "livpure", "drinking water filter", "purifier for home"
  ],
  1046: [
    "utc water purifier", "utc ro", "ro utc", "premium purifier",
    "utc purifier", "advanced water purifier", "premium water purifier",
    "hot cold purifier", "uv purifier", "premium ro",
    "water purifier utc", "best water purifier"
  ],

  # ── MICROWAVE ──
  16: [
    "microwave", "solo microwave", "mw", "oven (microwave)",
    "microwave oven", "micro wave", "20 litre microwave", "20l microwave",
    "solo oven", "reheat oven", "basic microwave", "kitchen microwave",
    "food warmer", "microwave 20ltr"
  ],

  # ── BEDS ──
  17: [
    "king bed basic", "king bed non storage", "king bed without storage",
    "double bed king", "king size bed", "6x6 bed", "6 by 6 bed",
    "basic king bed", "king cot", "king bed frame", "king palang",
    "double bed basic", "king size cot", "non storage king bed",
    "king bed no storage", "large bed basic", "diwan king"
  ],
  28: [
    "single bed", "single bed basic", "single bed wooden", "wooden single bed",
    "6x3 bed", "6 by 3 bed", "small bed", "basic single bed",
    "single cot", "single palang", "single bed frame", "one person bed",
    "1 person bed", "hostel bed", "pg bed", "compact bed", "narrow bed"
  ],
  1005: [
    "upholstered king bed storage", "upholstered king bed", "cushioned king bed",
    "padded king bed", "king bed with storage", "fabric king bed",
    "king storage bed upholstered", "soft king bed", "king bed cushion",
    "king bed hydraulic", "box bed king", "upholstered bed king storage"
  ],
  1017: [
    "queen bed basic", "queen bed non storage", "queen bed without storage",
    "double bed queen", "queen size bed", "6x5 bed", "6 by 5 bed",
    "basic queen bed", "queen cot", "queen bed frame", "queen palang",
    "queen size cot", "non storage queen bed", "queen bed no storage",
    "medium bed basic", "standard double bed"
  ],
  1023: [
    "king bed storage", "standard king bed storage", "6x6 storage bed",
    "king storage bed", "king box bed", "king hydraulic bed",
    "king bed with drawer", "storage bed king size", "double bed king storage",
    "king size storage bed", "6x6 bed with storage", "king bed with storage"
  ],
  1024: [
    "upholstered king bed no storage", "upholstered king bed non storage",
    "cushioned king bed without storage", "padded king bed no storage",
    "fabric king bed no storage", "king bed upholstered non storage",
    "soft king bed no storage"
  ],
  1025: [
    "upholstered queen bed storage", "upholstered queen bed", "cushioned queen bed",
    "padded queen bed", "queen bed with storage", "fabric queen bed",
    "queen storage bed upholstered", "soft queen bed", "queen bed cushion",
    "queen bed hydraulic", "box bed queen", "upholstered bed queen storage"
  ],
  1026: [
    "upholstered queen bed no storage", "upholstered queen bed non storage",
    "cushioned queen bed without storage", "padded queen bed no storage",
    "fabric queen bed no storage", "queen bed upholstered non storage",
    "soft queen bed no storage"
  ],
  1027: [
    "queen bed storage", "standard queen bed storage", "6x5 storage bed",
    "queen storage bed", "queen box bed", "queen hydraulic bed",
    "queen bed with drawer", "storage bed queen size", "double bed queen storage",
    "queen size storage bed", "6x5 bed with storage"
  ],
  1031: [
    "upholstered single bed", "cushioned single bed", "padded single bed",
    "fabric single bed", "soft single bed", "single bed upholstered",
    "upholstered bed 6x3", "single bed non storage", "premium single bed",
    "fancy single bed"
  ],
  1053: [
    "premium king bed", "premium king bed storage", "premium upholstered king",
    "premium upholstered king bed", "best king bed", "luxury king bed",
    "top king bed", "high end king bed", "premium bed king storage",
    "premium cushioned king bed", "premium padded king bed"
  ],
  1054: [
    "premium queen bed", "premium queen bed storage", "premium upholstered queen",
    "premium upholstered queen bed", "best queen bed", "luxury queen bed",
    "top queen bed", "high end queen bed", "premium bed queen storage",
    "premium cushioned queen bed", "premium padded queen bed"
  ],

  # ── SOFAS ──
  18: [
    "5 seater sofa", "5 seater couch", "five seater sofa", "5 seater sofa set",
    "sofa with center table", "sofa with table", "sofa and table combo",
    "5 seater fabric sofa", "fabric sofa 5 seater", "sofa set 5 seater",
    "family sofa", "living room sofa 5", "5 seater settee",
    "sofa combo with center table", "large sofa", "big sofa"
  ],
  1020: [
    "4 seater sofa", "4 seater couch", "four seater sofa", "4 seater sofa set",
    "canwood sofa", "wooden sofa", "wooden frame sofa", "sofa 4 seater",
    "4 seater settee", "wood sofa", "compact sofa set", "medium sofa"
  ],
  1039: [
    "3+1+1 sofa", "3 1 1 sofa", "3+1+1 fabric sofa", "5 seater sofa set",
    "sofa set 3+1+1", "3 plus 1 plus 1 sofa", "three plus one plus one",
    "sofa set with singles", "sofa set with single chairs", "3 1 1 couch",
    "3+1+1 couch", "modular sofa set"
  ],
  1041: [
    "7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set",
    "green sofa set", "fabric green sofa", "sofa with puffies", "sofa with ottoman",
    "sofa set with puffies green", "green 7 seater", "seven seater sofa green",
    "large sofa set green", "sofa with puffy and table green", "7-seater sofa", "7-seater couch",
    "l shape sofa green", "sectional sofa green", "corner sofa green"
  ],
  1042: [
    "3 seater sofa", "3 seater couch", "three seater sofa", "3 seater fabric sofa",
    "small sofa", "compact sofa", "sofa 3 seater", "3 seat couch",
    "three seat sofa", "3 person sofa", "living room sofa 3", "basic sofa",
    "affordable sofa", "budget sofa"
  ],
  1043: [
    "2 seater sofa", "2 seater couch", "two seater sofa", "2 seater fabric sofa",
    "loveseat", "love seat", "couple sofa", "small couch", "sofa 2 seater",
    "2 seat couch", "two seat sofa", "2 person sofa", "compact couch",
    "mini sofa", "apartment sofa"
  ],
  1047: [
    "sofa chair", "accent chair", "arm chair", "single sofa chair",
    "armchair", "single seater sofa", "1 seater sofa", "lounge chair",
    "reading chair", "sofa single", "one seater sofa", "sofa chair p",
    "occasional chair"
  ],
  1048: [
    "7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set",
    "grey sofa set", "gray sofa set", "fabric grey sofa", "sofa with puffies",
    "sofa with ottoman", "sofa set with puffies grey", "grey 7 seater",
    "seven seater sofa grey", "large sofa set grey", "gray 7 seater",
    "sofa with puffy and table grey", "7-seater sofa", "7-seater couch",
    "l shape sofa grey", "sectional sofa grey", "corner sofa grey", "l shape sofa"
  ],
  1049: [
    "7 seater sofa", "7 seater couch", "7 seater sofa set", "7 seater couch set",
    "beige sofa set", "fabric beige sofa", "sofa with puffies",
    "sofa with ottoman", "sofa set with puffies beige", "beige 7 seater",
    "seven seater sofa beige", "large sofa set beige", "cream sofa set",
    "sofa with puffy and table beige", "neutral sofa set", "7-seater sofa", "7-seater couch",
    "l shape sofa beige", "sectional sofa beige", "corner sofa beige"
  ],

  # ── MATTRESSES ──
  21: [
    "mattress pair 4 inch", "4 inch mattress", "4 inch mattress pair",
    "thin mattress", "basic mattress pair", "mattress 4 inches",
    "double mattress 4 inch", "gadda pair 4 inch", "king mattress pair 4",
    "foam mattress 4 inch", "4in mattress pair", "budget mattress pair",
    "affordable mattress", "6x6 mattress 4 inch"
  ],
  44: [
    "mattress pair 5 inch", "5 inch mattress", "5 inch mattress pair",
    "medium mattress", "standard mattress pair", "mattress 5 inches",
    "double mattress 5 inch", "gadda pair 5 inch", "king mattress pair 5",
    "foam mattress 5 inch", "5in mattress pair", "comfortable mattress pair",
    "6x6 mattress 5 inch"
  ],
  1018: [
    "queen mattress pair 6x5", "qs mattress pair", "queen size mattress pair",
    "queen mattress pair", "6x5 mattress pair", "6x5x6 mattress pair",
    "queen mattress set", "queen gadda pair", "queen foam mattress pair",
    "mattress pair queen size", "queen bed mattress pair"
  ],
  1019: [
    "king mattress pair 6 inch", "6 inch mattress pair", "6 inch king mattress",
    "thick mattress pair", "mattress pair 6 inches", "6x6x6 mattress pair",
    "king size mattress pair 6", "premium mattress pair", "thick gadda pair",
    "foam mattress 6 inch pair", "6in mattress pair king"
  ],
  1050: [
    "queen mattress one piece 6 inch", "qs mattress single piece",
    "queen mattress 1 piece", "queen one piece mattress", "6x5 mattress single",
    "queen mattress 6 inch single", "single piece queen mattress",
    "queen mattress one piece", "6x5x6 mattress one piece", "queen gadda 6 inch"
  ],
  1051: [
    "queen mattress one piece 5 inch", "qs mattress 5 inch single piece",
    "queen mattress 1 piece 5 inch", "queen one piece mattress 5",
    "6x5 mattress 5 inch single", "queen mattress 5 inch single",
    "single piece queen mattress 5 inch", "6x5x5 mattress one piece",
    "queen gadda 5 inch"
  ],
  1052: [
    "queen mattress pair 6 inch", "qs mattress pair 6 inch",
    "queen size mattress pair 6", "6x5x6 mattress pair",
    "queen mattress set 6 inch", "queen gadda pair 6 inch",
    "6 inch queen mattress pair", "thick queen mattress pair"
  ],
  1057: [
    "single mattress", "single bed mattress", "single mattress 4 inch",
    "mattress single bed", "6x3 mattress", "small mattress",
    "single gadda", "hostel mattress", "pg mattress", "one person mattress",
    "1 person mattress", "compact mattress", "single foam mattress",
    "narrow mattress", "thin single mattress"
  ],

  # ── INVERTERS & BATTERIES ──
  24: [
    "single battery inverter", "inverter single battery", "inverter 1 battery",
    "small inverter", "basic inverter", "home inverter single",
    "inverter for 1bhk", "1 battery inverter", "one battery inverter",
    "compact inverter", "inverter for small home", "basic power backup"
  ],
  45: [
    "double battery inverter", "inverter double battery", "inverter 2 battery",
    "big inverter", "large inverter", "home inverter double",
    "inverter for 2bhk", "2 battery inverter", "two battery inverter",
    "heavy duty inverter", "inverter for large home", "full home inverter"
  ],
  56: [
    "inverter battery", "battery for inverter", "ups battery",
    "tubular battery", "backup battery", "replacement battery",
    "inverter battery only", "extra battery", "additional battery",
    "exide battery", "amaron battery", "battery only"
  ],

  # ── GAS STOVES ──
  34: [
    "2 burner stove", "two burner stove", "2-burner gas", "gas chulha 2",
    "2 burner gas stove", "two burner gas stove", "2 burner cooktop",
    "small gas stove", "compact gas stove", "gas stove 2 burner",
    "chulha 2 burner", "2 flame stove", "basic gas stove"
  ],
  49: [
    "3 burner stove", "three burner stove", "3-burner gas", "gas chulha 3",
    "3 burner gas stove", "three burner gas stove", "3 burner cooktop",
    "big gas stove", "large gas stove", "gas stove 3 burner",
    "chulha 3 burner", "3 flame stove", "family gas stove"
  ],

  # ── STUDY FURNITURE ──
  40: [
    "study table", "study desk", "computer table", "work desk",
    "office desk", "work table", "laptop table", "workstation",
    "writing desk", "home office table", "wfh desk", "work from home desk",
    "student desk", "homework table"
  ],
  41: [
    "premium study chair", "office chair premium", "ergonomic chair premium",
    "premium office chair", "premium desk chair", "high back chair",
    "executive chair", "boss chair", "manager chair", "premium computer chair",
    "premium ergonomic chair", "study chair premium", "best study chair"
  ],
  1058: [
    "study chair", "office chair", "desk chair", "computer chair",
    "basic study chair", "basic office chair", "standard chair",
    "work chair", "swivel chair", "revolving chair", "chair for study",
    "chair for desk", "home chair", "wfh chair", "work from home chair"
  ],

  # ── BOOKSHELF ──
  42: [
    "bookshelf", "book shelf", "book rack", "rack", "storage rack",
    "book stand", "bookcase", "display shelf", "open shelf",
    "wall shelf", "study shelf", "room shelf", "organizer shelf",
    "book storage", "multi purpose rack"
  ],

  # ── CHIMNEY ──
  1015: [
    "chimney", "kitchen chimney", "exhaust chimney", "range hood",
    "cooker hood", "kitchen exhaust", "smoke extractor", "chimni",
    "kitchen hood", "cooking chimney", "auto clean chimney",
    "kitchen ventilation", "fume extractor"
  ],

  # ── TABLES ──
  29: [
    "center table", "centre table", "sofa table", "living room table",
    "hall table", "drawing room table", "ct", "wooden center table",
    "center table for sofa", "tea table center"
  ],
  51: [
    "side table glass", "glass side table", "side table glass top",
    "glass top side table", "bedside glass table", "glass nightstand",
    "fancy side table", "designer side table"
  ],
  53: [
    "coffee table", "tea table", "low table", "small table",
    "sofa side table", "coffee center table", "living room low table",
    "wooden coffee table", "ct", "drawing room table"
  ],
  1055: [
    "side table", "bedside table", "nightstand", "night stand",
    "lamp table", "bed side table", "small side table", "basic side table",
    "bedroom side table", "end table"
  ],
  1044: [
    "dressing table", "dresser", "vanity table", "makeup table",
    "vanity", "mirror table", "cosmetic table", "dressing unit",
    "dresser with mirror", "bedroom dresser", "std dressing table",
    "standard dressing table"
  ],

  # ── DINING TABLES ──
  1033: [
    "6 seater dining table sheesham", "6 seater wooden dining table",
    "6 seater dining table wood", "sheesham dining table 6 seater",
    "wooden dining 6 seater", "6 person dining table wood",
    "six seater dining table sheesham", "sheesham wood 6 seater dining",
    "large wooden dining table", "dining table 6 sheesham"
  ],
  1034: [
    "4 seater dining table sheesham", "4 seater wooden dining table",
    "4 seater dining table wood", "sheesham dining table 4 seater",
    "wooden dining 4 seater", "4 person dining table wood",
    "four seater dining table sheesham", "sheesham wood 4 seater dining",
    "small wooden dining table", "dining table 4 sheesham",
    "compact dining table"
  ],
  1035: [
    "6 seater dining table glass", "6 seater glass dining table",
    "glass top dining table 6", "glass dining table 6 seater",
    "6 person dining table glass", "six seater glass dining",
    "modern dining table 6 seater", "glass dining 6 seater",
    "designer dining table"
  ],
  1036: [
    "6 seater dining table cushion", "6 seater dining table sheesham cushion",
    "cushion dining table 6 seater", "6 seater dining with cushion chairs",
    "sheesham dining cushion 6", "wooden dining cushion 6 seater",
    "comfortable dining table 6", "padded dining chairs 6 seater",
    "6 seater dining set cushion"
  ],
  1037: [
    "4 seater dining table cushion", "4 seater dining table sheesham cushion",
    "cushion dining table 4 seater", "4 seater dining with cushion chairs",
    "sheesham dining cushion 4", "wooden dining cushion 4 seater",
    "comfortable dining table 4", "padded dining chairs 4 seater",
    "4 seater dining set cushion", "compact cushion dining table"
  ],
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
    """Search products by name (partial match) and PRODUCT_VARIANTS."""
    query = query.lower().strip()
    query_words = set(query.split())  # Sub-words for combined intent matching
    
    results = []
    seen_ids = set()
    
    # 1. Match against product names
    for pid, name in id_to_name.items():
        name_lower = name.lower()
        if query in name_lower or all(w in name_lower for w in query_words if len(w) > 2):
            product = get_product_by_id(pid)
            if product and pid not in seen_ids:
                results.append(product)
                seen_ids.add(pid)
    
    # 2. Match against PRODUCT_VARIANTS (e.g. "7 seater sofa" → IDs 1048, 1041, 1049)
    # Also support searching for combined intents like "bed mattress" matching "mattress" and "bed" tags
    for pid, variants in PRODUCT_VARIANTS.items():
        if pid not in seen_ids:
            for variant in variants:
                var_lower = variant.lower()
                if query in var_lower or var_lower in query or all(w in var_lower for w in query_words if len(w) > 2):
                    product = get_product_by_id(pid)
                    if product:
                        results.append(product)
                        seen_ids.add(pid)
                    break
    
    return results


def format_product_for_display(product: Dict[str, Any], duration: int = 6) -> str:
    """Format product info for WhatsApp display."""
    rent = calculate_rent(product["id"], duration)
    return f"• {product['name']}: ₹{rent}/month ({duration}mo)"


def apply_discount(original_price: int, discount_percent: int = 30, upfront: bool = False) -> int:
    """
    Apply global 30% discount first. 
    If upfront=True, apply an ADDITIONAL 10% discount on the result.
    Returns whole number (no decimals).
    """
    if not original_price:
        return 0
    # Tier 1: 30% Flat
    multiplier = (100 - discount_percent) / 100
    discounted = original_price * multiplier
    
    # Tier 2: 10% Upfront (additional)
    if upfront:
        discounted *= 0.90
        
    return int(round(discounted))


def format_price_comparison(original_price: int, duration: int = 6, unit: str = "months") -> str:
    """
    Format price in the user-requested: ~Original~ Final Rs +GST format.
    Includes the 'Best Price' (Upfront) for 12 months.
    """
    final_price = apply_discount(original_price)
    unit_str = "/mo" if unit == "months" else ""
    base_fmt = f"~₹{original_price:,}~ ₹{final_price:,}{unit_str} +GST"
    
    # If 12 months, also show the Upfront Price (additional 10% off)
    if duration >= 12 and unit == "months":
        upfront_price = apply_discount(original_price, upfront=True)
        return f"{base_fmt}\n    🚀 *Upfront Deal: ₹{upfront_price:,}/mo +GST*"
        
    return base_fmt


def create_bundle_quote(product_ids: List[int], duration: int, unit: str = "months") -> Dict[str, Any]:
    """Create a quote for multiple products with 30% discount and 18% GST."""
    items = []
    total_original = 0
    total_discounted = 0
    
    for pid in product_ids:
        product = get_product_by_id(pid)
        if product:
            orig_rent = calculate_rent(pid, duration, unit)
            discounted_rent = apply_discount(orig_rent)
            items.append({
                "product": product["name"],
                "original_rent": orig_rent,
                "monthly_rent": discounted_rent, # Final discounted rent
                "display_text": format_price_comparison(orig_rent, duration, unit)
            })
            total_original += orig_rent
            total_discounted += discounted_rent
    
    # Calculate GST (18%)
    gst_amount = int(round(total_discounted * 0.18))
    grand_total = total_discounted + gst_amount
    
    # Estimate security (roughly 2x monthly rent, capped at 15k)
    security = min(total_discounted * 2, 15000)
    
    return {
        "items": items,
        "total_original": total_original,
        "total_discounted": total_discounted,
        "gst_amount": gst_amount,
        "grand_total": grand_total,
        "security_deposit": security,
        "duration": duration,
        "unit": unit
    }
