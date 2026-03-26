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

def get_customer_profile(phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve customer profile from the database based on phone number.
    Returns None if customer not found or DB unavailable.
    """
    if not is_db_available():
        return None
        
    query = """
    SELECT name, email, phone_number, location_address, pincode, rented_items, member_since, is_active
    FROM customers
    WHERE phone_number = %s OR phone_number = %s
    LIMIT 1;
    """
    
    # Handle both raw phone and potentially prefixed phone from WhatsApp
    clean_phone = phone.replace("+", "").strip()
    # If it's a 12-digit number starting with 91, also try the 10-digit version
    short_phone = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
    
    try:
        row = execute_query_one(query, (clean_phone, short_phone))
        if row:
            return {
                "name": row[0],
                "email": row[1],
                "phone": row[2],
                "location": row[3],
                "pincode": row[4],
                "rented_items": row[5], # This is JSONB, psycopg2 usually parses to list/dict
                "member_since": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
                "is_active": row[7]
            }
        return None
    except Exception as e:
        print(f"⚠️ Error fetching customer profile: {e}")
        return None

def verify_customer_status(phone: str) -> Dict[str, Any]:
    """
    High-level verification check for the orchestrator.
    Returns verification flags and profile data.
    """
    profile = get_customer_profile(phone)
    if profile:
        return {
            "is_verified": True,
            "profile": profile,
            "active_rentals": profile.get("rented_items", [])
        }
    return {
        "is_verified": False,
        "profile": None,
        "active_rentals": []
    }
