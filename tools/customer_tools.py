"""
Tools for looking up and verifying customer profiles in the RentBasket database.
Used by the Orchestrator to route between Sales and Support agents.
"""

import os
import sys
from typing import Dict, Any, Optional

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_query_one, is_db_available
from utils.phone_utils import normalize_phone

def get_customer_profile(phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve customer profile from the database based on phone number.
    Returns None if customer not found or DB unavailable.
    """
    if not is_db_available():
        return None
        
    normalized = normalize_phone(phone)
    if not normalized:
        return None

    # Match last 10 digits
    query = """
    SELECT id, name, email, phone_number, location_address, pincode, rented_items, member_since, is_active
    FROM customers
    WHERE phone_number LIKE %s
    LIMIT 1;
    """
    
    try:
        row = execute_query_one(query, (f"%{normalized}",))
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "location": row[4],
                "pincode": row[5],
                "rented_items": row[6],
                "member_since": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
                "is_active": row[8]
            }
        return None
    except Exception as e:
        print(f"⚠️ Error fetching customer profile: {e}")
        return None

def verify_customer_status(phone: str) -> Dict[str, Any]:
    """
    High-level verification check for the orchestrator.
    Categorizes user as: active_customer, past_customer, lead, or unknown.
    """
    profile = get_customer_profile(phone)
    
    if profile:
        is_active = profile.get("is_active", False)
        status = "active_customer" if is_active else "past_customer"
        return {
            "is_verified": True,
            "status": status,
            "profile": profile,
            "active_rentals": profile.get("rented_items", []) if is_active else []
        }
    
    # In a real CRM, we'd check a 'leads' table here too.
    # For now, if found in no table, they are unknown or lead.
    return {
        "is_verified": False,
        "status": "unknown", # Orchestrator can upgrade this to 'lead' after first interaction
        "profile": None,
        "active_rentals": []
    }
