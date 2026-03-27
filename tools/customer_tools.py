"""
Tools for looking up and verifying customer profiles in the RentBasket database.
Used by the Orchestrator to route between Sales and Support agents.
"""

import os
import sys
from typing import Dict, Any, Optional

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db
from utils.phone_utils import normalize_phone

def get_customer_profile(phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve customer profile from Firestore based on phone number.
    Returns None if customer not found or Firebase unavailable.
    """
    db = get_db()
    if not db:
        return None
        
    normalized = normalize_phone(phone)
    if not normalized:
        return None

    try:
        # Match by phone number as Document ID
        doc = db.collection("customers").document(normalized).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                "id": doc.id,
                "name": data.get("name"),
                "email": data.get("email"),
                "phone": data.get("phone_number") or normalized,
                "location": data.get("location_address"),
                "pincode": data.get("pincode"),
                "rented_items": data.get("rented_items", []),
                "member_since": data.get("member_since"),
                "is_active": data.get("is_active", False)
            }
        return None
    except Exception as e:
        print(f"⚠️ Error fetching customer profile from Firebase: {e}")
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
