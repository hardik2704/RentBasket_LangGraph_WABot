# Location Tools for RentBasket WhatsApp Bot
# Tools for checking serviceability by pincode

from langchain_core.tools import tool
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    SERVICEABLE_PINCODES, 
    BORDER_PINCODES,
    SALES_PHONE_GURGAON,
    SALES_PHONE_NOIDA
)
from logistics import DistanceEngine, calculate_delivery_price

# Initialize Distance Engine
distance_engine = DistanceEngine()

# Office Pincodes for distance logging
OFFICE_PINCODES = {
    "Gurgaon": "122003",
    "Noida": "201301"
}


def _extract_pincode(text: str) -> str:
    """Extract 6-digit pincode from text."""
    match = re.search(r'\b\d{6}\b', text)
    return match.group() if match else None


def _identify_city_from_pincode(pincode: str) -> str:
    """Identify city from pincode prefix."""
    if pincode.startswith("122"):
        return "Gurgaon"
    elif pincode.startswith("201"):
        return "Noida"
    elif pincode.startswith("110"):
        return "Delhi"
    elif pincode.startswith("121"):
        return "Faridabad"
    elif pincode.startswith("124"):
        return "Rohtak/Jhajjar"
    else:
        return "Unknown area"


@tool
def check_serviceability_tool(pincode_or_location: str) -> str:
    """
    Check if a location/pincode is serviceable for delivery.
    Use this when customer provides their location or pincode.
    
    Args:
        pincode_or_location: 6-digit pincode or location text containing pincode
    
    Returns:
        Serviceability status and next steps
    """
    # Extract pincode if embedded in text
    pincode = _extract_pincode(pincode_or_location)
    
    if not pincode:
        # Try common location names
        location_lower = pincode_or_location.lower()
        
        # Check for known non-serviceable areas
        if any(area in location_lower for area in ["delhi", "saket", "cp", "connaught", "dwarka", "rohini", "janakpuri"]):
            return f"""
❌ **Delhi is not serviceable currently.**

We currently serve only:
• Gurgaon (all sectors except Manesar)
• Noida (all sectors)

📞 For special arrangements, contact:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

If you have an alternate address in our service area, please share it!
"""
        
        if any(area in location_lower for area in ["faridabad", "greater faridabad"]):
            return f"""
❌ **Faridabad is not serviceable currently.**

We serve Gurgaon & Noida only.

📞 Contact our team for updates: {SALES_PHONE_GURGAON}
"""
        
        if any(area in location_lower for area in ["gurgaon", "gurugram", "sector"]):
            return """
✅ **We serve Gurgaon!**

Please share your exact pincode so I can confirm:
• Delivery availability
• Fastest delivery slot

Example: 122001, 122018, etc.
"""
        
        if any(area in location_lower for area in ["noida", "greater noida"]):
            return """
✅ **We serve Noida!**

Please share your exact pincode so I can confirm:
• Delivery availability  
• Fastest delivery slot

Example: 201301, 201306, etc.
"""
        
        # Unknown location - ask for pincode
        return """
To check delivery availability, please share your **6-digit pincode**.

We currently serve:
• Gurgaon (all sectors except Manesar)
• Noida (all sectors)
"""
    # We have a pincode - check serviceability
    city = _identify_city_from_pincode(pincode)

    # Calculate distance to nearest office dynamically
    min_dist = float('inf')
    closest_office = None
    for office, off_pin in OFFICE_PINCODES.items():
        dist = distance_engine.estimate_road_km(off_pin, pincode)
        if dist is not None and dist < min_dist:
            min_dist = dist
            closest_office = office
            
    is_serviceable = pincode in SERVICEABLE_PINCODES or min_dist <= 20
    is_border = pincode in BORDER_PINCODES or (20 < min_dist <= 35)
    
    if is_serviceable:
        dist_str = f" (approx {min_dist:.1f} km from {closest_office} office)" if closest_office else ""
        return f"""
✅ **Great news! Pincode {pincode} ({city}) is serviceable!**

We can deliver to your location{dist_str}.
• Standard delivery: 2-5 business days
• Express delivery: Subject to availability

Would you like to proceed with your order?
"""
    
    if is_border:
        dist_str = f" (approx {min_dist:.1f} km from {closest_office})" if closest_office else ""
        return f"""
⚠️ **Pincode {pincode} is in a border area or slightly far{dist_str}.**

We might be able to cater to this location with special arrangement.

📞 Please contact our sales team:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

They can confirm availability and arrange priority delivery.
"""
    
    # Not serviceable
    if city in ["Delhi", "Faridabad", "Rohtak/Jhajjar"]:
        return f"""
❌ **Sorry, pincode {pincode} ({city}) is not serviceable.**

We currently serve only Gurgaon & Noida.

📞 For special requests, contact:
• Call: {SALES_PHONE_GURGAON}

If you have an alternate address in Gurgaon or Noida, please share it!
"""
    
    # Non-serviceable, far away
    return f"""
❌ **Sorry, pincode {pincode} is outside our delivery range.**

We currently serve Gurgaon and Noida.

📞 Please contact our team if you need further assistance:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}
"""


@tool
def get_service_areas_tool() -> str:
    """
    Get list of all serviceable areas.
    Use this when customer asks about service areas or delivery locations.
    
    Returns:
        List of serviceable cities and areas
    """
    return f"""
📍 **RentBasket Service Areas:**

✅ **Gurgaon (Gurugram)**
• All main sectors covered
• Excluding: Manesar industrial area

✅ **Noida**
• All sectors covered
• Greater Noida: Limited areas

❌ **Not Covered Currently:**
• Delhi NCR (all areas)
• Faridabad
• Ghaziabad (most areas)

📞 **Contact for special requests:**
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

Share your pincode and I'll confirm exact availability!
"""
