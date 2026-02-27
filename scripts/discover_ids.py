import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://testapi.rentbasket.com"
AUTH_KEY = "gyfgfvytfrdctyftyftfyiyftrdrtufc"

def auth_headers():
    return {
        "Accept": "application/json",
        "Authorization-Key": AUTH_KEY
    }

def probe_product(cat_id, sub_cat_id, type_id):
    url = f"{API_BASE}/get-amenity-types"
    params = {
        "category_id": cat_id,
        "subcategory_id": sub_cat_id,
        "absolute_amenity_type": type_id,
    }
    try:
        r = requests.get(url, params=params, headers=auth_headers(), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success" or data.get("data"):
                return data
    except Exception as e:
        pass
    return None

def main():
    print("🔍 Probing for Fridge 190 Ltr (ID 11)...")
    # In many systems, categories are small ints
    # I'll try common ranges
    target_type = 11
    
    # Based on data/products.py, Fridge is a category. 
    # Let's try to find it.
    for cat in range(1, 100):
        for sub in range(1, 100):
            result = probe_product(cat, sub, target_type)
            if result:
                print(f"✅ Found! Category: {cat}, SubCategory: {sub}")
                print(json.dumps(result, indent=2))
                return

if __name__ == "__main__":
    main()
