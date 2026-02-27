import os
import sys
import re
import json
import requests
from typing import Dict, Any, List, Optional, Set
from dotenv import load_dotenv

# Ensure parent path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

API_BASE = "https://testapi.rentbasket.com"
AUTH_KEY = "gyfgfvytfrdctyftyftfyiyftrdrtufc"
PRODUCTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/products.py")

def auth_headers():
    return {
        "Accept": "application/json",
        "Authorization-Key": AUTH_KEY
    }

def fetch_product_from_api(cat_id: int, sub_cat_id: int, type_id: int) -> Optional[Dict[str, Any]]:
    url = f"{API_BASE}/get-amenity-types"
    params = {
        "category_id": cat_id,
        "subcategory_id": sub_cat_id,
        "absolute_amenity_type": type_id,
    }
    try:
        r = requests.get(url, params=params, headers=auth_headers(), timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "Success" and data.get("data") and data["data"].get("items"):
                return data["data"]["items"][0]
    except Exception:
        pass
    return None

def update_products_file(new_products: List[Dict[str, Any]]):
    """
    Update data/products.py with new product data and structure.
    """
    with open(PRODUCTS_FILE, "r") as f:
        content = f.read()

    # 1. Update id_to_name
    id_to_name_match = re.search(r"id_to_name = \{(.*?)\}", content, re.DOTALL)
    if id_to_name_match:
        try:
            id_to_name_str = id_to_name_match.group(1)
            # Use current content to build the actual dict
            id_to_name = eval("{" + id_to_name_str + "}")
            for p in new_products:
                id_to_name[int(p["amenity_type_id"])] = p["amenity_type_name"]
            
            new_str = "id_to_name = {\n"
            for pid in sorted(id_to_name.keys()):
                new_str += f"    {pid}: \"{id_to_name[pid]}\",\n"
            new_str += "}"
            content = re.sub(r"id_to_name = \{.*?\}", new_str, content, flags=re.DOTALL)
        except Exception as e: print(f"Error id_to_name: {e}")

    # 2. Update id_to_price
    id_to_price_match = re.search(r"id_to_price = \{(.*?)\}", content, re.DOTALL)
    if id_to_price_match:
        try:
            id_to_price = eval("{" + id_to_price_match.group(1) + "}")
            for p in new_products:
                prices = [p.get("rent_3", 0), p.get("rent_6", 0), p.get("rent_9", 0), p.get("rent_12", 0)]
                id_to_price[int(p["amenity_type_id"])] = prices
            
            new_str = "id_to_price = {\n"
            for pid in sorted(id_to_price.keys()):
                new_str += f"    {pid}: {id_to_price[pid]},\n"
            new_str += "}"
            content = re.sub(r"id_to_price = \{.*?\}", new_str, content, flags=re.DOTALL)
        except Exception as e: print(f"Error id_to_price: {e}")

    # 3. Structural Update: category_to_id
    cat_match = re.search(r"category_to_id = \{(.*?)\}", content, re.DOTALL)
    if cat_match:
        try:
            category_to_id = eval("{" + cat_match.group(1) + "}")
            for p in new_products:
                pid = int(p["amenity_type_id"])
                # API gives category_id
                api_cat_id = f"cat_{p['category_id']}"
                
                # Check if it fits in any existing category by name match
                name = p["amenity_type_name"].lower()
                matched = False
                for cat_name, pids in category_to_id.items():
                    if cat_name in name or any(sub_cat in name for sub_cat in cat_name.split()):
                        if pid not in pids:
                            pids.append(pid)
                            category_to_id[cat_name] = sorted(list(set(pids)))
                        matched = True
                        break
                
                if not matched:
                    if api_cat_id not in category_to_id:
                        category_to_id[api_cat_id] = []
                    if pid not in category_to_id[api_cat_id]:
                        category_to_id[api_cat_id].append(pid)
                        category_to_id[api_cat_id] = sorted(list(set(category_to_id[api_cat_id])))

            new_str = "category_to_id = {\n"
            for cat in sorted(category_to_id.keys()):
                new_str += f"    \"{cat}\": {category_to_id[cat]},\n"
            new_str += "}"
            content = re.sub(r"category_to_id = \{.*?\}", new_str, content, flags=re.DOTALL)
        except Exception as e: print(f"Error category_to_id: {e}")

    with open(PRODUCTS_FILE, "w") as f:
        f.write(content)
    print(f"✅ Updated {PRODUCTS_FILE} with {len(new_products)} products.")

def full_sync():
    print("🚀 Starting FINAL programmatic sync...")
    discovered = {}
    
    # Range based on previous hits
    # I'll scan the most productive cat/sub IDs found so far
    scan_points = [(1,1), (2,12), (3,1), (4,1), (1,12), (2,1)]
    
    for cat, sub in scan_points:
        print(f"🔍 Scanning Cat: {cat}, Sub: {sub}...")
        # Check current data/products.py IDs + ranges
        # IDs 1-100 and 1000-1100 cover 95% of RentBasket products
        for type_id in list(range(1, 151)) + list(range(1000, 1101)):
            product = fetch_product_from_api(cat, sub, type_id)
            if product:
                pid = int(product["amenity_type_id"])
                if pid not in discovered:
                    print(f"   ✨ Found: {product['amenity_type_name']} (ID: {pid})")
                    discovered[pid] = product
                    
    if discovered:
        update_products_file(list(discovered.values()))
        
        # Trigger ChromaDB build
        try:
            print("🧠 Refreshing semantic index...")
            import mcp_server
            result = mcp_server.build_semantic_index()
            print(f"✅ {result}")
        except Exception as e:
            print(f"Warning: Could not refresh ChromaDB: {e}")
    else:
        print("⚠️ No products discovered.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", type=int, help="Sync specific product ID")
    parser.add_argument("--full", action="store_true", help="Run full sync")
    args = parser.parse_args()
    
    if args.type:
        product = fetch_product_from_api(1, 1, args.type)
        if product: update_products_file([product])
        else: print("❌ Product not found.")
    elif args.full:
        full_sync()
    else:
        print("Please specify --type ID or --full")
