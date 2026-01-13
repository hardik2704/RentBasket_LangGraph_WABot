# Office Location Tool for RentBasket WhatsApp Bot
# Provides office addresses and directions

from langchain_core.tools import tool
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GURGAON_OFFICE, NOIDA_OFFICE, WEBSITE


@tool
def get_office_location_tool(city: str = None) -> str:
    """
    Get RentBasket office location, address and hours.
    Use this when customer asks about showroom, office location, or where to visit.
    
    Args:
        city: Which office to get info for ("gurgaon", "noida", or None for both)
    
    Returns:
        Office address, hours, and contact information
    """
    if city:
        city_lower = city.lower().strip()
        
        if any(word in city_lower for word in ["gurgaon", "gurugram", "ggn"]):
            return f"""
📍 **RentBasket Gurgaon Office**

**Address:** {GURGAON_OFFICE['address']}

**Opening Hours:** {GURGAON_OFFICE['hours']}

**Contact:** {GURGAON_OFFICE['phone']}

You can visit our office to see products in person! We recommend calling ahead to confirm availability of specific items.

🗺️ [View on Google Maps](https://maps.google.com/?q={GURGAON_OFFICE['address'].replace(' ', '+')})
"""
        
        if any(word in city_lower for word in ["noida", "greater noida"]):
            return f"""
📍 **RentBasket Noida Office**

**Address:** {NOIDA_OFFICE['address']}

**Opening Hours:** {NOIDA_OFFICE['hours']}

**Contact:** {NOIDA_OFFICE['phone']}

You can visit our office to see products in person! We recommend calling ahead to confirm availability of specific items.

🗺️ [View on Google Maps](https://maps.google.com/?q={NOIDA_OFFICE['address'].replace(' ', '+')})
"""
    
    # Return both offices
    return f"""
📍 **RentBasket Offices - Visit Us!**

━━━━━━━━━━━━━━━━━━
**GURGAON OFFICE**
━━━━━━━━━━━━━━━━━━
📍 {GURGAON_OFFICE['address']}
🕐 {GURGAON_OFFICE['hours']}
📞 {GURGAON_OFFICE['phone']}

━━━━━━━━━━━━━━━━━━
**NOIDA OFFICE**
━━━━━━━━━━━━━━━━━━
📍 {NOIDA_OFFICE['address']}
🕐 {NOIDA_OFFICE['hours']}
📞 {NOIDA_OFFICE['phone']}

✨ You can visit either office to see our products in person!
💡 We recommend calling ahead to check availability of specific items.

🌐 Online catalog: {WEBSITE}
"""
