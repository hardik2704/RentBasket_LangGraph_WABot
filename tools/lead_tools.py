from langchain_core.tools import tool
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import upsert_lead, get_lead
from utils.phone_utils import normalize_phone
from data.products import apply_discount, calculate_rent, id_to_name

@tool
def sync_lead_data_tool(
    phone: str,
    name: Optional[str] = None,
    push_name: Optional[str] = None,
    extracted_name: Optional[str] = None,
    delivery_location: Optional[Dict[str, Any]] = None,
    product_preferences: Optional[List[Dict[str, Any]]] = None,
    final_cart: Optional[List[Dict[str, Any]]] = None,
    lead_stage: Optional[str] = None,
    conversation_summary: Optional[str] = None,
    budget_range: Optional[Dict[str, Any]] = None,
    preferences_notes: Optional[str] = None,
    duration_months: Optional[int] = None,
) -> str:
    """
    Update the lead data in Firestore 'leads' collection.
    Use this tool whenever the user provides new information (location, prefs, items).

    budget_range: dict with optional keys 'min' and 'max' (monthly ₹ amounts).
                  e.g. {"min": 1000, "max": 3000}
    preferences_notes: free-text string of any stated preferences
                       e.g. "wants AC, prefers furnished, PG room, bachelor"
    duration_months: rental duration in months (e.g. 4, 6, 12). Persist this whenever the customer states a duration.
    """
    lead_data = {
        "last_message_timestamp": datetime.now(timezone.utc)
    }
    
    # Store all name variations
    if push_name: lead_data["push_name"] = push_name
    if extracted_name: lead_data["extracted_name"] = extracted_name
    
    # Set primary 'name' - prioritize extracted if available
    primary_name = extracted_name or name or push_name
    if primary_name: lead_data["name"] = primary_name

    if phone: lead_data["phone"] = phone
    if delivery_location: lead_data["delivery_location"] = delivery_location

    # Accumulate product_preferences (merge with existing, don't overwrite)
    if product_preferences:
        try:
            normalized = normalize_phone(phone) if phone else phone
            existing_lead = get_lead(normalized) if normalized else None
            existing_prefs = existing_lead.get("product_preferences", []) if existing_lead else []
            # Merge: add new prefs that aren't already tracked
            existing_ids = {str(p.get("product_id", p.get("category", ""))) for p in existing_prefs}
            for pref in product_preferences:
                pref_key = str(pref.get("product_id", pref.get("category", "")))
                if pref_key not in existing_ids:
                    existing_prefs.append(pref)
            lead_data["product_preferences"] = existing_prefs
        except Exception:
            lead_data["product_preferences"] = product_preferences

    if lead_stage: lead_data["lead_stage"] = lead_stage
    if conversation_summary: lead_data["conversation_summary"] = conversation_summary
    if budget_range: lead_data["budget_range"] = budget_range
    if preferences_notes: lead_data["preferences_notes"] = preferences_notes
    if duration_months: lead_data["duration_months"] = duration_months
    
    # Process final_cart with defaults
    if final_cart:
        processed_cart = []
        for item in final_cart:
            pid = item.get("product_id")
            if not pid: continue
            
            qty = item.get("quantity", 1)
            duration = item.get("duration", 12) # Default 12 months per instructions
            
            # Fetch default price if not provided
            price = item.get("final_price")
            if not price:
                try:
                    orig_rent = calculate_rent(int(pid), duration)
                    price = apply_discount(orig_rent) # 30% off standard
                except:
                    price = 0
            
            processed_cart.append({
                "product_id": str(pid),
                "quantity": qty,
                "duration": duration,
                "final_price": price
            })
        lead_data["final_cart"] = processed_cart
        # If cart exists, escalate stage to cart_created if currently lower
        if not lead_stage:
            lead_data["lead_stage"] = "cart_created"

    try:
        normalized = normalize_phone(phone) if phone else phone
        if normalized:
            lead_data["phone"] = normalized
        upsert_lead(normalized, lead_data)
        return f"Lead successfully updated for {normalized}."
    except Exception as e:
        return f"Failed to update lead in Firestore: {str(e)}"
