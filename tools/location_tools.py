# Location Tools for RentBasket WhatsApp Bot
# Tools for checking serviceability by pincode using RentBasket API

from langchain_core.tools import tool
import re
import os
import requests

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    SALES_PHONE_GURGAON,
    SALES_PHONE_NOIDA,
    RENTBASKET_API_BASE,
    MAX_SERVICEABLE_DISTANCE_KM,
)

# V1.2: The RentBasket backend API is authenticated with a JWT that was
# issued by RentBasket itself. This JWT is INDEPENDENT of the self-signed
# cart-link JWT (which uses RENTBASKET_JWT_SECRET). Keep them separate so
# rotating one never breaks the other.
#
# Precedence:
#   1. RENTBASKET_API_JWT  (preferred, new env var)
#   2. RENTBASKET_JWT      (legacy env var, back-compat)
#   3. Hardcoded original  (last-resort fallback)
_RENTBASKET_API_JWT = (
    os.environ.get("RENTBASKET_API_JWT")
    or os.environ.get("RENTBASKET_JWT")
    or "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzUwNjExMDQsImV4cCI6MTE3NzUwNjExMDQsImRhdGEiOnsiaWQiOjEsImVtYWlsIjoidmlqYXltYWhlbkBnbWFpbC5jb20ifX0.WZBiCCK6R0MmubatJWpLerv5GXSSmFHC5-IjZw7jE4M"
)


def _api_auth_headers() -> dict:
    """Auth headers for RentBasket API using JWT Bearer token."""
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {_RENTBASKET_API_JWT}",
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


def _call_distance_api(pincode: str) -> dict | None:
    """
    Call RentBasket API to get distance from service centers.

    Returns:
        dict with keys:
            gurgaon_km          - actual distance from Gurgaon office (float)
            noida_km            - actual distance from Noida office (float)
            gurgaon_max_km      - max serviceable distance for Gurgaon (float)
            noida_max_km        - max serviceable distance for Noida (float)
        or None on failure.
    """
    url = f"{RENTBASKET_API_BASE}/get-distance-from-service-centers?pin={pincode}"
    try:
        resp = requests.get(url, headers=_api_auth_headers(), timeout=10)
        resp.raise_for_status()
        body = resp.json()
        return _parse_distances(body)
    except Exception as e:
        print(f"   [ServiceabilityAPI] Error for pin {pincode}: {e}")
        return None


def _parse_distances(body: dict) -> dict | None:
    """
    Parse the API response.

    Expected shape:
    {
      "status": "Success",
      "responseCode": 200,
      "data": {
        "distance_values": {
          "servicingdistFromGGNOffice": "20",
          "servicingdistFromNoidaOffice": "20",
          "distFromGGNOffice": 1.659,
          "distFromNoidaOffice": 35.371
        }
      }
    }
    """
    try:
        dv = body["data"]["distance_values"]

        gurgaon_km = float(dv["distFromGGNOffice"])
        noida_km = float(dv["distFromNoidaOffice"])

        # Max serviceable distance comes from the API itself; fall back to config
        gurgaon_max = float(dv.get("servicingdistFromGGNOffice", MAX_SERVICEABLE_DISTANCE_KM))
        noida_max = float(dv.get("servicingdistFromNoidaOffice", MAX_SERVICEABLE_DISTANCE_KM))

        result = {
            "gurgaon_km": gurgaon_km,
            "noida_km": noida_km,
            "gurgaon_max_km": gurgaon_max,
            "noida_max_km": noida_max,
        }
        print(f"   [ServiceabilityAPI] Parsed: {result}")
        return result
    except (KeyError, TypeError, ValueError) as e:
        print(f"   [ServiceabilityAPI] Parse error: {e} | raw: {body}")
        return None


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

        if any(area in location_lower for area in ["delhi", "saket", "cp", "connaught", "dwarka", "rohini", "janakpuri"]):
            return f"""
Delhi is not serviceable currently.

We currently serve only:
- Gurgaon (all sectors except Manesar)
- Noida (all sectors)

For special arrangements, contact:
- Gurgaon: {SALES_PHONE_GURGAON}
- Noida: {SALES_PHONE_NOIDA}

If you have an alternate address in our service area, please share it!
"""

        if any(area in location_lower for area in ["faridabad", "greater faridabad"]):
            return f"""
Faridabad is not serviceable currently.

We serve Gurgaon & Noida only.

Contact our team for updates: {SALES_PHONE_GURGAON}
"""

        if any(area in location_lower for area in ["gurgaon", "gurugram", "sector"]):
            return """
We serve Gurgaon!

Please share your exact pincode so I can confirm:
- Delivery availability
- Fastest delivery slot

Example: 122001, 122018, etc.
"""

        if any(area in location_lower for area in ["noida", "greater noida"]):
            return """
We serve Noida!

Please share your exact pincode so I can confirm:
- Delivery availability
- Fastest delivery slot

Example: 201301, 201306, etc.
"""

        # Unknown location - ask for pincode
        return """
To check delivery availability, please share your *6-digit pincode*.

We currently serve:
- Gurgaon (all sectors except Manesar)
- Noida (all sectors)
"""

    # ── We have a pincode -- call the API ──
    city = _identify_city_from_pincode(pincode)
    distances = _call_distance_api(pincode)

    if distances is None:
        return f"""
Sorry, I couldn't verify serviceability for pincode {pincode} right now. Please try again in a moment.

Or contact our sales team directly:
- Gurgaon: {SALES_PHONE_GURGAON}
- Noida: {SALES_PHONE_NOIDA}
"""

    gurgaon_km = distances["gurgaon_km"]
    noida_km = distances["noida_km"]
    gurgaon_max = distances["gurgaon_max_km"]
    noida_max = distances["noida_max_km"]

    gurgaon_ok = gurgaon_km <= gurgaon_max
    noida_ok = noida_km <= noida_max

    # Build distance info lines
    parts = []
    g_status = "Serviceable" if gurgaon_ok else "Not Serviceable"
    n_status = "Serviceable" if noida_ok else "Not Serviceable"
    parts.append(f"Approximately {gurgaon_km:.1f} km from the Gurugram Office -- {g_status}")
    parts.append(f"Approximately {noida_km:.1f} km from the Noida Office -- {n_status}")
    distance_info = "\n".join(parts)

    if gurgaon_ok or noida_ok:
        # Pick the closer serviceable office
        if gurgaon_ok and noida_ok:
            office = "Gurugram" if gurgaon_km <= noida_km else "Noida"
        elif gurgaon_ok:
            office = "Gurugram"
        else:
            office = "Noida"

        return f"""SERVICEABLE
Pincode {pincode} ({city}) is serviceable.

{distance_info}

Delivery from our *{office} Office*. Standard delivery: 2-5 business days."""

    # Not serviceable
    return f"""NOT_SERVICEABLE
Sorry, pincode {pincode} ({city}) is outside our delivery range.

{distance_info}

We serve Gurgaon and Noida within {gurgaon_max:.0f} km of our offices. Contact us for special requests: Gurgaon {SALES_PHONE_GURGAON} | Noida {SALES_PHONE_NOIDA}"""


@tool
def get_service_areas_tool() -> str:
    """
    Get list of all serviceable areas.
    Use this when customer asks about service areas or delivery locations.

    Returns:
        List of serviceable cities and areas
    """
    return f"""
*RentBasket Service Areas:*

*Gurgaon (Gurugram)*
- All main sectors covered
- Excluding: Manesar industrial area

*Noida*
- All sectors covered
- Greater Noida: Limited areas

*Not Covered Currently:*
- Delhi NCR (all areas)
- Faridabad
- Ghaziabad (most areas)

*Contact for special requests:*
- Gurgaon: {SALES_PHONE_GURGAON}
- Noida: {SALES_PHONE_NOIDA}

Share your pincode and I'll confirm exact availability!
"""
