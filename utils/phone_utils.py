"""
Phone number normalization utilities for RentBasket.
Ensures all incoming WhatsApp numbers are consistently converted to 10-digit local formats.
"""

import re

def normalize_phone(phone: str) -> str:
    """
    Extract the last 10 digits from any phone number string.
    RentBasket serves Delhi NCR, so we assume Indian +91 context.
    
    Examples:
    - "+919958448249" -> "9958448249"
    - "919958448249"  -> "9958448249"
    - "09958448249"   -> "9958448249"
    - "9958448249"    -> "9958448249"
    """
    if not phone:
        return ""
    
    # Remove all non-numeric characters
    clean = re.sub(r'\D', '', str(phone))
    
    # Return last 10 digits if available, otherwise the full clean string
    return clean[-10:] if len(clean) >= 10 else clean

def is_valid_phone(phone: str) -> bool:
    """Check if the normalized phone is a valid 10-digit Indian mobile number."""
    normalized = normalize_phone(phone)
    # Most Indian mobiles start with 6, 7, 8, or 9
    return len(normalized) == 10 and normalized[0] in '6789'
