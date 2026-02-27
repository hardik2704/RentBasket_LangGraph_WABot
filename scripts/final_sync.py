import os
import sys
import re
import json
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

API_BASE = "https://testapi.rentbasket.com"
AUTH_KEY = "gyfgfvytfrdctyftyftfyiyftrdrtufc"
PRODUCTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/products.py")

KNOWN_IDS = [
    10, 1010, 11, 36, 12, 50, 1008, 1011, 13, 37, 14, 60, 15, 1046, 16, 17, 28, 1005, 1017, 1023, 
    1024, 1025, 1026, 1027, 1031, 1053, 1054, 18, 1020, 1039, 1041, 1042, 1043, 1048, 1049, 21, 
    44, 1018, 1019, 1050, 1051, 1052, 1057, 24, 45, 56, 29, 51, 53, 1033, 1034, 1035, 1036, 1037, 
    1044, 1055, 34, 49, 40, 41, 1058, 42, 1015, 1047
]

def auth_headers():
    return {"Accept": "application/json", "Authorization-Key": AUTH_KEY}

def fetch_product(pid: int):
    # Try common cat/sub (1,1) first
    url = f"{API_BASE}/get-amenity-types"
    params = {"category_id": 1, "subcategory_id": 1, "absolute_amenity_type": pid}
    try:
        r = requests.get(url, params=params, headers=auth_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "Success" and data.get("data") and data["data"].get("items"):
                return data["data"]["items"][0]
    except Exception: pass
    return None

def update_catalog(products: List[Dict[str, Any]]):
    with open(PRODUCTS_FILE, "r") as f: content = f.read()

    # Create new mappings
    id_to_name = {}
    id_to_price = {}
    
    # Existing structure check
    name_match = re.search(r"id_to_name = \{(.*?)\}", content, re.DOTALL)
    price_match = re.search(r"id_to_price = \{(.*?)\}", content, re.DOTALL)
    
    # We'll use the existing dicts as base to not lose anything not in API
    if name_match: id_to_name = eval("{" + name_match.group(1) + "}")
    if price_match: id_to_price = eval("{" + price_match.group(1) + "}")
    
    for p in products:
        pid = int(p["amenity_type_id"])
        id_to_name[pid] = p["amenity_type_name"]
        # Comprehensive pricing structure:
        # [0:1d, 1:8d, 2:15d, 3:30d, 4:60d, 5:3m, 6:6m, 7:9m, 8:12m+]
        id_to_price[pid] = [
            p.get("rent_01d", 0),
            p.get("rent_08d", 0),
            p.get("rent_15d", 0),
            p.get("rent_30d", 0), 
            p.get("rent_60d", 0),
            p.get("rent_3", 0),
            p.get("rent_6", 0),
            p.get("rent_9", 0),
            p.get("rent_12", 0)
        ]
    
    # Build strings
    name_str = "id_to_name = {\n"
    for pid in sorted(id_to_name.keys()):
        name_str += f"    {pid}: {json.dumps(id_to_name[pid])},\n"
    name_str += "}"
    
    price_str = "id_to_price = {\n"
    for pid in sorted(id_to_price.keys()): price_str += f"    {pid}: {id_to_price[pid]},\n"
    price_str += "}"
    
    content = re.sub(r"id_to_name = \{.*?\}", name_str, content, flags=re.DOTALL)
    content = re.sub(r"id_to_price = \{.*?\}", price_str, content, flags=re.DOTALL)
    
    with open(PRODUCTS_FILE, "w") as f: f.write(content)
    print(f"✅ Catalog updated with {len(products)} live products.")

def main():
    print(f"🚀 Syncing {len(KNOWN_IDS)} products...")
    found = []
    for i, pid in enumerate(KNOWN_IDS):
        if i % 10 == 0: print(f"  .. processing {i}/{len(KNOWN_IDS)}")
        p = fetch_product(pid)
        if p: found.append(p)
    
    if found:
        update_catalog(found)
        try:
            import mcp_server
            print("🧠 Refreshing index...")
            mcp_server.build_semantic_index()
        except Exception as e: print(f"Index error: {e}")
    else: print("No products found from API.")

if __name__ == "__main__":
    main()
