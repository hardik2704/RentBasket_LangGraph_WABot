#!/usr/bin/env python3
"""
RentBasket WhatsApp Bot "Ku" - Webhook Server
Flask server for handling real WhatsApp Business API integration

Usage:
    python3 webhook_server.py                    # Run on default port 8000
    python webhook_server.py --port 8000        # Run on custom port
    ngrok http 8000                             # Expose locally (separate terminal)
"""

import os
import sys
import re
import io
import tempfile
import argparse
import threading
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
import json
from urllib.parse import quote

# Ensure parent packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import BOT_NAME, SALES_PHONE_GURGAON, SALES_PHONE_NOIDA, KU_REFERRAL_LINK, RENTBASKET_JWT
from tools.location_tools import _extract_pincode, _identify_city_from_pincode, _call_distance_api
from agents.orchestrator import route_and_run
from agents.state import create_initial_state
from whatsapp.client import WhatsAppClient
from utils.phone_utils import normalize_phone
from utils.session_cache import SessionCache, update_user_facts
from utils.logger import log_conversation_turn as file_log_turn, start_new_session as file_start_session
from utils.db_logger import (
    log_conversation_turn,
    start_new_session,
    get_or_create_session,
    update_session,
    log_event,
)
from utils.firebase_client import upsert_lead, get_lead


def restore_lead_to_state(normalized_phone: str, state: dict) -> dict:
    """
    Load persisted lead data from Firestore into the in-memory conversation state.
    Called when a new conversation is created (server restart or re-greeting)
    so the bot remembers duration, name, location, etc.
    """
    try:
        lead = get_lead(normalized_phone)
        if not lead:
            return state

        collected = state.get("collected_info", {})

        # Restore duration (critical -- prevents re-asking)
        if lead.get("duration_months") and not collected.get("duration_months"):
            collected["duration_months"] = lead["duration_months"]

        # Restore customer name
        name = lead.get("extracted_name") or lead.get("name") or lead.get("push_name")
        if name and not collected.get("customer_name"):
            collected["customer_name"] = name

        # Restore delivery location
        loc = lead.get("delivery_location") or {}
        if loc.get("pincode") and not collected.get("pincode"):
            collected["pincode"] = loc["pincode"]
        if loc.get("city") and not collected.get("city"):
            collected["city"] = loc["city"]

        # Restore phone
        collected["phone"] = normalized_phone

        state["collected_info"] = collected
        print(f"   Restored lead data for {normalized_phone}: duration={collected.get('duration_months')}, name={collected.get('customer_name')}")
    except Exception as e:
        print(f"   Warning: Failed to restore lead data for {normalized_phone}: {e}")

    return state


# ========================================
# CONFIGURATION
# ========================================

# WhatsApp API credentials from .env
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "12345")
VERSION = os.getenv("VERSION", "v23.0")

# Validate credentials (warn instead of exit – Render injects env vars at runtime)
if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
    print("⚠️ Warning: Missing WhatsApp credentials (PHONE_NUMBER_ID, ACCESS_TOKEN)")
    print("   Set them as environment variables or in a .env file")

# ========================================
# PRICING NEGOTIATION DETECTION
# ========================================

# Keywords that trigger pricing negotiation escalation
PRICING_NEGOTIATION_KEYWORDS = [
    "costly", "expensive", "discount", "cheaper", "go down", 
    "best price", "offer", "reduce", "negotiate", "too much",
    "high price", "lower", "budget", "afford", "deal"
]

def is_pricing_negotiation(text: str) -> bool:
    """Check if message indicates pricing negotiation intent.

    Excludes:
    - Messages containing URLs (user pasting links)
    - Messages that mention duration/tenure (user asking about longer rental periods)
    - Very short messages (single words that happen to match)
    """
    text_lower = text.lower().strip()

    # Skip URLs — user pasting a link should never trigger pricing negotiation
    if "http" in text_lower or "://" in text_lower or "rentbasket.com" in text_lower:
        return False

    # Skip if the message is about duration/tenure — legitimate pricing question, not a complaint
    duration_indicators = [
        r"\d+\s*(?:months?|mo\b)",
        r"\b(?:longer|shorter)\s+(?:tenure|duration|term|period)",
        r"\b(?:how\s+(?:much|long)|what\s+if|will\s+there\s+be)",
        r"\b(?:for\s+\d+|rent\s+for)",
    ]
    for pat in duration_indicators:
        if re.search(pat, text_lower):
            return False

    # Require at least one pricing keyword
    return any(keyword in text_lower for keyword in PRICING_NEGOTIATION_KEYWORDS)

# ========================================
# INTERACTIVE BUTTONS & DYNAMIC EXAMPLES
# ========================================

GREETING_BUTTONS = [
    {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
    {"id": "HOW_RENTING_WORKS", "title": "How Renting Works?"},
]

# ========================================
# INFORMATIONAL FLOW TEXTS
# ========================================

HOW_RENTING_WORKS_TEXT = (
    "Let's get you settled! Here is your 4-step journey with RentBasket: \u26a1\n\n"
    "1\ufe0f\u20e3 Select & Onboard (3 mins) \U0001f4f1\n"
    "Pick your items on our app and finish onboarding in minutes. It's that fast!\n\n"
    "2\ufe0f\u20e3 Secure & Relax \U0001f6e1\ufe0f\n"
    "Pay a one-time refundable deposit. We're proud to say 95% of our customers get their full deposit back!\n\n"
    "3\ufe0f\u20e3 Free Setup (72 hrs) \U0001f69a\n"
    "We deliver and install everything for FREE within 72 hours. No need to hunt for help; we handle it all.\n\n"
    "4\ufe0f\u20e3 Enjoy & Live \U0001f4b3\n"
    "Pay low monthly rent and leave the maintenance to us. If you move, we'll relocate your items for zero extra cost! \U0001f3e0\n\n"
    "Ready to upgrade your space?"
)

WHY_RENTBASKET_TEXT = (
    "Why RentBasket Specifically? \u2b50\n\n"
    "We're not just a rental service - we're your furniture partners:\n\n"
    "\U0001f31f 4.9 Google Star Rating\n"
    "Check out real reviews from our happy customers!\n\n"
    "\U0001f3af Hyper-Localization\n"
    "We know your city better than anyone, so we get you the best people and fastest service\n\n"
    "\U0001f512 95% Full Security Refund\n"
    "We're blessed with customers who treat our products beautifully\n\n"
    "\U0001f49a Customer-First Approach\n"
    "Our reviews speak louder than words"
)

LATEST_REVIEWS_TEXT = (
    "Check out our Customer Reviews: https://rentbasket.short.gy/reviews\n\n"
    "Latest 5 Customer Experiences with RentBasket\n\n"
    "Prateek Jain \u2b50\u2b50\u2b50\u2b50\u2b50\n"
    "23 hours ago\n\n"
    "\"Got a fresh new mattress on urgent basis. Ordered at 8 PM and it was delivered by "
    "10 PM. Very quick and authentic service!\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Sejal Sangole \u2b50\u2b50\u2b50\u2b50\u2b50\n"
    "6 days ago\n\n"
    "\"Great experience with RentBasket. Smooth process and reliable service.\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Shivam Sood \u2b50\u2b50\u2b50\u2b50\u2b50\n"
    "3 weeks ago\n\n"
    "\"Very prompt service and delivery along with installation. Truly hassle-free.\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Harmeet Kaur \u2b50\u2b50\u2b50\u2b50\u2b50\n"
    "3 weeks ago\n\n"
    "\"Very good experience, fast delivery, and good quality products.\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Justin Shibu \u2b50\u2b50\u2b50\u2b50\u2b50\n"
    "4 weeks ago\n\n"
    "\"Great and quick fridge service. Highly satisfied.\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Comfort On Rent, Happiness Delivered.\n"
    "RentBasket \u2014 Furnishing Homes, Effortlessly."
)

# ========================================
# BROWSE PRODUCTS FLOW
# ========================================

BROWSE_PRODUCTS_OCCASION = os.getenv("BROWSE_PRODUCTS_OCCASION", "heavy discount offers")
BROWSE_PRODUCTS_REFERRAL_CODE = os.getenv("BROWSE_PRODUCTS_REFERRAL_CODE", "ATFU1NTg1")
BROWSE_PRODUCTS_BASE_URL = os.getenv(
    "BROWSE_PRODUCTS_BASE_URL",
    "https://testqr.rentbasket.com/lead-shopping",
)

BROWSE_FLOW_HEADER = "Browse Products"

# ── Room-based browse hierarchy ──────────────────────────────────
# Room → Subcategory → Variants  (product_id, display_name)
# Prices are looked up dynamically via calculate_rent(pid, duration).

ROOM_CATEGORIES = {
    "ROOM_BEDROOM": {
        "title": "Bedroom",
        "description": "Beds, mattresses, storage",
        "subcategories": {
            "SUBCAT_BED_TYPE": {
                "title": "Bed Type",
                "variants": [
                    (28,   "Single Bed 6x3"),
                    (17,   "Double Bed King"),
                    (1017, "Double Bed Queen"),
                    (1023, "King Storage Bed"),
                    (1005, "King Storage Premium"),
                    (1027, "Queen Storage Bed"),
                    (1031, "Single Upholstered"),
                ],
            },
            "SUBCAT_MATTRESS": {
                "title": "Mattress",
                "variants": [
                    (1057, "Single 4 Inch"),
                    (21,   "4 Inch Pair"),
                    (44,   "5 Inch Pair"),
                    (1019, "6 Inch Pair (King)"),
                    (1018, "QS Pair 6x5"),
                    (1050, "QS One Piece 6 Inch"),
                    (1051, "QS One Piece 5 Inch"),
                ],
            },
            "SUBCAT_BEDROOM_STORAGE": {
                "title": "Storage",
                "variants": [
                    (42,   "Book Shelf"),
                    (1044, "Dressing Table"),
                ],
            },
            "SUBCAT_BEDROOM_ADDONS": {
                "title": "Add-ons",
                "variants": [
                    (51,   "Side Table Glass Top"),
                    (1055, "Side Table"),
                ],
            },
        },
    },
    "ROOM_LIVING": {
        "title": "Living Room",
        "description": "Sofas, TVs, tables, AC",
        "subcategories": {
            "SUBCAT_SOFA": {
                "title": "Sofa",
                "variants": [
                    (1043, "2 Seater Sofa"),
                    (1042, "3 Seater Sofa"),
                    (1020, "4 Seater Canwood"),
                    (18,   "5 Seater with CT"),
                    (1039, "3+1+1 Fabric Sofa"),
                    (1041, "7 Seater Green Set"),
                    (1048, "7 Seater Grey Set"),
                    (1047, "Sofa Chair"),
                ],
            },
            "SUBCAT_TABLES": {
                "title": "Tables",
                "variants": [
                    (29,   "Center Table"),
                    (53,   "Coffee Table"),
                    (51,   "Side Table Glass Top"),
                    (1033, "6 Seater Dining"),
                    (1034, "4 Seater Dining"),
                ],
            },
            "SUBCAT_ELECTRONICS": {
                "title": "TV / Electronics",
                "variants": [
                    (12,   "Smart LED 32 inch"),
                    (50,   "Smart LED 40 inch"),
                    (1008, "Smart LED 43 inch"),
                    (1011, "Smart LED 48 inch"),
                ],
            },
            "SUBCAT_COOLING": {
                "title": "Cooling",
                "variants": [
                    (14,  "Window AC"),
                    (60,  "Split AC 1.5 Ton"),
                ],
            },
            "SUBCAT_POWER": {
                "title": "Power Backup",
                "variants": [
                    (24,  "Inverter Single Batt"),
                    (45,  "Inverter Double Batt"),
                    (56,  "Inverter Battery"),
                ],
            },
        },
    },
    "ROOM_KITCHEN": {
        "title": "Kitchen",
        "description": "Fridge, washing, cooking",
        "subcategories": {
            "SUBCAT_FRIDGE": {
                "title": "Refrigerator",
                "variants": [
                    (11, "Fridge 190 Ltr"),
                    (36, "Double Door Fridge"),
                ],
            },
            "SUBCAT_WASHING": {
                "title": "Washing Machine",
                "variants": [
                    (13, "Fully Automatic WM"),
                    (37, "Semi Automatic WM"),
                ],
            },
            "SUBCAT_COOKING": {
                "title": "Cooking",
                "variants": [
                    (16,   "Microwave 20Ltr"),
                    (34,   "Gas Stove 2 Burner"),
                    (49,   "Gas Stove 3 Burner"),
                    (1015, "Chimney"),
                ],
            },
            "SUBCAT_WATER": {
                "title": "Water Purifier",
                "variants": [
                    (15,   "Water Purifier"),
                    (1046, "Water Purifier UTC"),
                ],
            },
        },
    },
    "ROOM_WORKSTATION": {
        "title": "Work Station",
        "description": "Desk, chair, shelf",
        "subcategories": {
            "SUBCAT_WS_TABLES": {
                "title": "Tables",
                "variants": [
                    (40, "Study Table"),
                ],
            },
            "SUBCAT_WS_CHAIRS": {
                "title": "Chairs",
                "variants": [
                    (41,   "Study Chair Premium"),
                    (1058, "Study Chair"),
                    (1047, "Sofa Chair"),
                ],
            },
            "SUBCAT_WS_STORAGE": {
                "title": "Storage",
                "variants": [
                    (42, "Book Shelf"),
                ],
            },
        },
    },
}

# Pre-built 1BHK packages  (product IDs auto-added to cart)
COMPLETE_1BHK_PACKAGES = {
    "PKG_BASIC": {
        "title": "Basic 1BHK",
        "description": "Single Bed, Mattress, Fridge, WM, Study Table, Chair",
        "items": [28, 21, 11, 37, 40, 1058],
    },
    "PKG_COMFORT": {
        "title": "Comfort 1BHK",
        "description": "Double Bed, Mattress, LED TV, Sofa, Fridge",
        "items": [17, 44, 12, 1043, 11],
    },
    "PKG_LUXURY": {
        "title": "Luxury 1BHK",
        "description": "King Bed, 6in Mattress, LED 43, 5-Seater Sofa, DD Fridge, WM, AC",
        "items": [1005, 1019, 1008, 18, 36, 13, 60],
    },
}

# Room selection list sections (sent as WhatsApp list message)
ROOM_SELECTION_SECTIONS = [
    {
        "title": "Select a Room",
        "rows": [
            {"id": "ROOM_BEDROOM",     "title": "Bedroom",        "description": "Beds, mattresses, storage"},
            {"id": "ROOM_LIVING",      "title": "Living Room",    "description": "Sofas, TVs, tables, AC"},
            {"id": "ROOM_KITCHEN",     "title": "Kitchen",        "description": "Fridge, washing, cooking"},
            {"id": "ROOM_WORKSTATION", "title": "Work Station",   "description": "Desk, chair, shelf"},
            {"id": "ROOM_1BHK",       "title": "Complete 1BHK",  "description": "Ready-to-move packages"},
        ],
    }
]

# Fuzzy lookup: user-typed text → room ID
ROOM_TEXT_MATCH = {
    "bedroom": "ROOM_BEDROOM", "bed room": "ROOM_BEDROOM", "bed": "ROOM_BEDROOM",
    "living": "ROOM_LIVING", "living room": "ROOM_LIVING", "hall": "ROOM_LIVING",
    "kitchen": "ROOM_KITCHEN", "cooking": "ROOM_KITCHEN",
    "work": "ROOM_WORKSTATION", "workstation": "ROOM_WORKSTATION", "work station": "ROOM_WORKSTATION",
    "office": "ROOM_WORKSTATION", "study": "ROOM_WORKSTATION", "wfh": "ROOM_WORKSTATION",
    "1bhk": "ROOM_1BHK", "1 bhk": "ROOM_1BHK", "complete": "ROOM_1BHK", "package": "ROOM_1BHK",
    "combo": "ROOM_1BHK", "full house": "ROOM_1BHK",
}


def _browse_context(phone: str) -> dict:
    ctx = session_context.get(phone)
    if ctx is None:
        ctx = {}
        session_context[phone] = ctx
    return ctx


def _set_browse_context(phone: str, **updates) -> dict:
    ctx = _browse_context(phone)
    ctx.update(updates)
    ctx.setdefault("browse_mode", True)
    return ctx


def _clear_browse_context(phone: str) -> None:
    ctx = session_context.get(phone, {})
    for key in ("browse_mode", "browse_step", "browse_duration", "browse_requested_items",
                "last_browse_quote", "last_browse_category",
                "browse_room", "browse_subcategory", "browse_variant_list",
                "browse_checkout_location",
                "direct_request", "direct_segments", "direct_option_list",
                "browse_modify_mode"):
        ctx.pop(key, None)
    session_context[phone] = ctx


def _parse_duration_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    cleaned = text.strip().lower()
    match = re.search(r"\b(\d{1,2})\b", cleaned)
    if match:
        value = int(match.group(1))
        if 1 <= value <= 36:
            return value
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20, "twenty one": 21, "twenty two": 22,
        "twenty three": 23, "twenty four": 24, "thirty": 30, "thirty six": 36,
    }
    for word, value in word_map.items():
        if re.search(rf"\b{re.escape(word)}\b", cleaned):
            return value
    return None


def _save_browse_lead_data(normalized_phone: str, payload: dict) -> None:
    try:
        upsert_lead(normalized_phone, payload)
    except Exception as e:
        print(f"   Warning: failed to save browse lead data for {normalized_phone}: {e}")


def _send_duration_buttons(phone: str) -> None:
    """Show 3/6/12 month duration buttons."""
    _set_browse_context(phone, browse_mode=True, browse_step="await_duration")
    buttons = [
        {"id": "BROWSE_DUR_3", "title": "3 Months"},
        {"id": "BROWSE_DUR_6", "title": "6 Months"},
        {"id": "BROWSE_DUR_12", "title": "12 Months"},
    ]
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text="First let me know the expected duration of rental (you can always extend the duration):",
        buttons=buttons,
        header=BROWSE_FLOW_HEADER,
    )


def _handle_checkout_location(phone: str, text: str, sender_name: str) -> bool:
    """Extract pincode from user message, check serviceability, send cart link or rejection."""
    ctx = _browse_context(phone)
    quote = ctx.get("last_browse_quote", {})
    cart_link = quote.get("cart_link")
    normalized_phone = normalize_phone(phone)

    pincode = _extract_pincode(text)
    if not pincode:
        whatsapp_client.send_text_message(
            phone,
            "I could not find a 6-digit pincode in your message. Please share your delivery pincode (e.g. 122001, 201301).",
            preview_url=False,
        )
        return True

    city = _identify_city_from_pincode(pincode)
    distances = _call_distance_api(pincode)

    if distances is None:
        whatsapp_client.send_text_message(
            phone,
            f"Could not verify serviceability for pincode {pincode} right now. Please try again or contact our sales team:\n"
            f"Gurgaon: {SALES_PHONE_GURGAON}\nNoida: {SALES_PHONE_NOIDA}",
            preview_url=False,
        )
        return True

    gurgaon_km = distances["gurgaon_km"]
    noida_km = distances["noida_km"]
    gurgaon_ok = gurgaon_km <= distances["gurgaon_max_km"]
    noida_ok = noida_km <= distances["noida_max_km"]

    _save_browse_lead_data(normalized_phone, {
        "delivery_pincode": pincode,
        "delivery_city": city,
        "distance_gurgaon_km": gurgaon_km,
        "distance_noida_km": noida_km,
        "serviceable": gurgaon_ok or noida_ok,
        "lead_stage": "checkout_serviceability_checked",
    })

    if gurgaon_ok or noida_ok:
        if gurgaon_ok and noida_ok:
            office = "Gurugram" if gurgaon_km <= noida_km else "Noida"
            dist = min(gurgaon_km, noida_km)
        elif gurgaon_ok:
            office = "Gurugram"
            dist = gurgaon_km
        else:
            office = "Noida"
            dist = noida_km

        if not cart_link:
            items = quote.get("items", [])
            duration = int(quote.get("duration") or 12)
            if items:
                cart_link = _build_browse_cart_link(items, duration)

        _save_browse_lead_data(normalized_phone, {"lead_stage": "checkout_link_sent"})

        whatsapp_client.send_text_message(
            phone,
            f"Pincode {pincode} ({city}) is serviceable.\n"
            f"Delivery from our *{office} Office* — approximately {dist:.1f} km away.\n"
            f"Standard delivery: 2-5 business days.\n\n"
            f"Get an *additional 2% discount* by completing your order through this link:",
            preview_url=False,
        )
        time.sleep(0.3)
        # Send cart link as a separate message so WhatsApp renders the preview
        whatsapp_client.send_text_message(phone, cart_link, preview_url=True)
        # Clear checkout step, keep browse mode for further browsing
        ctx["browse_step"] = "quote_ready"
    else:
        closer_km = min(gurgaon_km, noida_km)
        closer_office = "Gurugram" if gurgaon_km <= noida_km else "Noida"
        whatsapp_client.send_text_message(
            phone,
            f"Sorry, pincode {pincode} ({city}) is outside our delivery range.\n\n"
            f"Nearest office: *{closer_office}* — approximately {closer_km:.1f} km away.\n"
            f"We currently serve within 20 km of our Gurgaon and Noida offices.\n\n"
            f"For special arrangements, contact:\n"
            f"Gurgaon: {SALES_PHONE_GURGAON}\nNoida: {SALES_PHONE_NOIDA}",
            preview_url=False,
        )
        # Let them modify or browse more
        time.sleep(0.3)
        buttons = [
            {"id": "BROWSE_MODIFY_CART", "title": "Modify Cart"},
            {"id": "BROWSE_PRODUCTS", "title": "Browse More"},
        ]
        whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text="Would you like to do anything else?",
            buttons=buttons,
            header="Not Serviceable",
        )
        ctx["browse_step"] = "quote_ready"

    return True


def _send_room_selection(phone: str) -> None:
    """Send the room-category list (Bedroom, Living Room, Kitchen, Work Station, 1BHK)."""
    ctx = _set_browse_context(phone, browse_step="await_room")
    try:
        whatsapp_client.send_list_message(
            to_phone=phone,
            body_text="Pick a room and I will show you exactly what we have.",
            button_text="Select Room",
            sections=ROOM_SELECTION_SECTIONS,
            header=BROWSE_FLOW_HEADER,
        )
    except Exception as e:
        print(f"   Warning: room list failed for {phone}: {e}")
        whatsapp_client.send_text_message(
            phone,
            "*Select a room:*\n1. Bedroom\n2. Living Room\n3. Kitchen\n4. Work Station\n5. Complete 1BHK\n\nReply with the room name.",
            preview_url=False,
        )


def _send_subcategory_selection(phone: str, room_id: str) -> None:
    """Send subcategories for a room (as buttons if <=3, list if >3)."""
    room = ROOM_CATEGORIES.get(room_id, {})
    room_title = room.get("title", "Room")
    subcats = room.get("subcategories", {})
    ctx = _set_browse_context(phone, browse_step="await_subcategory", browse_room=room_id)

    # Log room selection
    _save_browse_lead_data(normalize_phone(phone), {
        "last_browsed_room": room_title,
        "lead_stage": "browse_room_selected",
    })

    items_list = list(subcats.items())
    if len(items_list) <= 3:
        # Use interactive buttons
        buttons = [{"id": sc_id, "title": sc["title"][:20]} for sc_id, sc in items_list]
        whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text=f"*{room_title}* — what are you looking for?",
            buttons=buttons,
            header=BROWSE_FLOW_HEADER,
        )
    else:
        # Use list message
        rows = [{"id": sc_id, "title": sc["title"][:24]} for sc_id, sc in items_list]
        sections = [{"title": room_title, "rows": rows}]
        try:
            whatsapp_client.send_list_message(
                to_phone=phone,
                body_text=f"*{room_title}* — pick a category below.",
                button_text="Select Category",
                sections=sections,
                header=BROWSE_FLOW_HEADER,
            )
        except Exception as e:
            print(f"   Warning: subcategory list failed for {phone}: {e}")
            lines = [f"*{room_title} categories:*"]
            for idx, (_, sc) in enumerate(items_list, 1):
                lines.append(f"{idx}. {sc['title']}")
            lines.append("\nReply with the category name.")
            whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=False)


def _send_1bhk_package_buttons(phone: str) -> None:
    """Show the three 1BHK packages as interactive buttons (exactly 3)."""
    ctx = _set_browse_context(phone, browse_step="await_subcategory", browse_room="ROOM_1BHK")
    buttons = [
        {"id": pkg_id, "title": pkg["title"][:20]}
        for pkg_id, pkg in COMPLETE_1BHK_PACKAGES.items()
    ]
    body_lines = ["*Complete 1BHK Packages*", ""]
    for pkg_id, pkg in COMPLETE_1BHK_PACKAGES.items():
        body_lines.append(f"*{pkg['title']}*: {pkg['description']}")
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text="\n".join(body_lines),
        buttons=buttons,
        header=BROWSE_FLOW_HEADER,
    )


def _send_variant_list(phone: str, room_id: str, subcat_id: str) -> None:
    """Show product variants for a subcategory as a text message with starting prices."""
    room = ROOM_CATEGORIES.get(room_id, {})
    room_title = room.get("title", "Room")
    subcat = room.get("subcategories", {}).get(subcat_id, {})
    subcat_title = subcat.get("title", "Category")
    variants = subcat.get("variants", [])

    ctx = _set_browse_context(phone, browse_step="await_variant_action",
                              browse_subcategory=subcat_id)
    duration = int(ctx.get("browse_duration") or 12)

    # Log subcategory selection
    _save_browse_lead_data(normalize_phone(phone), {
        "last_browsed_subcategory": f"{room_title} > {subcat_title}",
        "lead_stage": "browse_subcategory_selected",
    })

    # Store variant list for number-based selection
    ctx["browse_variant_list"] = variants

    # Build text with starting prices
    lines = [f"*{subcat_title} — {room_title}*", f"Duration: {duration} months", ""]
    for idx, (pid, name) in enumerate(variants, 1):
        price = calculate_rent(pid, duration) or 0
        discounted = int(round(price * 0.70)) if price else 0
        if discounted:
            lines.append(f"{idx}. {name} — from Rs. {discounted:,}/mo")
        else:
            lines.append(f"{idx}. {name}")

    lines.append("")
    lines.append("Reply with the item number or name to add to cart.")

    whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=False)
    time.sleep(0.3)

    # Navigation buttons
    has_cart = bool(ctx.get("last_browse_quote", {}).get("items"))
    buttons = [
        {"id": "BROWSE_BACK_ROOM", "title": "Back to Rooms"},
    ]
    # Add back-to-subcategories if room has >1 subcategory
    if len(room.get("subcategories", {})) > 1:
        buttons.append({"id": "BROWSE_BACK_SUBCAT", "title": f"Back to {room_title[:14]}"})
    if has_cart:
        buttons.append({"id": "BROWSE_SHOW_DETAILS", "title": "View Cart"})

    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text="Or navigate:",
        buttons=buttons[:3],  # WhatsApp max 3 buttons
        header=BROWSE_FLOW_HEADER,
    )


def _handle_1bhk_package_selection(phone: str, package_id: str, sender_name: str) -> None:
    """Auto-add all items from a 1BHK package to the browse cart and show quote."""
    pkg = COMPLETE_1BHK_PACKAGES.get(package_id)
    if not pkg:
        whatsapp_client.send_text_message(phone, "Could not find that package. Please try again.")
        return

    ctx = _browse_context(phone)
    duration = int(ctx.get("browse_duration") or 12)
    normalized_phone = normalize_phone(phone)

    items = []
    for pid in pkg["items"]:
        product = get_product_by_id(pid)
        if not product:
            continue
        mrp = calculate_rent(pid, duration) or 0
        discounted = int(round(mrp * 0.70)) if mrp else 0
        items.append({
            "product_id": pid,
            "product_name": product.get("name", "Product"),
            "name": product.get("name", "Product"),
            "qty": 1,
            "original_rent": mrp,
            "rent": discounted,
            "duration": duration,
            "matched": True,
        })

    _save_browse_lead_data(normalized_phone, {
        "package_selected": pkg["title"],
        "lead_stage": "browse_package_selected",
    })

    whatsapp_client.send_text_message(
        phone,
        f"*{pkg['title']}* package selected.\n{pkg['description']}\n\nPreparing your quote...",
        preview_url=False,
    )
    time.sleep(0.3)

    _send_browse_quote(phone, sender_name, pkg["title"], items, duration)


def _handle_variant_text_selection(phone: str, text: str, sender_name: str) -> bool:
    """Match user text (number or name) against displayed variant list, add to cart."""
    ctx = _browse_context(phone)
    variants = ctx.get("browse_variant_list", [])
    if not variants:
        return False

    # Strip trailing punctuation (user may type "1." or "2)")
    cleaned = re.sub(r"[.\)\]\,;:!]+$", "", text.strip()).strip()

    # Try number match first
    try:
        idx = int(cleaned)
        if 1 <= idx <= len(variants):
            pid, _ = variants[idx - 1]
            return _handle_browse_item_selection(phone, sender_name, pid)
    except ValueError:
        pass

    # Try fuzzy name match
    lower = cleaned.lower()
    for pid, name in variants:
        if lower in name.lower() or name.lower() in lower:
            return _handle_browse_item_selection(phone, sender_name, pid)

    # If no match in variant list, try the full product search pipeline
    return False


def _handle_browse_item_selection(phone: str, sender_name: str, product_id: int) -> bool:
    """Handle user tapping a product variant from the list. Adds to browse cart and shows updated quote."""
    ctx = _browse_context(phone)
    duration = int(ctx.get("browse_duration") or 12)
    normalized_phone = normalize_phone(phone)

    product = get_product_by_id(product_id)
    if not product:
        whatsapp_client.send_text_message(phone, "Could not find that product. Please try again.")
        return True

    mrp = calculate_rent(product_id, duration) or 0
    discounted = int(round(mrp * 0.70)) if mrp else 0
    product_name = product.get("name", "Product")

    new_item = {
        "product_id": product_id,
        "product_name": product_name,
        "name": product_name,
        "qty": 1,
        "original_rent": mrp,
        "rent": discounted,
        "duration": duration,
        "matched": True,
    }

    # Merge with existing browse cart
    existing_quote = ctx.get("last_browse_quote", {})
    existing_items = list(existing_quote.get("items", []))
    existing_ids = {it.get("product_id") for it in existing_items if it.get("product_id")}

    if product_id in existing_ids:
        for ex in existing_items:
            if ex.get("product_id") == product_id:
                ex["qty"] = ex.get("qty", 1) + 1
                break
        added_msg = f"Added one more *{product_name}* to your cart."
    else:
        existing_items.append(new_item)
        added_msg = f"*{product_name}* added to your cart."

    # Log product interest to database
    _save_browse_lead_data(normalized_phone, {
        "last_item_added": product_name,
        "lead_stage": "browse_item_selected",
    })

    # Per-item pricing confirmation
    pricing_lines = [
        added_msg,
        "",
        f"*{product_name}* | {duration} months",
        f"MRP: Rs. {mrp:,}/mo",
        f"After 30% discount: Rs. {discounted:,}/mo",
    ]
    if duration >= 12 and discounted:
        upfront_price = int(round(discounted * 0.90))
        upfront_save = (mrp - upfront_price) * duration
        pricing_lines.append(f"Pay upfront: Rs. {upfront_price:,}/mo (extra 10% off, save Rs. {upfront_save:,} total)")

    whatsapp_client.send_text_message(phone, "\n".join(pricing_lines), preview_url=False)
    time.sleep(0.4)

    # Send the full updated quote with checkout option
    _send_browse_quote(phone, sender_name, product_name, existing_items, duration)
    return True


# ── Direct Product Request Flow ──────────────────────────────────────
# When user sends a free-text message like "Study Chair and table I want"
# we detect the product intent, show matching variants with pricing,
# and let them pick — skipping the full room-based browse hierarchy.

def _try_direct_product_request(phone: str, sender_name: str, text: str) -> bool:
    """
    Detect if the user's free text contains product keywords.
    If so, start a direct-request flow (skip browse hierarchy).
    Returns True if we intercepted the message, False otherwise.
    """
    ctx = session_context.get(phone, {})
    if ctx.get("browse_mode") or ctx.get("sales_mode"):
        return False

    # Split text into segments and search for product matches
    text_wo_duration = remove_duration_phrases(text)
    segments = split_into_segments(text_wo_duration)
    if not segments:
        return False

    all_matches = []
    for seg in segments:
        seg = clean_item_segment(seg)
        if not seg:
            continue
        qty, item_text = extract_qty_and_item(seg)
        item_text = re.sub(r"\b(for|months?|mo)\b.*$", "", item_text).strip()
        if not item_text or len(item_text) < 2:
            continue
        matches = search_products_by_name(item_text)
        if matches:
            all_matches.append({
                "query": item_text,
                "qty": qty,
                "matches": matches,
            })

    if not all_matches:
        return False

    # Activate direct request flow
    duration_from_text = extract_duration(text, None)

    session_context[phone] = session_context.get(phone, {})
    session_context[phone]["browse_mode"] = True
    session_context[phone]["direct_request"] = True
    session_context[phone]["direct_segments"] = all_matches
    session_context[phone]["sender_name"] = sender_name

    if duration_from_text:
        session_context[phone]["browse_duration"] = duration_from_text
        session_context[phone]["browse_step"] = "direct_await_selection"
        _send_direct_request_options(phone)
    else:
        session_context[phone]["browse_step"] = "direct_await_duration"
        # Acknowledge the request, then ask duration
        segment_names = [seg["query"].title() for seg in all_matches]
        whatsapp_client.send_text_message(
            phone,
            f"I found options for: {', '.join(segment_names)}.\nLet me show you the best options with pricing.",
            preview_url=False,
        )
        time.sleep(0.3)
        _send_duration_buttons(phone)

    return True


def _send_direct_request_options(phone: str) -> None:
    """Show product options for each segment in the direct request, with pricing."""
    ctx = session_context.get(phone, {})
    segments = ctx.get("direct_segments", [])
    duration = int(ctx.get("browse_duration") or 12)

    lines = [f"*Available Options* ({duration} months rental)", ""]

    option_list = []  # flat list of (product_id, product_name) for number selection

    for seg in segments:
        query_title = seg["query"].title()
        matches = seg["matches"]

        if len(matches) == 1:
            p = matches[0]
            mrp = calculate_rent(p["id"], duration) or 0
            disc = int(round(mrp * 0.70)) if mrp else 0
            idx = len(option_list) + 1
            option_list.append((p["id"], p["name"]))
            lines.append(f"{idx}. {p['name']} -- ~Rs. {mrp:,}~ Rs. {disc:,}/mo +GST")
        else:
            lines.append(f"*{query_title}:*")
            for p in matches:
                mrp = calculate_rent(p["id"], duration) or 0
                disc = int(round(mrp * 0.70)) if mrp else 0
                idx = len(option_list) + 1
                option_list.append((p["id"], p["name"]))
                lines.append(f"{idx}. {p['name']} -- ~Rs. {mrp:,}~ Rs. {disc:,}/mo +GST")
            lines.append("")

    lines.append("")
    lines.append("Reply with the numbers you want to add to cart.")
    lines.append("Example: 1, 3  or  1 and 3")

    ctx["direct_option_list"] = option_list
    ctx["browse_step"] = "direct_await_selection"

    whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=False)


def _handle_direct_selection(phone: str, text: str, sender_name: str) -> bool:
    """
    Parse the user's number selections (e.g. '1, 3' or '1 and 3') from the
    direct-request options list.  Build cart items and send quote.
    """
    ctx = _browse_context(phone)
    option_list = ctx.get("direct_option_list", [])
    duration = int(ctx.get("browse_duration") or 12)

    if not option_list:
        return False

    cleaned = text.strip()
    # Extract numbers from text like "1, 3", "1 and 3", "1 3", "1,3"
    numbers = re.findall(r"\d+", cleaned)
    selected_ids = set()
    for n in numbers:
        idx = int(n)
        if 1 <= idx <= len(option_list):
            selected_ids.add(idx)

    if not selected_ids:
        # Maybe user typed a product name instead of numbers
        lower = cleaned.lower()
        for i, (pid, pname) in enumerate(option_list, 1):
            if lower in pname.lower() or pname.lower() in lower:
                selected_ids.add(i)

    if not selected_ids:
        whatsapp_client.send_text_message(
            phone,
            f"Could not match your selection. Reply with item numbers (1-{len(option_list)}) from the list above.",
            preview_url=False,
        )
        return True

    # Build cart items from selection
    items = []
    for idx in sorted(selected_ids):
        pid, pname = option_list[idx - 1]
        product = get_product_by_id(pid)
        if not product:
            continue
        mrp = calculate_rent(pid, duration) or 0
        discounted = int(round(mrp * 0.70)) if mrp else 0
        items.append({
            "product_id": pid,
            "product_name": product.get("name", pname),
            "name": product.get("name", pname),
            "qty": 1,
            "original_rent": mrp,
            "rent": discounted,
            "duration": duration,
            "matched": True,
        })

    if not items:
        whatsapp_client.send_text_message(phone, "Could not find those products. Please try again.", preview_url=False)
        return True

    # Merge with any existing browse cart
    existing_quote = ctx.get("last_browse_quote", {})
    existing_items = list(existing_quote.get("items", []))
    existing_pids = {it.get("product_id") for it in existing_items if it.get("product_id")}
    for item in items:
        if item["product_id"] in existing_pids:
            for ex in existing_items:
                if ex.get("product_id") == item["product_id"]:
                    ex["qty"] = ex.get("qty", 1) + 1
                    break
        else:
            existing_items.append(item)

    # Clear direct request state, keep browse mode for cart flow
    ctx.pop("direct_request", None)
    ctx.pop("direct_segments", None)
    ctx.pop("direct_option_list", None)

    names = ", ".join(it["product_name"] for it in items)
    _send_browse_quote(phone, sender_name, names, existing_items, duration)
    return True


# ── Browse Cart Modification Flow ────────────────────────────────────

def _apply_browse_cart_modification(phone: str, text: str, sender_name: str) -> bool:
    """
    Apply an add/remove modification to the browse cart.
    Returns True if handled, False to fall through.
    """
    ctx = _browse_context(phone)
    quote = ctx.get("last_browse_quote", {})
    items = list(quote.get("items", []))
    duration = int(quote.get("duration") or ctx.get("browse_duration") or 12)

    if not items:
        return False

    intent, cleaned = _detect_cart_modify_intent(text)

    if intent == "remove":
        cleaned_lower = cleaned.lower()
        new_items = []
        removed_name = None
        for item in items:
            item_name = (item.get("product_name") or item.get("name") or "").lower()
            if not removed_name and (cleaned_lower in item_name or item_name in cleaned_lower
                    or any(w in item_name for w in cleaned_lower.split() if len(w) > 2)):
                removed_name = item.get("product_name") or item.get("name")
                continue  # skip/remove
            new_items.append(item)

        if not removed_name:
            whatsapp_client.send_text_message(
                phone,
                f"Could not find that item in your cart. Try the exact name, e.g.: remove {items[0].get('product_name', 'Fridge')}",
                preview_url=False,
            )
            return True

        if not new_items:
            # Cart is now empty
            whatsapp_client.send_text_message(phone, f"Removed *{removed_name}*. Your cart is now empty.", preview_url=False)
            ctx.pop("last_browse_quote", None)
            ctx.pop("browse_modify_mode", None)
            ctx["browse_step"] = "await_room"
            time.sleep(0.3)
            buttons = [
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text="Would you like to start fresh?",
                buttons=buttons,
                header=BROWSE_FLOW_HEADER,
            )
            return True

        whatsapp_client.send_text_message(phone, f"Removed *{removed_name}* from your cart.", preview_url=False)
        time.sleep(0.3)
        ctx.pop("browse_modify_mode", None)
        _send_browse_quote(phone, sender_name, "modified cart", new_items, duration)
        return True

    elif intent == "add":
        # Parse and add new items
        new_items = parse_cart_items(cleaned)
        matched_new = [it for it in new_items if it.get("matched")]
        if not matched_new:
            whatsapp_client.send_text_message(
                phone,
                "Could not find that product. Try typing the exact name, e.g.: add Study Table",
                preview_url=False,
            )
            return True

        for item in matched_new:
            item["duration"] = duration
            mrp = calculate_rent(item["product_id"], duration) or int(item.get("original_rent") or 0)
            item["original_rent"] = mrp
            item["rent"] = int(round(mrp * 0.70)) if mrp else 0

        existing_pids = {it.get("product_id") for it in items if it.get("product_id")}
        for item in matched_new:
            if item["product_id"] in existing_pids:
                for ex in items:
                    if ex.get("product_id") == item["product_id"]:
                        ex["qty"] = ex.get("qty", 1) + item.get("qty", 1)
                        break
            else:
                items.append(item)

        ctx.pop("browse_modify_mode", None)
        _send_browse_quote(phone, sender_name, "modified cart", items, duration)
        return True

    # No clear intent — check if it's a number to remove by index
    try:
        idx = int(cleaned.strip())
        if 1 <= idx <= len(items):
            removed = items.pop(idx - 1)
            removed_name = removed.get("product_name") or removed.get("name")
            if not items:
                whatsapp_client.send_text_message(phone, f"Removed *{removed_name}*. Your cart is now empty.", preview_url=False)
                ctx.pop("last_browse_quote", None)
                ctx.pop("browse_modify_mode", None)
                ctx["browse_step"] = "await_room"
                time.sleep(0.3)
                buttons = [{"id": "BROWSE_PRODUCTS", "title": "Browse Products"}]
                whatsapp_client.send_interactive_buttons(
                    to_phone=phone, body_text="Would you like to start fresh?",
                    buttons=buttons, header=BROWSE_FLOW_HEADER,
                )
                return True
            whatsapp_client.send_text_message(phone, f"Removed *{removed_name}* from your cart.", preview_url=False)
            time.sleep(0.3)
            ctx.pop("browse_modify_mode", None)
            _send_browse_quote(phone, sender_name, "modified cart", items, duration)
            return True
    except (ValueError, TypeError):
        pass

    return False


def _build_browse_cart_payload(items: List[dict], duration: int) -> List[dict]:
    payload = []
    for item in items:
        if not item.get("product_id"):
            continue
        product = None
        try:
            product = get_product_by_id(item["product_id"])
        except Exception:
            product = None
        amenity_type_id = None
        if isinstance(product, dict):
            amenity_type_id = product.get("amenity_type_id") or product.get("amenity_id") or product.get("type_id") or product.get("id")
        if amenity_type_id is None:
            amenity_type_id = item["product_id"]
        payload.append({
            "amenity_type_id": amenity_type_id,
            "count": int(item.get("qty", 1)),
            "duration": int(duration),
        })
    return payload


def _build_browse_cart_link(items: List[dict], duration: int) -> str:
    payload = _build_browse_cart_payload(items, duration)
    # Keep brackets/braces/colons literal so the backend receives valid JSON array syntax
    encoded_items = quote(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), safe=":,")
    return f"{BROWSE_PRODUCTS_BASE_URL}?token={RENTBASKET_JWT}&referral_code={BROWSE_PRODUCTS_REFERRAL_CODE}&items={encoded_items}"


def _format_browse_estimate(items: List[dict], duration: int) -> Tuple[str, int, int, int]:
    # Only calculate on matched items with real prices
    matched_items = [it for it in items if it.get("matched", True) and (it.get("original_rent") or it.get("rent"))]
    original_monthly = 0
    for item in matched_items:
        original_monthly += int(item.get("original_rent") or item.get("rent") or 0) * int(item.get("qty", 1))
    discounted_monthly = int(round(original_monthly * 0.70))
    savings_total = max(0, (original_monthly - discounted_monthly) * int(duration))

    if original_monthly == 0:
        message = (
            "I could not find exact matches for those items in our catalogue.\n\n"
            "Could you try with more specific names? For example: Storage Bed, Single Door Fridge, Split AC, Study Chair."
        )
        return message, 0, 0, 0

    # Per-item breakdown
    lines = [f"*Your Cart - {duration} Month Rental*", ""]
    for item in matched_items:
        name = item.get("product_name") or item.get("name") or "Product"
        qty = int(item.get("qty", 1))
        per_unit_mrp = int(item.get("original_rent") or item.get("rent") or 0)
        per_unit_disc = int(round(per_unit_mrp * 0.70)) if per_unit_mrp else 0
        if qty > 1:
            line_total = per_unit_disc * qty
            lines.append(f"- {name} x{qty}:  Rs. {per_unit_disc:,} x {qty} = Rs. {line_total:,}/mo")
        else:
            lines.append(f"- {name}:  Rs. {per_unit_disc:,}/mo  (was Rs. {per_unit_mrp:,})")

    lines.append("")
    monthly_saving = original_monthly - discounted_monthly
    lines.append(f"Monthly Total: Rs. {discounted_monthly:,}  (saving Rs. {monthly_saving:,}/mo vs MRP)")
    lines.append(f"Total saving over {duration} months: Rs. {savings_total:,}")

    # Upfront option for 12+ month rentals
    if duration >= 12:
        upfront_monthly = int(round(discounted_monthly * 0.90))
        upfront_total_saving = max(0, (original_monthly - upfront_monthly) * int(duration))
        lines.append(f"\nPay upfront: Rs. {upfront_monthly:,}/mo  (extra 10% off — save Rs. {upfront_total_saving:,} total)")

    message = "\n".join(lines)
    return message, original_monthly, discounted_monthly, savings_total


def _send_browse_quote(phone: str, sender_name: str, source_text: str, items: List[dict], duration: int) -> None:
    normalized_phone = normalize_phone(phone)

    # Filter out unmatched / Rs.0 items before building cart link
    matched_items = [it for it in items if it.get("matched", True) and it.get("product_id")]

    quote_text, original_monthly, discounted_monthly, savings_total = _format_browse_estimate(items, duration)

    # If nothing matched, send the error message without cart buttons
    if original_monthly == 0:
        whatsapp_client.send_text_message(phone, quote_text, preview_url=False)
        # Keep browse mode active so they can try again
        session_context[phone] = session_context.get(phone, {})
        session_context[phone]["browse_mode"] = True
        session_context[phone]["browse_step"] = "await_items"
        return

    cart_link = _build_browse_cart_link(matched_items, duration)

    session_context[phone] = session_context.get(phone, {})
    session_context[phone]["last_browse_quote"] = {
        "items": matched_items,
        "duration": duration,
        "original_monthly": original_monthly,
        "discounted_monthly": discounted_monthly,
        "savings_total": savings_total,
        "cart_link": cart_link,
        "source_text": source_text,
    }
    session_context[phone]["browse_mode"] = True
    session_context[phone]["browse_step"] = "quote_ready"

    _save_browse_lead_data(normalized_phone, {
        "duration_months": duration,
        "browse_requested_items": source_text,
        "browse_quote_original_monthly": original_monthly,
        "browse_quote_discounted_monthly": discounted_monthly,
        "browse_quote_savings_total": savings_total,
        "browse_cart_link": cart_link,
        "lead_stage": "browse_quote_ready",
    })

    # Notify about unmatched items if any
    unmatched = [it for it in items if not it.get("matched") or not it.get("product_id")]
    if unmatched:
        unmatched_names = ", ".join(it.get("name", "unknown") for it in unmatched)
        whatsapp_client.send_text_message(
            phone,
            f"Note: I could not find a match for: {unmatched_names}. Showing the items I found.",
            preview_url=False,
        )
        time.sleep(0.3)

    whatsapp_client.send_text_message(phone, quote_text, preview_url=False)
    time.sleep(0.4)

    buttons = [
        {"id": "BROWSE_SHOW_DETAILS", "title": "View Cart"},
        {"id": "BROWSE_PRODUCTS", "title": "Browse More"},
        {"id": "BROWSE_CUSTOMER_REVIEWS", "title": "Reviews"},
    ]
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text="What would you like to do next?",
        buttons=buttons,
        header="Browse Quote",
    )


def _send_browse_full_details(phone: str, sender_name: str) -> bool:
    ctx = session_context.get(phone, {})
    quote = ctx.get("last_browse_quote", {})
    items = quote.get("items", [])
    duration = int(quote.get("duration") or 12)
    cart_link = quote.get("cart_link") or _build_browse_cart_link(items, duration)
    normalized_phone = normalize_phone(phone)

    if not items:
        whatsapp_client.send_text_message(phone, "No browse quote found yet. Please share the product list again.")
        return True

    # ── Build professional cart format ────────────────────────────
    sep = "\u2501" * 20  # ━━━━━━━━━━━━━━━━━━━━

    lines = [
        "Here are the details for your selected items:",
        "",
        "*Order Confirmation*",
        f"Your Cart - {duration} Month Rental",
        sep,
        "",
        "*Order Details*",
    ]

    total_rent = 0
    total_mrp = 0
    item_names = []
    for item in items:
        product_name = item.get("product_name") or item.get("name") or "Product"
        qty = int(item.get("qty", 1))
        per_unit_mrp = int(item.get("original_rent") or item.get("rent") or 0)
        per_unit_disc = int(item.get("rent") or int(round(per_unit_mrp * 0.70)) if per_unit_mrp else 0)
        line_rent = per_unit_disc * qty
        line_mrp = per_unit_mrp * qty
        total_rent += line_rent
        total_mrp += line_mrp
        item_names.append(f"{product_name} x{qty}")

        lines.append(f"- {qty}x {product_name}")
        lines.append(f"  ~Rs. {per_unit_mrp:,}/mo~ *Rs. {per_unit_disc:,}/mo* + GST")

    # Monthly rent breakdown
    gst = int(round(total_rent * 0.18))
    net_monthly = total_rent + gst

    lines.append("")
    lines.append(sep)
    lines.append("*Monthly Rent*")
    lines.append(f"- Rent: Rs. {total_rent:,}/mo")
    lines.append(f"- GST (18%): Rs. {gst:,}/mo")
    lines.append(f"- *Net Monthly: Rs. {net_monthly:,}/mo*")

    # One-time charges
    security_deposit = total_rent * 2
    lines.append("")
    lines.append(sep)
    lines.append("*One Time Charges*")
    lines.append(f"- Security Deposit: Rs. {security_deposit:,} _(refundable)_")
    lines.append("- Delivery: ~Rs. 400~ Rs. 0")
    lines.append("- Installation: ~Rs. 500~ Rs. 0")
    net_first_month = net_monthly + security_deposit
    lines.append(f"- *Net Payable (1st Month): Rs. {net_first_month:,}*")

    # Savings
    monthly_saving = total_mrp - total_rent
    total_saving = monthly_saving * duration
    lines.append("")
    lines.append(sep)
    lines.append(f"You save *Rs. {monthly_saving:,}/month* x {duration} months = *Rs. {total_saving:,}* on this cart!")

    # Terms
    lines.append("")
    lines.append("*Terms & Conditions*")
    lines.append("- Products are in mint condition")
    lines.append("- Standard maintenance included")
    lines.append("- Free shipping & standard installation")
    lines.append("- Complete KYC before delivery")

    # Log the full cart to database
    _save_browse_lead_data(normalized_phone, {
        "final_cart_items": ", ".join(item_names),
        "final_cart_monthly": total_rent,
        "final_cart_net_monthly": net_monthly,
        "final_cart_duration": duration,
        "final_cart_savings": total_saving,
        "final_cart_link": cart_link,
        "lead_stage": "cart_viewed",
    })

    whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=False)
    time.sleep(0.4)

    # Three action buttons
    buttons = [
        {"id": "BROWSE_MODIFY_CART", "title": "Modify Cart"},
        {"id": "BROWSE_CUSTOMER_REVIEWS", "title": "Check Reviews"},
        {"id": "BROWSE_CHECKOUT", "title": "Checkout"},
    ]
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text="What would you like to do?",
        buttons=buttons,
        header="Your Cart",
    )
    return True


def _handle_browse_products_text(phone: str, sender_name: str, text: str, message_id: str) -> bool:
    ctx = _browse_context(phone)
    if not ctx.get("browse_mode"):
        return False

    normalized_phone = normalize_phone(phone)
    raw_text = (text or "").strip()
    if not raw_text:
        return True

    step = ctx.get("browse_step", "await_duration")

    # ── Direct request flow: user picks from options list ─────────
    if step == "direct_await_duration":
        duration = _parse_duration_from_text(raw_text)
        if duration is None:
            _send_duration_buttons(phone)
            return True
        ctx["browse_duration"] = duration
        _save_browse_lead_data(normalized_phone, {"duration_months": duration, "lead_stage": "direct_duration_set"})
        _send_direct_request_options(phone)
        return True

    if step == "direct_await_selection":
        if _handle_direct_selection(phone, raw_text, sender_name):
            return True
        # If direct selection failed, re-show options
        _send_direct_request_options(phone)
        return True

    # ── Browse cart modify mode: add/remove items ─────────────────
    if ctx.get("browse_modify_mode"):
        if _apply_browse_cart_modification(phone, raw_text, sender_name):
            return True
        # If modification didn't work, show instructions again
        quote = ctx.get("last_browse_quote", {})
        items = quote.get("items", [])
        item_list = "\n".join(f"{i}. {it.get('product_name', '?')}" for i, it in enumerate(items, 1))
        whatsapp_client.send_text_message(
            phone,
            f"Could not understand that. Your current cart:\n{item_list}\n\n"
            f"Try: 'remove fridge' or 'add study table' or reply with an item number to remove it.",
            preview_url=False,
        )
        return True

    if step == "await_duration":
        duration = _parse_duration_from_text(raw_text)
        if duration is None:
            # Re-show the duration buttons
            _send_duration_buttons(phone)
            return True

        ctx["browse_duration"] = duration
        ctx["browse_step"] = "await_room"
        _save_browse_lead_data(normalized_phone, {"duration_months": duration, "lead_stage": "browse_duration_set"})
        whatsapp_client.send_text_message(
            phone,
            f"Got it, {duration} months. Now pick a room to start browsing.",
            preview_url=False,
        )
        time.sleep(0.3)
        _send_room_selection(phone)
        return True

    if step == "await_checkout_location":
        return _handle_checkout_location(phone, raw_text, sender_name)

    if step == "await_room":
        # User typed a room name instead of tapping the list
        matched_room = ROOM_TEXT_MATCH.get(raw_text.lower().strip())
        if matched_room:
            if matched_room == "ROOM_1BHK":
                _send_1bhk_package_buttons(phone)
            else:
                _send_subcategory_selection(phone, matched_room)
            return True
        # Not a room — re-show list
        _send_room_selection(phone)
        return True

    if step == "await_subcategory":
        # User typed a subcategory name instead of tapping
        room_id = ctx.get("browse_room", "")
        room = ROOM_CATEGORIES.get(room_id, {})
        subcats = room.get("subcategories", {})
        lower = raw_text.lower().strip()
        for sc_id, sc in subcats.items():
            if lower in sc["title"].lower() or sc["title"].lower() in lower:
                _send_variant_list(phone, room_id, sc_id)
                return True
        # Not matched — re-show subcategories
        if room_id == "ROOM_1BHK":
            _send_1bhk_package_buttons(phone)
        elif room_id:
            _send_subcategory_selection(phone, room_id)
        else:
            _send_room_selection(phone)
        return True

    if step == "await_variant_action":
        # User typed an item number/name from the variant list
        if _handle_variant_text_selection(phone, raw_text, sender_name):
            return True
        # Variant list exists but input didn't match — do NOT fall through
        # to the free-text parser (which would replace the cart)
        variants = ctx.get("browse_variant_list", [])
        if variants:
            whatsapp_client.send_text_message(
                phone,
                f"Could not match that. Reply with a number (1-{len(variants)}) or the exact item name from the list above.",
                preview_url=False,
            )
            return True
        # No variant list (edge case) — fall through to free-text

    if step in ("await_items", "await_variant_action", "await_product_finalization", "quote_ready"):
        duration = int(ctx.get("browse_duration") or _parse_duration_from_text(raw_text) or 12)

        # Strip additive prefixes ("also", "and a", "I also want") before parsing
        cleaned_text = raw_text
        additive_prefixes = [
            r"^(?:i\s+)?also\s+(?:want\s+(?:to\s+)?(?:add\s+)?)?",
            r"^(?:and\s+)?(?:also\s+)?(?:add|include)\s+",
            r"^and\s+(?:a\s+)?",
            r"^plus\s+",
        ]
        is_additive = False
        for pat in additive_prefixes:
            m = re.match(pat, cleaned_text.strip().lower())
            if m:
                cleaned_text = cleaned_text.strip()[m.end():].strip()
                is_additive = True
                break

        items = parse_cart_items(cleaned_text)
        if not items:
            if step in ("await_items", "await_variant_action"):
                _send_room_selection(phone)
                whatsapp_client.send_text_message(
                    phone,
                    "I could not match those items. Please pick a room above or type more specific names, e.g.: Storage Bed, Single Door Fridge, Split AC.",
                    preview_url=False,
                )
            else:
                whatsapp_client.send_text_message(
                    phone,
                    "I could not finalize the product list from that message. Please share the exact items or pick a room above.",
                    preview_url=False,
                )
            return True

        for item in items:
            if item.get("product_id"):
                try:
                    product = get_product_by_id(item["product_id"])
                except Exception:
                    product = None
                original_rent = calculate_rent(item["product_id"], duration) or int(item.get("original_rent") or item.get("rent") or 0)
                item["duration"] = duration
                item["original_rent"] = original_rent
                item["rent"] = int(round(original_rent * 0.70)) if original_rent else 0
                if isinstance(product, dict):
                    item["product_name"] = product.get("name") or item.get("product_name")

        # If this is an additive request and we have an existing quote, merge items
        existing_quote = ctx.get("last_browse_quote", {})
        if (is_additive or step == "quote_ready") and existing_quote.get("items"):
            # Only merge matched items (skip unmatched ones from the new request)
            new_matched = [it for it in items if it.get("matched")]
            if new_matched:
                existing_items = list(existing_quote["items"])
                existing_ids = {it.get("product_id") for it in existing_items if it.get("product_id")}
                for item in new_matched:
                    if item.get("product_id") in existing_ids:
                        # Update qty for duplicate product
                        for ex in existing_items:
                            if ex.get("product_id") == item["product_id"]:
                                ex["qty"] = ex.get("qty", 1) + item.get("qty", 1)
                                break
                    else:
                        existing_items.append(item)
                items = existing_items

        ctx["browse_requested_items"] = raw_text
        ctx["browse_step"] = "quote_ready"
        _send_browse_quote(phone, sender_name, raw_text, items, duration)
        return True

    return False

# Words that count as a greeting (first message or re-greeting)
GREETING_WORDS = {"hi", "hello", "hey", "hii", "hiii", "helo", "heloo", "helloo",
                  "namaste", "namaskar", "good morning", "good afternoon", "good evening",
                  "hola", "yo", "sup", "start", "hai", "hlw", "hlo", "hy",
                  "ho", "hoo", "h", "ji", "hellow", "helo"}

def is_greeting(text: str) -> bool:
    """Return True if the message is a greeting word."""
    return text.strip().lower() in GREETING_WORDS

# ========================================
# SPECIAL CUSTOMER HANDLER
# ========================================

def handle_greeting(phone: str, sender_name: str):
    """
    Send the structured greeting message with interactive buttons.
    This bypasses the LLM entirely for a deterministic, instant response.
    """
    normalized_phone = normalize_phone(phone)
    
    # Use proper name if it looks real, otherwise generic
    name = sender_name if sender_name and sender_name.strip() else "there"

    greeting_text = (
        f"Hi {name}\n"
        f"I'm Ku from RentBasket, your personal rental assistant.\n"
        f"\n"
        f"We offer quality furniture and appliances on rent at affordable prices, "
        f"powered by customer service which is best in the market.\n"
        f"\n"
        f"Check out our website for more details:\n"
        f"https://rentbasket.com"
    )
    buttons = GREETING_BUTTONS
    action_type = "greeting"

    try:
        result = whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text=greeting_text,
            buttons=buttons
        )
        if "error" in result:
            print(f"   \u26a0\ufe0f Interactive buttons failed: {result['error']}")
            print(f"   \u21a9\ufe0f Falling back to plain text...")
            whatsapp_client.send_text_message(phone, greeting_text, preview_url=True)
    except Exception as e:
        print(f"   \u274c Error sending greeting buttons: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to plain text
        try:
            whatsapp_client.send_text_message(phone, greeting_text, preview_url=True)
        except Exception as e2:
            print(f"   \u274c Even plain text failed: {e2}")

    # --- LEAD TRACKING (independent — must not depend on session/logging) ---
    try:
        existing_lead = get_lead(normalized_phone)
        lead_payload = {
            "name": sender_name or "New Lead",
            "phone": normalized_phone,
            "push_name": sender_name,
        }
        # Only set lead_stage to "new" for genuinely new leads
        # Don't overwrite advanced stages like "cart_created" or "qualified"
        if not existing_lead:
            lead_payload["lead_stage"] = "new"
        upsert_lead(normalized_phone, lead_payload)
    except Exception as e:
        print(f"   CRITICAL: Lead creation failed for {normalized_phone}: {e}")
        import traceback; traceback.print_exc()

    # --- RESTORE LEAD DATA INTO CONVERSATION STATE ---
    # When user re-greets, create a fresh state. Restore name and location but NOT duration,
    # since the user is starting a new conversation and should be asked about duration again.
    try:
        with conversations_lock:
            conversations[phone] = create_initial_state()
            conversations[phone] = restore_lead_to_state(normalized_phone, conversations[phone])
            # Clear duration on re-greeting — user starts fresh, will be asked again
            conversations[phone]["collected_info"].pop("duration_months", None)
            if sender_name:
                conversations[phone]["collected_info"]["customer_name"] = sender_name
            conversations[phone]["collected_info"]["phone"] = normalized_phone
    except Exception as e:
        print(f"   Warning: State restoration failed (non-fatal): {e}")

    # Also clear any stale browse/sales session context on re-greeting
    session_context.pop(phone, None)

    # Log to DB + file (non-critical — failures here must never block lead creation)
    try:
        session_id = get_or_create_session(normalized_phone, sender_name)
        log_conversation_turn(normalized_phone, sender_name, "[Greeting]", greeting_text,
                              session_id=session_id, agent_used="sales")
        log_event(normalized_phone, action_type, {"buttons": [b["id"] for b in buttons]},
                  session_id=session_id)
    except Exception as e:
        print(f"   Logging error (non-fatal): {e}")

    print(f"   Greeting + interactive buttons sent to {phone}")
    return jsonify({"status": "ok", "action": action_type}), 200


FALLBACK_EXAMPLES = [
    [
        "• \"Fridge for 6 months\"",
        "• \"Sofa in Gurgaon\"",
        "• \"1BHK setup under ₹3000\""
    ],
    [
        "• \"Washing machine for 3 months\"",
        "• \"Bed and mattress on rent\"",
        "• \"Furniture for PG room\""
    ]
]

# Track set rotation
fallback_counter = 0

def get_next_fallback_examples() -> str:
    """Get the next set of fallback examples (rotated)."""
    global fallback_counter
    examples = FALLBACK_EXAMPLES[fallback_counter % len(FALLBACK_EXAMPLES)]
    fallback_counter += 1
    return "\n".join(examples)


# ========================================
# SALES MODE: Cart Builder + Voice Transcription
# ========================================

from data.products import (
    search_products_by_name,
    calculate_rent,
    apply_discount,
    get_product_by_id,
)

# ---------------------------
# CONFIG
# ---------------------------

GST_RATE = 0.18
DEFAULT_DURATION = 12
MAX_DURATION = 36

# Initialize OpenAI client once
# Make sure OPENAI_API_KEY is set in your environment
openai_client = OpenAI()

# Optional shared state expected by your app
# session_context = {}
# per_phone_locks = {}
# per_phone_locks_lock = threading.Lock()
# whatsapp_client = ...
# normalize_phone = ...
# get_or_create_session = ...
# log_conversation_turn = ...
# log_event = ...


# ---------------------------
# HELPERS
# ---------------------------

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def _safe_int(value: str, default: int = 1) -> int:
    try:
        return int(value)
    except Exception:
        return default


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"[“”\"']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_duration(text: str, default: int = DEFAULT_DURATION) -> int:
    """
    Extract duration from text like:
    - for 12 months
    - 6 months
    - for six months
    """
    t = normalize_text(text)

    # Numeric duration
    m = re.search(r"(?:for\s*)?(\d{1,2})\s*(?:months?|mo\b)", t)
    if m:
        duration = _safe_int(m.group(1), default)
        return max(1, min(duration, MAX_DURATION))

    # Word duration
    for word, num in WORD_NUMBERS.items():
        if re.search(rf"(?:for\s*)?\b{word}\b\s*(?:months?|mo\b)", t):
            return max(1, min(num, MAX_DURATION))

    return default


def remove_duration_phrases(text: str) -> str:
    t = normalize_text(text)
    t = re.sub(r"(?:for\s*)?\d{1,2}\s*(?:months?|mo\b)", "", t)
    for word in WORD_NUMBERS.keys():
        t = re.sub(rf"(?:for\s*)?\b{word}\b\s*(?:months?|mo\b)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def extract_qty_and_item(segment: str) -> Tuple[int, str]:
    """
    Supports:
    - 2 bed
    - 2x bed
    - two bed
    - 2 beds
    """
    seg = normalize_text(segment)

    # numeric quantity
    m = re.match(r"^(\d+)\s*x?\s+(.+)$", seg)
    if m:
        qty = max(1, _safe_int(m.group(1), 1))
        item = m.group(2).strip()
        return qty, item

    # word quantity
    for word, num in WORD_NUMBERS.items():
        if seg.startswith(word + " "):
            item = seg[len(word):].strip()
            return max(1, num), item

    return 1, seg


def split_into_segments(text: str) -> List[str]:
    """
    Break a transcript into likely product chunks.
    """
    t = normalize_text(text)

    # Normalize separators common in speech-to-text
    t = t.replace(" plus ", ", ")
    t = t.replace(" also ", ", ")
    t = t.replace(" तथा ", ", ")  # harmless if transcript has mixed language

    # Split "and" only when between distinct items (not inside product names like "bed and mattress")
    # Use "and" as separator but keep known compound products together
    compound_products = ["bed and mattress", "sofa and center table", "table and chair",
                         "table and chairs", "bed and mattresses"]
    for cp in compound_products:
        placeholder = cp.replace(" and ", " & ")
        t = t.replace(cp, placeholder)
    t = t.replace(" and ", ", ")
    for cp in compound_products:
        placeholder = cp.replace(" and ", " & ")
        t = t.replace(placeholder, cp)

    # Split by commas / newlines / semicolons
    raw_segments = re.split(r"[,\n;]+", t)
    segments = [s.strip() for s in raw_segments if s.strip()]
    return segments


def clean_item_segment(segment: str) -> str:
    """
    Remove filler words that often appear in voice transcripts.
    """
    seg = normalize_text(segment)

    # Remove leading filler phrases (more comprehensive for voice transcripts)
    filler_prefixes = [
        r"^(?:i\s+)?(?:need|want|would\s+like)\s+(?:to\s+(?:have|get|rent|add)\s+)?",
        r"^(?:please\s+)?(?:add|give\s+me|get\s+me|send\s+me)\s+",
        r"^(?:also\s+)?(?:include|put\s+in)\s+",
        r"^(?:can\s+(?:i|you)\s+(?:get|add|have)\s+(?:me\s+)?)",
    ]
    for pat in filler_prefixes:
        seg = re.sub(pat, "", seg)

    # Remove trailing/embedded filler words
    seg = re.sub(r"\b(please|kindly)\b", "", seg)
    # Remove "in quantity" and similar noise from transcripts
    seg = re.sub(r"\bin\s+quantity\b", "", seg)
    # Remove "one in" / "one for" when it's noise (not a number)
    seg = re.sub(r"\bone\s+(?:in|for)\s*$", "", seg)

    seg = re.sub(r"\s+", " ", seg).strip()
    return seg


# ---------------------------
# CART PARSING
# ---------------------------

def parse_cart_items(text: str) -> List[dict]:
    """
    Parse free-text or transcript input into cart items.

    Returns:
        [
          {
            name, qty, duration, product_id, product_name,
            rent, original_rent, matched
          },
          ...
        ]
    """
    if not text or not text.strip():
        return []

    duration = extract_duration(text, DEFAULT_DURATION)
    text_wo_duration = remove_duration_phrases(text)

    segments = split_into_segments(text_wo_duration)
    items = []

    for seg in segments:
        seg = clean_item_segment(seg)
        if not seg:
            continue

        qty, item_text = extract_qty_and_item(seg)
        item_text = re.sub(r"\b(for|months?|mo)\b.*$", "", item_text).strip()

        if not item_text:
            continue

        matches = search_products_by_name(item_text) or []
        if matches:
            product = matches[0]
            original_rent = calculate_rent(product["id"], duration) or 0
            final_rent = apply_discount(original_rent) if original_rent else 0

            items.append({
                "name": item_text,
                "qty": qty,
                "duration": duration,
                "product_id": product["id"],
                "product_name": product["name"],
                "rent": final_rent,
                "original_rent": original_rent,
                "matched": True,
            })
        else:
            items.append({
                "name": item_text,
                "qty": qty,
                "duration": duration,
                "product_id": None,
                "product_name": item_text.title(),
                "rent": 0,
                "original_rent": 0,
                "matched": False,
            })

    return items


# ---------------------------
# FORMATTING
# ---------------------------

def format_sales_cart(items: list, duration: int = DEFAULT_DURATION) -> str:
    """
    WhatsApp-friendly cart message.
    """
    if not items:
        return (
            "I could not find any matching products.\n\n"
            "Please try again with items like:\n"
            "bed, fridge, washing machine, sofa, AC, mattress"
        )

    lines = []
    lines.append("*Tentative Cart*")
    lines.append(f"Duration: {duration} months\n")

    total_monthly = 0

    for i, item in enumerate(items, 1):
        product_name = item["product_name"]
        pid_str = f"#{item['product_id']}" if item["product_id"] else "(not found)"
        qty = item["qty"]
        per_unit_rent = item["rent"] or 0
        item_monthly = per_unit_rent * qty

        if item["matched"] and per_unit_rent:
            rent_str = f"₹{per_unit_rent:,}/mo"
        else:
            rent_str = "Price N/A"

        lines.append(f"{i}. {product_name} {pid_str}")
        lines.append(f"   Qty: {qty} | {rent_str} + GST")

        total_monthly += item_monthly

    gst = int(round(total_monthly * GST_RATE))
    grand_total = total_monthly + gst

    lines.append(
        f"\n*Monthly Rent: ₹{total_monthly:,} + GST (₹{gst:,}) = ₹{grand_total:,}/mo*"
    )
    lines.append("\n_Note: Security deposit & one-time charges may apply at the time of order._")

    return "\n".join(lines)


# ---------------------------
# VOICE TRANSCRIPTION
# ---------------------------

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "voice_note.ogg") -> str:
    """
    Transcribe WhatsApp voice note audio into text.
    """
    if not audio_bytes:
        return ""

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # important for transcription APIs

    transcript = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )

    text = getattr(transcript, "text", "") or ""
    return text.strip()


# ---------------------------
# MAIN FLOW
# ---------------------------

def build_and_send_sales_cart(phone: str, sender_name: str, text: str, source: str = "text"):
    """
    Parse text, build cart, send it with action buttons.
    Filters out unmatched items and warns the user about them.
    """
    items = parse_cart_items(text)
    duration = items[0]["duration"] if items else DEFAULT_DURATION

    # Separate matched from unmatched
    matched = [it for it in items if it.get("matched")]
    unmatched = [it for it in items if not it.get("matched")]

    # Warn about unmatched items
    if unmatched:
        unmatched_names = ", ".join(it.get("name", "unknown") for it in unmatched)
        whatsapp_client.send_text_message(
            phone,
            f"Could not find: {unmatched_names}. Try more specific names (e.g. 'single door fridge' instead of 'fridge').",
        )
        time.sleep(0.3)

    # Build cart text with only matched items (or show "no matches" message)
    cart_text = format_sales_cart(matched, duration)

    # Store cart in session for later actions like Upfront Payment / Modify Cart
    ctx = session_context.get(phone, {})
    ctx["last_cart"] = matched
    ctx["last_duration"] = duration
    ctx["last_source"] = source
    ctx["last_raw_text"] = text
    ctx["sales_mode"] = True
    session_context[phone] = ctx

    whatsapp_client.send_text_message(phone, cart_text)
    time.sleep(0.5)

    # Only show action buttons if we have matched items
    if matched:
        cart_buttons = [
            {"id": "UPFRONT_PAYMENT", "title": "Upfront Payment"},
            {"id": "MODIFY_CART", "title": "Modify Cart"},
            {"id": "FINAL_LINK", "title": "Final Link"},
        ]

        whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text="Choose an option:",
            buttons=cart_buttons,
        )

    normalized_phone = normalize_phone(phone)
    session_id = get_or_create_session(normalized_phone, sender_name)

    log_conversation_turn(
        normalized_phone,
        sender_name,
        text,
        cart_text,
        session_id=session_id,
        agent_used="sales_cart_builder",
    )

    log_event(
        normalized_phone,
        "sales_cart_built",
        {"items": len(items), "duration": duration, "source": source},
        session_id=session_id,
    )


def _detect_cart_modify_intent(text: str) -> tuple:
    """
    Detect if text is a cart modification instruction (add/remove).
    Returns: (intent, cleaned_text) where intent is 'remove', 'add', or None.
    """
    t = text.strip().lower()
    # Remove patterns
    remove_patterns = [
        r"^remove\s+(?:the\s+)?",
        r"^delete\s+(?:the\s+)?",
        r"^take\s+out\s+(?:the\s+)?",
        r"^drop\s+(?:the\s+)?",
        r"^cancel\s+(?:the\s+)?",
        r"^no\s+(?:need\s+(?:for\s+)?)?(?:the\s+)?",
        r"^don'?t\s+(?:need|want)\s+(?:the\s+)?",
        r"^hat(?:a|ao?)\s+(?:do|de)\s+",  # Hindi: hata do
    ]
    for pat in remove_patterns:
        m = re.match(pat, t)
        if m:
            cleaned = t[m.end():].strip()
            return ("remove", cleaned)

    # Add patterns
    add_patterns = [
        r"^(?:also\s+)?add\s+",
        r"^(?:also\s+)?include\s+",
        r"^put\s+in\s+",
        r"^(?:also\s+)?want\s+(?:to\s+add\s+)?",
        r"^(?:also\s+)?need\s+",
        r"^aur\s+",  # Hindi: aur (and more)
    ]
    for pat in add_patterns:
        m = re.match(pat, t)
        if m:
            cleaned = t[m.end():].strip()
            return ("add", cleaned)

    return (None, t)


def _apply_cart_modification(phone: str, text: str) -> bool:
    """
    Try to apply an add/remove modification to the existing SALES cart.
    Returns True if a modification was applied, False if we should build a fresh cart.
    """
    ctx = session_context.get(phone, {})
    last_cart = ctx.get("last_cart", [])
    duration = ctx.get("last_duration", 12)

    if not last_cart:
        return False

    intent, cleaned = _detect_cart_modify_intent(text)
    if intent is None:
        # Check if it looks like a full product list (has commas, 'and', multiple items)
        # If so, replace the cart entirely. Otherwise, treat as add.
        segments = split_into_segments(text)
        if len(segments) >= 2:
            return False  # Looks like a full new list — let build_and_send_sales_cart handle it
        # Single item without explicit intent — treat as add
        intent = "add"
        cleaned = text.strip().lower()

    if intent == "remove":
        # Find and remove matching items from cart
        cleaned_lower = cleaned.lower()
        new_cart = []
        removed = False
        for item in last_cart:
            item_name = (item.get("product_name") or item.get("name") or "").lower()
            # Check if the remove text matches this item
            if not removed and (cleaned_lower in item_name or item_name in cleaned_lower
                    or any(w in item_name for w in cleaned_lower.split() if len(w) > 2)):
                removed = True
                continue  # Skip this item (remove it)
            new_cart.append(item)

        if not removed:
            return False  # Didn't find anything to remove — let it rebuild

        ctx["last_cart"] = new_cart
        # Rebuild and resend the cart with remaining items
        cart_text = format_sales_cart(new_cart, duration)
        whatsapp_client.send_text_message(phone, cart_text)
        time.sleep(0.5)

        cart_buttons = [
            {"id": "UPFRONT_PAYMENT", "title": "Upfront Payment"},
            {"id": "MODIFY_CART", "title": "Modify Cart"},
            {"id": "FINAL_LINK", "title": "Final Link"},
        ]
        whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text="Choose an option:",
            buttons=cart_buttons,
        )
        ctx.pop("sales_modify_mode", None)
        return True

    elif intent == "add":
        # Parse the new items and append to existing cart
        new_items = parse_cart_items(cleaned)
        matched_new = [it for it in new_items if it.get("matched")]
        if not matched_new:
            return False  # Couldn't find the product — let it rebuild

        # Override duration from existing cart
        for item in matched_new:
            item["duration"] = duration

        combined_cart = list(last_cart) + matched_new
        ctx["last_cart"] = combined_cart

        cart_text = format_sales_cart(combined_cart, duration)
        whatsapp_client.send_text_message(phone, cart_text)
        time.sleep(0.5)

        cart_buttons = [
            {"id": "UPFRONT_PAYMENT", "title": "Upfront Payment"},
            {"id": "MODIFY_CART", "title": "Modify Cart"},
            {"id": "FINAL_LINK", "title": "Final Link"},
        ]
        whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text="Choose an option:",
            buttons=cart_buttons,
        )
        ctx.pop("sales_modify_mode", None)
        return True

    return False


def process_sales_text_async(phone: str, sender_name: str, text: str, message_id: str):
    """
    Background thread: build cart from typed text in SALES mode.
    If in modify mode, try to apply add/remove to existing cart first.
    """
    with per_phone_locks_lock:
        if phone not in per_phone_locks:
            per_phone_locks[phone] = threading.Lock()
        user_lock = per_phone_locks[phone]

    with user_lock:
        try:
            ctx = session_context.get(phone, {})
            # If in modify mode, try to apply modification to existing cart
            if ctx.get("sales_modify_mode") or ctx.get("last_cart"):
                if _apply_cart_modification(phone, text):
                    print(f"Sales cart modified for {phone}")
                    return

            # Otherwise build fresh cart
            build_and_send_sales_cart(phone, sender_name, text, source="text")
            print(f"Sales cart sent to {phone} from text")
        except Exception as e:
            print(f"Error building sales cart for {phone}: {e}")
            import traceback
            traceback.print_exc()
            whatsapp_client.send_text_message(
                phone,
                "Sorry, I couldn't process that. Please try again with product names like: bed, fridge, sofa, AC, washing machine."
            )


def process_sales_audio_async(phone: str, sender_name: str, media_id: str, message_id: str):
    """
    Background thread: download audio, transcribe it, then build cart.
    """
    with per_phone_locks_lock:
        if phone not in per_phone_locks:
            per_phone_locks[phone] = threading.Lock()
        user_lock = per_phone_locks[phone]

    with user_lock:
        try:
            # Step 1: Download audio
            audio_bytes = whatsapp_client.download_media(media_id)
            if not audio_bytes:
                whatsapp_client.send_text_message(
                    phone,
                    "Sorry, I couldn't download your voice message. Please type your cart items instead."
                )
                return

            # Step 2: Transcribe
            transcribed_text = transcribe_audio_bytes(audio_bytes, filename="voice_note.ogg")
            if not transcribed_text:
                whatsapp_client.send_text_message(
                    phone,
                    "I couldn't understand the voice message. Please try again or type your cart items."
                )
                return

            # Step 3: Confirm what was heard
            whatsapp_client.send_text_message(phone, f'You said: "{transcribed_text}"')
            time.sleep(0.3)

            # Step 4: Build real cart from transcript
            build_and_send_sales_cart(phone, sender_name, transcribed_text, source="voice")
            print(f"Sales cart sent to {phone} from voice note")

        except Exception as e:
            print(f"Error processing sales audio for {phone}: {e}")
            import traceback
            traceback.print_exc()
            whatsapp_client.send_text_message(
                phone,
                "Sorry, I couldn't process your voice message. Please type your cart items instead."
            )


def process_browse_audio_async(phone: str, sender_name: str, media_id: str, message_id: str):
    """
    Background thread: download audio, transcribe it, then continue the browse flow.
    """
    with per_phone_locks_lock:
        if phone not in per_phone_locks:
            per_phone_locks[phone] = threading.Lock()
        user_lock = per_phone_locks[phone]

    with user_lock:
        try:
            audio_bytes = whatsapp_client.download_media(media_id)
            if not audio_bytes:
                whatsapp_client.send_text_message(
                    phone,
                    "Sorry, I couldn't download your voice message. Please type the duration or the product list instead."
                )
                return

            transcribed_text = transcribe_audio_bytes(audio_bytes, filename="browse_voice_note.ogg")
            if not transcribed_text:
                whatsapp_client.send_text_message(
                    phone,
                    "I couldn't understand the voice message. Please try again or type the duration/product list."
                )
                return

            whatsapp_client.send_text_message(phone, f'You said: "{transcribed_text}"')
            time.sleep(0.3)
            _handle_browse_products_text(phone, sender_name, transcribed_text, message_id)
            print(f"Browse flow handled for {phone} from voice note")

        except Exception as e:
            print(f"Error processing browse audio for {phone}: {e}")
            import traceback
            traceback.print_exc()
            whatsapp_client.send_text_message(
                phone,
                "Sorry, I couldn't process your voice message. Please type the duration or product list instead."
            )

# FLASK APP
# ========================================

app = Flask(__name__)

# Store conversations per phone number
conversations = {}  # phone_number -> ConversationState

# Store session context for interactive button handling
session_context = {}  # phone_number -> {last_product, handoff_needed, intent, sales_mode, last_cart}

# Cache for processed message IDs to prevent duplicates (Meta retries)
# Using a dict with timestamps so we can expire old entries
processed_ids_dict = {}  # message_id -> timestamp
MAX_CACHE_SIZE = 500
CACHE_EXPIRY_SECONDS = 300  # 5 minutes

# THREAD SAFETY: Global lock for shared dictionaries and per-phone processing
conversations_lock = threading.Lock()
per_phone_locks = {}  # phone_number -> threading.Lock
per_phone_locks_lock = threading.Lock() # Lock for the per_phone_locks dict itself

# Initialize WhatsApp client
whatsapp_client = WhatsAppClient(
    phone_number_id=PHONE_NUMBER_ID,
    access_token=ACCESS_TOKEN,
    demo_mode=False  # Real mode!
)

# Verify Firebase connectivity at startup
try:
    from utils.firebase_client import get_db as _startup_get_db
    _fb_db = _startup_get_db()
    if _fb_db:
        print("Firebase: Connected")
    else:
        print("CRITICAL: Firebase NOT initialized -- leads will NOT be saved!")
        print("   Check that FIREBASE_CONFIG environment variable is set correctly.")
except Exception as e:
    print(f"CRITICAL: Firebase startup check failed: {e}")


@app.route("/", methods=["GET"])
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "bot": BOT_NAME,
        "version": "1.0",
        "message": f"🤖 {BOT_NAME} WhatsApp Bot is live!"
    })


# ========================================
# LOG DOWNLOAD ENDPOINTS (for production testing)
# ========================================

LOGS_SECRET = VERIFY_TOKEN  # Reuse the webhook verify token as auth

@app.route("/logs", methods=["GET"])
def list_logs():
    """List all log files. Auth: ?secret=YOUR_VERIFY_TOKEN"""
    if request.args.get("secret") != LOGS_SECRET:
        return "Forbidden", 403
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        return jsonify({"files": []})
    
    files = []
    for f in sorted(os.listdir(log_dir)):
        if f.endswith(".txt"):
            path = os.path.join(log_dir, f)
            files.append({
                "name": f,
                "size_bytes": os.path.getsize(path),
                "url": f"/logs/{f}?secret={LOGS_SECRET}"
            })
    return jsonify({"files": files})


@app.route("/logs/<filename>", methods=["GET"])
def download_log(filename):
    """Download a specific log file. Auth: ?secret=YOUR_VERIFY_TOKEN"""
    if request.args.get("secret") != LOGS_SECRET:
        return "Forbidden", 403
    
    # Sanitize filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        return "Bad request", 400
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    log_path = os.path.join(log_dir, filename)
    
    if not os.path.exists(log_path):
        return "Not found", 404
    
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    from flask import Response
    return Response(content, mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/logs/download-all", methods=["GET"])
def download_all_logs():
    """Download ALL log files as a single zip. Auth: ?secret=YOUR_VERIFY_TOKEN"""
    if request.args.get("secret") != LOGS_SECRET:
        return "Forbidden", 403
    
    import zipfile
    import io
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        return "No logs yet", 404
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(log_dir)):
            if f.endswith(".txt"):
                zf.write(os.path.join(log_dir, f), f)
    
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="rentbasket_logs.zip")


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    WhatsApp webhook verification (GET request).
    Meta sends this to verify your webhook URL.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    print(f"📥 Webhook verification request:")
    print(f"   Mode: {mode}")
    print(f"   Token: {token}")
    print(f"   Challenge: {challenge}")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verified successfully!")
        return challenge, 200
    
    print("❌ Webhook verification failed!")
    return "Forbidden", 403


def format_bot_response(text: str) -> str:
    """
    Apply formatting rules to bot response.
    Specifically: replace all double asterisks ** with single asterisk *.
    """
    if not text:
        return text
    # Replace ** with *
    return text.replace("**", "*")


def process_webhook_async(phone, text, sender_name, message_id, message_type, interactive_response, quoted_message_id=None, reaction=None):
    """
    Process the message logic in a background thread.
    Uses a per-phone lock to ensure messages from the same user are processed sequentially.
    """
    # 1. Get or create a lock for this specific phone number
    with per_phone_locks_lock:
        if phone not in per_phone_locks:
            per_phone_locks[phone] = threading.Lock()
        user_lock = per_phone_locks[phone]

    # 2. Acquire user_lock to ensure FIFO processing for this user
    with user_lock:
        print(f"   🔒 Processing message {message_id} for {phone} (Lock acquired)")
        try:
            # 10-Digit Normalization for RentBasket
            normalized_phone = normalize_phone(phone)
            
            # Check for pricing negotiation intent
            if is_pricing_negotiation(text):
                print(f"   💰 Pricing negotiation detected!")
                handle_pricing_negotiation(phone, sender_name, text, message_id)
                return

            # Get state within the global conversations lock
            with conversations_lock:
                if phone not in conversations:
                    conversations[phone] = create_initial_state()
                    # Restore persisted lead data (duration, name, location) from Firestore
                    conversations[phone] = restore_lead_to_state(normalized_phone, conversations[phone])
                    start_new_session(normalized_phone, sender_name)
                    print(f"   New conversation started for {normalized_phone}")
                state = conversations[phone]
            
            # Get or create DB session (use normalized phone for consistency)
            session_id = get_or_create_session(normalized_phone, sender_name)
            
            # Ensure customer name and phone are in state
            if sender_name and not state["collected_info"].get("customer_name"):
                state["collected_info"]["customer_name"] = sender_name
            
            # Always use normalized phone for state consistency
            state["collected_info"]["phone"] = normalized_phone

            # --- EARLY LEAD CREATION (safety net — runs before agent processing) ---
            try:
                if not get_lead(normalized_phone):
                    upsert_lead(normalized_phone, {
                        "name": sender_name or "New Lead",
                        "phone": normalized_phone,
                        "push_name": sender_name,
                        "lead_stage": "new"
                    })
                    print(f"   Lead created for {normalized_phone}")
            except Exception as e:
                print(f"   CRITICAL: Early lead creation failed for {normalized_phone}: {e}")

            # Capture Session Cache Facts
            is_frustrated = any(kw in text.lower() for kw in ["angry", "bad", "worst", "slow", "pathetic", "help", "not working"])
            has_media = message_type in ("image", "video", "document")
            
            update_user_facts(
                normalized_phone, 
                customer_name=sender_name,
                frustration_flag=is_frustrated,
                media_presence=has_media,
                last_msg_timestamp=time.time()
            )
            
            # Simple pincode extraction from incoming message
            import re
            pincode_match = re.search(r'\b\d{6}\b', text)
            if pincode_match:
                state["collected_info"]["pincode"] = pincode_match.group()
                print(f"   📍 Pincode {state['collected_info']['pincode']} extracted")

            # Duration extraction from incoming message
            duration_match = re.search(r'(\d+)\s*(?:months?|mo\b)', text.lower())
            if duration_match:
                dur = int(duration_match.group(1))
                if 1 <= dur <= 36:
                    state["collected_info"]["duration_months"] = dur
                    print(f"   📅 Duration {dur} months extracted")

            # Process message with the agent
            print(f"   🤖 Processing with {BOT_NAME}...")
            response, new_state = route_and_run(text, state)
            
            # Extract routing metadata for DB logging
            routing_meta = new_state.pop("_routing_meta", {})
            intent = routing_meta.get("intent")
            agent_used = routing_meta.get("agent_used")
            
            # Update state within global lock
            with conversations_lock:
                conversations[phone] = new_state
            
            # Update session in DB with latest state info
            update_session(
                session_id,
                conversation_stage=new_state.get("conversation_stage"),
                active_agent=agent_used,
                collected_info=new_state.get("collected_info"),
                needs_human=new_state.get("needs_human"),
            )
            
            # --- ANALYTICS EVENTS ---
            workflow_stage = new_state.get("collected_info", {}).get("workflow_stage")
            if workflow_stage == "ticket_logged":
                log_event(normalized_phone, "support_ticket_created", {"issue": new_state.get("support_context", {}).get("issue_type")}, session_id=session_id)
            elif workflow_stage == "escalated":
                log_event(normalized_phone, "support_escalation", {"context": new_state.get("support_context", {})}, session_id=session_id)

            # Lead stage transitions
            prev_stage = state.get("collected_info", {}).get("_last_lead_stage")
            new_lead_stage = new_state.get("collected_info", {}).get("_last_lead_stage")
            # Check Firestore lead for actual stage (set by sync_lead_data_tool)
            try:
                from utils.firebase_client import get_lead
                lead_doc = get_lead(normalized_phone)
                if lead_doc:
                    current_lead_stage = lead_doc.get("lead_stage")
                    if current_lead_stage == "qualified" and prev_stage not in ("qualified", "cart_created", "reserved", "converted"):
                        log_event(normalized_phone, "lead_qualified", {"stage": current_lead_stage}, session_id=session_id)
                    elif current_lead_stage == "cart_created" and prev_stage not in ("cart_created", "reserved", "converted"):
                        log_event(normalized_phone, "cart_created", {
                            "cart": lead_doc.get("final_cart", []),
                            "stage": current_lead_stage,
                        }, session_id=session_id)
                    # Persist observed stage into state for next turn comparison
                    new_state["collected_info"]["_last_lead_stage"] = current_lead_stage
            except Exception as _e:
                pass  # Analytics failure must never affect bot response

            
            # Apply formatting
            response = format_bot_response(response)
            
            # Split and send messages
            messages_to_send = []
            if "|||" in response:
                messages_to_send = response.split("|||")
            elif "How can I help you in making your living space more comfortable?😊" in response and "We offer Quality furniture" in response:
                temp_response = response.replace("How can I help you in making your living space more comfortable?😊", "How can I help you in making your living space more comfortable?😊|||")
                temp_response = temp_response.replace("powered by customer service which is best in the market.", "powered by customer service which is best in the market.|||")
                messages_to_send = temp_response.split("|||")
            else:
                messages_to_send = [response]
            
            # --- CUSTOM UX HANDLER FOR NEW SUPPORT STRUCTURE ---
            import utils.support_menus as sm_menus
            
            for i, msg in enumerate(messages_to_send):
                msg = msg.strip()
                if not msg: continue
                
                # Handling structured Support Lists
                if msg.startswith("[SEND_SUPPORT_LIST:"):
                    menu_key = msg.replace("[SEND_SUPPORT_LIST:", "").replace("]", "").strip()
                    menu_dict = getattr(sm_menus, menu_key, None)
                    if menu_dict:
                        whatsapp_client.send_list_message(
                            to_phone=phone,
                            body_text=menu_dict.get("body_text", "Options:"),
                            button_text=menu_dict.get("button_text", "Select"),
                            sections=menu_dict.get("sections", []),
                            header=menu_dict.get("header")
                        )
                    continue

                # Handling structured Support Buttons
                elif msg.startswith("[SEND_SUPPORT_BUTTONS:"):
                    # Format: [SEND_SUPPORT_BUTTONS:VAR_NAME|Header text|Body text|Footer text]
                    raw_data = msg.replace("[SEND_SUPPORT_BUTTONS:", "").replace("]", "").split("|")
                    var_name = raw_data[0].strip()
                    buttons_list = getattr(sm_menus, var_name, [])
                    
                    if buttons_list:
                        head = raw_data[1].strip() if len(raw_data) > 1 and raw_data[1].strip() else None
                        body = raw_data[2].strip() if len(raw_data) > 2 and raw_data[2].strip() else "Please choose an option:"
                        foot = raw_data[3].strip() if len(raw_data) > 3 and raw_data[3].strip() else None
                        
                        whatsapp_client.send_interactive_buttons(
                            to_phone=phone, body_text=body, buttons=buttons_list, header=head, footer=foot
                        )
                    continue
                
                # ── Cart Confirmation Buttons ──────────────────────────────
                elif "[SEND_CART_BUTTONS]" in msg:
                    # Send the cart text first, then send the action buttons separately
                    cart_text = msg.replace("[SEND_CART_BUTTONS]", "").strip()
                    if cart_text:
                        whatsapp_client.send_text_message(phone, cart_text, preview_url=False)
                        time.sleep(0.6)

                    # Hot-lead detection → swap primary button + add footer
                    try:
                        from utils.firebase_client import is_hot_lead
                        _hot = is_hot_lead(normalize_phone(phone))
                    except Exception:
                        _hot = False

                    if _hot:
                        primary_btn = {"id": "RESERVE_SETUP", "title": "Reserve Now"}
                        cart_footer = "Free delivery locked in for you!"
                    else:
                        primary_btn = {"id": "RESERVE_SETUP", "title": "Reserve Now"}
                        cart_footer = None

                    cart_action_buttons = [
                        primary_btn,
                        {"id": "MODIFY_CART",    "title": "Modify Cart"},
                        {"id": "TALK_TO_EXPERT", "title": "Talk to Expert"},
                    ]
                    whatsapp_client.send_interactive_buttons(
                        to_phone=phone,
                        body_text="What would you like to do?",
                        buttons=cart_action_buttons,
                        footer=cart_footer,
                    )
                    continue

                # Standard handoff handler
                elif "[SEND_HANDOFF_BUTTONS]" in msg:
                    clean_msg = msg.replace("[SEND_HANDOFF_BUTTONS]", "").strip()
                    handoff_buttons = [
                        {"id": "CALL_ME", "title": "Call me"},
                        {"id": "WHATSAPP", "title": "Chat here"}
                    ]
                    whatsapp_client.send_interactive_buttons(
                        to_phone=phone,
                        body_text=clean_msg,
                        buttons=handoff_buttons
                    )
                else:
                    # Plain text
                    whatsapp_client.send_text_message(phone, msg, preview_url="http" in msg)
                    
                if len(messages_to_send) > 1:
                    time.sleep(0.5) # Slight delay between split messages
            
            # Log turn with metadata (DB + file)
            log_response = response.replace("|||", "\n")
            log_conversation_turn(
                normalized_phone, sender_name, text, log_response,
                session_id=session_id,
                agent_used=agent_used,
                intent=intent,
                wa_message_id=message_id,
                quoted_message_id=quoted_message_id,
                reaction_emoji=reaction.get("emoji") if reaction else None
            )
            print(f"   ✅ Response sent successfully for {phone}")

        except Exception as e:
            print(f"❌ Error in background process for {phone}: {e}")
            import traceback
            traceback.print_exc()


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Handle incoming WhatsApp messages (POST request).
    """
    try:
        payload = request.get_json()
        
        # Parse the webhook payload
        message_data = parse_whatsapp_webhook(payload)
        
        if not message_data:
            # Not a message event (could be status update, etc.)
            return jsonify({"status": "no_message"}), 200
        
        phone = message_data["from_phone"]
        text = message_data.get("text", "")
        message_id = message_data.get("message_id")
        sender_name = message_data.get("sender_name", phone)
        message_type = message_data.get("type")
        interactive_response = message_data.get("interactive")
        
        # 1. Deduplication check (Thread-safe)
        with conversations_lock:
            now = time.time()
            if message_id in processed_ids_dict:
                print(f"   Skipping duplicate message: {message_id}")
                return jsonify({"status": "duplicate"}), 200

            # Add to cache
            processed_ids_dict[message_id] = now

            # Prune expired entries
            if len(processed_ids_dict) > MAX_CACHE_SIZE:
                expired = [k for k, v in processed_ids_dict.items() if now - v > CACHE_EXPIRY_SECONDS]
                for k in expired:
                    processed_ids_dict.pop(k, None)

        print(f"\n💬 Message from {sender_name} ({phone}):")
        print(f"   Type: {message_type}")
        print(f"   Text: {text}")
        
        # Send read receipt first (marks message with blue ticks)
        if message_id:
            whatsapp_client.send_read_and_typing_indicator(message_id)
        
        # Handle simple interactive button responses synchronously if quick
        if message_type == "interactive" and interactive_response:
            return handle_interactive_response(phone, sender_name, interactive_response, message_id)

        if message_type == "audio":
            browse_active = session_context.get(phone, {}).get("browse_mode")
            sales_active = session_context.get(phone, {}).get("sales_mode")
            media_id = message_data.get("media_id")
            if sales_active:
                thread = threading.Thread(
                    target=process_sales_audio_async,
                    args=(phone, sender_name, media_id, message_id)
                )
                thread.start()
                return jsonify({"status": "processing_sales_audio"}), 200
            if browse_active:
                thread = threading.Thread(
                    target=process_browse_audio_async,
                    args=(phone, sender_name, media_id, message_id)
                )
                thread.start()
                return jsonify({"status": "processing_browse_audio"}), 200

        if not text and message_type in ("image", "video", "document"):
            return handle_media_message(
                phone, sender_name, message_type,
                message_data.get("media_id"),
                message_data.get("media_caption", ""),
                message_id
            )

        if not text:
            print("   ⚠️ Skipping unsupported message type")
            return jsonify({"status": "non_text_message"}), 200
            
        # 2. START BACKGROUND PROCESSING
        # We start a thread to do the heavy lifting (AI + multiple tool calls)
        # and return 200 OK to WhatsApp immediately to stop retries.
        
        # Check for Fallback before background thread
        if text.lower() in ["help", "option", "options", "menu"]:
             return handle_fallback(phone, sender_name)

        # Check for Greeting — send interactive buttons directly, skip the LLM
        if is_greeting(text):
            return handle_greeting(phone, sender_name)

        # Check for SALES keyword — activate sales team cart-building mode
        if text.strip().upper() == "SALES":
            session_context[phone] = {"sales_mode": True, "sender_name": sender_name}
            whatsapp_client.send_text_message(
                phone,
                "Share me the cart on voice message or just type it, I will create a tentative cart message for you!"
            )
            # Log activation
            normalized_phone = normalize_phone(phone)
            session_id = get_or_create_session(normalized_phone, sender_name)
            log_event(normalized_phone, "sales_mode_activated", {}, session_id=session_id)
            return jsonify({"status": "ok", "action": "sales_mode_activated"}), 200

        browse_ctx = session_context.get(phone, {})
        if browse_ctx.get("browse_mode"):
            if _handle_browse_products_text(phone, sender_name, text, message_id):
                return jsonify({"status": "processing_browse_text"}), 200

        # SALES mode text input — build cart from text instead of routing to LLM
        if session_context.get(phone, {}).get("sales_mode"):
            thread = threading.Thread(
                target=process_sales_text_async,
                args=(phone, sender_name, text, message_id)
            )
            thread.start()
            return jsonify({"status": "processing_sales_text"}), 200

        # ── Direct product request interception ──────────────────
        # If user sends "Study Chair and table I want" (product keywords detected),
        # enter a direct-request flow instead of routing to the LLM agent.
        if _try_direct_product_request(phone, sender_name, text):
            return jsonify({"status": "processing_direct_request"}), 200

        thread = threading.Thread(
            target=process_webhook_async,
            args=(
                phone, text, sender_name, message_id, message_type,
                interactive_response, message_data.get("quoted_message_id"),
                message_data.get("reaction")
            )
        )
        thread.start()

        return jsonify({"status": "processing"}), 200
        
    except Exception as e:
        print(f"❌ Error handling webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


def handle_pricing_negotiation(phone: str, sender_name: str, text: str, message_id: str):
    """
    Handle pricing negotiation by sending interactive buttons.
    """
    print(f"   🔔 Sending interactive buttons for pricing negotiation...")
    
    # Store context for when user responds
    session_context[phone] = {
        "handoff_needed": True,
        "intent": "pricing_support",
        "last_message": text,
        "sender_name": sender_name
    }
    
    # Send interactive buttons (WhatsApp title limit is 20 chars)
    buttons = [
        {"id": "BUDGET_OPTIONS", "title": "Budget Options"},
        {"id": "LONGER_TENURE", "title": "Longer Tenures"},
        {"id": "TALK_TO_SALES", "title": "Talk to Sales"}
    ]
    
    body_text = """I completely understand — let me help you find the absolute best value for your budget.

How would you like to proceed?"""

    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text=body_text,
        buttons=buttons,
        header="Best Price Request",
        footer=f"Sales: {SALES_PHONE_GURGAON}"
    )
    
    # Log the interaction
    session_id = get_or_create_session(phone, sender_name)
    log_conversation_turn(phone, sender_name, text, "[Sent interactive pricing buttons]",
                          session_id=session_id)
    log_event(phone, "pricing_negotiation", {"message": text}, session_id=session_id)
    
    print(f"   ✅ Interactive buttons sent!")
    return jsonify({"status": "ok", "action": "pricing_negotiation"}), 200


def handle_interactive_response(phone: str, sender_name: str, interactive: dict, message_id: str):
    """
    Handle user's response to interactive buttons.
    """
    try:
        # Get reply ID from response (button_reply OR list_reply)
        button_reply = interactive.get("button_reply", {})
        list_reply = interactive.get("list_reply", {})
        
        # Unify: list selections come as list_reply, buttons as button_reply
        reply = button_reply or list_reply
        button_id = reply.get("id", "")
        button_title = reply.get("title", "")
        
        print(f"   🔘 Interactive reply: {button_id} ({button_title})")
        
        # Get stored context
        context = session_context.get(phone, {})
        
        if button_id in ("TALK_TO_TEAM", "CALL_ME", "TALK_TO_SALES"):
            # Handle callback request
            response = f"""*Callback Confirmed!*

Our sales team will call you within *15 minutes* to discuss your requirements.

*Your callback is queued!*
• Priority: High
• Estimated wait: 10-15 mins

If urgent, call directly:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

Thank you for choosing RentBasket!"""
            whatsapp_client.send_text_message(phone, response)
            print(f"   📋 [Placeholder] Would create sales lead for {phone}")
            return jsonify({"status": "ok", "action": "callback_queued"}), 200
            
        elif button_id == "TRY_AGAIN":
            response = "Sure! Let's try again. What are you looking to rent today? You can just send me a single word like 'Sofa' or 'Fridge'."
            whatsapp_client.send_text_message(phone, response)
            return jsonify({"status": "ok", "action": "try_again"}), 200
            
        elif button_id == "BUDGET_OPTIONS":
            # Route directly to agent — bypass pricing negotiation check
            print(f"   User requested budget options. Routing to agent directly.")
            _text = "Show me more affordable alternatives and budget-friendly options"

            def _route_budget_options():
                with per_phone_locks_lock:
                    if phone not in per_phone_locks:
                        per_phone_locks[phone] = threading.Lock()
                    user_lock = per_phone_locks[phone]
                with user_lock:
                    try:
                        normalized_phone = normalize_phone(phone)
                        with conversations_lock:
                            if phone not in conversations:
                                conversations[phone] = create_initial_state()
                                conversations[phone] = restore_lead_to_state(normalized_phone, conversations[phone])
                            state = conversations[phone]
                        state["collected_info"]["phone"] = normalized_phone
                        if sender_name and not state["collected_info"].get("customer_name"):
                            state["collected_info"]["customer_name"] = sender_name

                        response, new_state = route_and_run(_text, state)
                        new_state.pop("_routing_meta", None)
                        with conversations_lock:
                            conversations[phone] = new_state
                        response = format_bot_response(response)
                        for msg in response.split("|||"):
                            msg = msg.strip()
                            if msg:
                                whatsapp_client.send_text_message(phone, msg, preview_url="http" in msg)
                                time.sleep(0.3)
                    except Exception as e:
                        print(f"Error routing budget options for {phone}: {e}")
                        whatsapp_client.send_text_message(phone, "Let me find budget-friendly options for you. What items are you looking for?")

            thread = threading.Thread(target=_route_budget_options)
            thread.start()
            return jsonify({"status": "ok", "action": "route_to_agent_budget"}), 200
            
        elif button_id == "LONGER_TENURE":
            # Route directly to agent — bypass pricing negotiation check
            print(f"   User requested longer tenures. Routing to agent directly.")
            _text = "Show me prices for longer rental durations like 6 months and 12 months"

            def _route_longer_tenure():
                with per_phone_locks_lock:
                    if phone not in per_phone_locks:
                        per_phone_locks[phone] = threading.Lock()
                    user_lock = per_phone_locks[phone]
                with user_lock:
                    try:
                        normalized_phone = normalize_phone(phone)
                        with conversations_lock:
                            if phone not in conversations:
                                conversations[phone] = create_initial_state()
                                conversations[phone] = restore_lead_to_state(normalized_phone, conversations[phone])
                            state = conversations[phone]
                        state["collected_info"]["phone"] = normalized_phone
                        if sender_name and not state["collected_info"].get("customer_name"):
                            state["collected_info"]["customer_name"] = sender_name

                        response, new_state = route_and_run(_text, state)
                        new_state.pop("_routing_meta", None)
                        with conversations_lock:
                            conversations[phone] = new_state
                        response = format_bot_response(response)
                        for msg in response.split("|||"):
                            msg = msg.strip()
                            if msg:
                                whatsapp_client.send_text_message(phone, msg, preview_url="http" in msg)
                                time.sleep(0.3)
                    except Exception as e:
                        print(f"Error routing longer tenure for {phone}: {e}")
                        whatsapp_client.send_text_message(phone, "Let me check the best prices for longer durations. Please share how many months you need (e.g. 6 or 12 months).")

            thread = threading.Thread(target=_route_longer_tenure)
            thread.start()
            return jsonify({"status": "ok", "action": "route_to_agent_tenure"}), 200
            
        elif button_id in ("BROWSE_FURNITURE", "BROWSE_APPLIANCES"):
            # Legacy greeting buttons — route into the browse flow
            _save_browse_lead_data(normalize_phone(phone), {"lead_stage": "browse_started"})
            _send_duration_buttons(phone)
            return jsonify({"status": "ok", "action": "browse_products_started"}), 200

        elif button_id == "COMPLETE_HOME_SETUP":
            # Route into browse flow for complete setup
            _save_browse_lead_data(normalize_phone(phone), {"lead_stage": "browse_started"})
            _send_duration_buttons(phone)
            return jsonify({"status": "ok", "action": "complete_home_setup"}), 200

        elif button_id.startswith("CAT_"):
            # Map category button IDs to better search queries for the agent
            cat_query_map = {
                "CAT_BEDS": "Show me beds and mattresses options with prices",
                "CAT_SOFAS": "Show me sofa options with prices",
                "CAT_DINING": "Show me dining table options with prices",
                "CAT_WFH": "Show me study table, study chair, and office desk options with prices",
                "CAT_ALL_FURNITURE": "Show me all furniture options with prices",
                "CAT_FRIDGE": "Show me refrigerator/fridge options with prices",
                "CAT_WASHING": "Show me washing machine options with prices",
                "CAT_AC": "Show me air conditioner/AC options with prices",
                "CAT_RO": "Show me water purifier options with prices",
                "CAT_ALL_APPLIANCES": "Show me all appliance options with prices",
            }
            category_text = cat_query_map.get(button_id, f"Show me {button_title} options with prices")
            print(f"   List item selected: {button_title}. Routing to agent.")

            thread = threading.Thread(
                target=process_webhook_async,
                args=(phone, category_text, sender_name, message_id, "text", None)
            )
            thread.start()
            return jsonify({"status": "ok", "action": "list_route_to_agent"}), 200

        # ── Cart Confirmation Buttons ──────────────────────────────────────────

        elif button_id == "RESERVE_SETUP":
            # Primary CTA — close the deal with referral discount
            normalized = normalize_phone(phone)
            try:
                from utils.firebase_client import upsert_lead
                upsert_lead(normalized, {
                    "lead_stage": "reserved",
                    "conversion_intent": "high",
                })
            except Exception as e:
                print(f"   Lead update failed (non-fatal): {e}")

            session_id = get_or_create_session(normalized, sender_name)
            log_event(normalized, "cart_reserved", {"button": button_id}, session_id=session_id)

            # Route to the agent so it can ask for pincode -> check serviceability -> send cart link
            print(f"   Reserve requested by {phone}. Routing to agent for location check.")
            thread = threading.Thread(
                target=process_webhook_async,
                args=(phone, "I want to reserve and proceed with the order", sender_name, message_id, "text", None)
            )
            thread.start()
            return jsonify({"status": "ok", "action": "reserved"}), 200

        elif button_id == "MODIFY_CART":
            normalized = normalize_phone(phone)
            try:
                from utils.firebase_client import upsert_lead
                upsert_lead(normalized, {"lead_stage": "cart_modification"})
            except Exception as e:
                print(f"   Lead update failed (non-fatal): {e}")

            ctx = session_context.get(phone, {})
            last_cart = ctx.get("last_cart", [])

            # If we have a SALES-mode cart, stay in SALES modify mode
            if last_cart:
                ctx["sales_mode"] = True
                ctx["sales_modify_mode"] = True
                # Show current cart summary so user knows what to modify
                item_names = [f"{it.get('qty', 1)}x {it.get('product_name', it.get('name', '?'))}" for it in last_cart if it.get("matched")]
                summary = ", ".join(item_names) if item_names else "your current items"
                whatsapp_client.send_text_message(
                    phone,
                    f"Your current cart: {summary}\n\n"
                    f"Tell me what to change, for example:\n"
                    f"- \"Remove the mattress\"\n"
                    f"- \"Add 1 study chair\"\n"
                    f"- \"Change bed to queen bed\"\n"
                    f"Or send a completely new list to replace the cart."
                )
                print(f"   Cart modification requested by {phone}. Staying in SALES modify mode.")
                return jsonify({"status": "ok", "action": "cart_modification_sales"}), 200

            # No SALES cart — route to the agent
            print(f"   Cart modification requested by {phone}. Routing to sales agent.")
            thread = threading.Thread(
                target=process_webhook_async,
                args=(
                    phone,
                    "I want to modify my cart. What are my options?",
                    sender_name, message_id, "text", None,
                )
            )
            thread.start()
            return jsonify({"status": "ok", "action": "cart_modification"}), 200

        elif button_id == "TALK_TO_EXPERT":
            # 👨‍💼  High-intent human handoff
            normalized = normalize_phone(phone)
            try:
                from utils.firebase_client import upsert_lead
                upsert_lead(normalized, {
                    "lead_stage": "sales_handoff",
                    "human_handover": True,
                })
            except Exception as e:
                print(f"   ⚠️ Lead update failed (non-fatal): {e}")

            session_id = get_or_create_session(phone, sender_name)
            log_event(phone, "expert_requested", {"phone": normalized}, session_id=session_id)

            response = (
                f"*Connecting you to a sales expert!*\n\n"
                f"Our specialist will reach out within *30 minutes*.\n\n"
                f"Your cart is saved — they'll have all your details already.\n\n"
                f"For urgent queries:\n"
                f"• Gurgaon: {SALES_PHONE_GURGAON}\n"
                f"• Noida: {SALES_PHONE_NOIDA}"
            )
            whatsapp_client.send_text_message(phone, response)
            print(f"   👨‍💼 Expert requested for {phone}")
            return jsonify({"status": "ok", "action": "expert_requested"}), 200

        # ── Upfront Payment (SALES mode) ──────────────────────────────
        elif button_id == "UPFRONT_PAYMENT":
            ctx = session_context.get(phone, {})
            last_cart = ctx.get("last_cart", [])
            duration = ctx.get("last_duration", 12)

            if not last_cart:
                whatsapp_client.send_text_message(phone, "No cart found. Please send your product list first.")
                return jsonify({"status": "ok", "action": "no_cart"}), 200

            # Determine upfront discount: 10% for 12mo, 5% for 6mo
            upfront_pct = 10 if duration >= 12 else 5

            lines = []
            lines.append(f"*Upfront Payment Option* (Extra {upfront_pct}% off!)")
            lines.append(f"Duration: {duration} months\n")

            total_monthly = 0
            total_upfront_monthly = 0
            for i, item in enumerate(last_cart, 1):
                pid_str = f"#{item['product_id']}" if item['product_id'] else "(not found)"
                regular_rent = item['rent']
                if item['original_rent']:
                    upfront_rent = apply_discount(item['original_rent'], upfront=True, upfront_percent=upfront_pct)
                else:
                    upfront_rent = 0
                lines.append(f"{i}. {item['product_name']} {pid_str}")
                lines.append(f"   Qty: {item['qty']} | ~\u20b9{regular_rent:,}/mo~ \u20b9{upfront_rent:,}/mo + GST")
                total_monthly += regular_rent * item['qty']
                total_upfront_monthly += upfront_rent * item['qty']

            gst_regular = int(round(total_monthly * 0.18))
            gst_upfront = int(round(total_upfront_monthly * 0.18))
            grand_regular = total_monthly + gst_regular
            grand_upfront = total_upfront_monthly + gst_upfront
            total_upfront_total = grand_upfront * duration
            savings = (grand_regular - grand_upfront) * duration

            lines.append(f"\n*Regular: \u20b9{grand_regular:,}/mo*")
            lines.append(f"*Upfront: \u20b9{grand_upfront:,}/mo*")
            lines.append(f"\n*Total Upfront Payment: \u20b9{total_upfront_total:,}* for {duration} months")
            lines.append(f"You save: \u20b9{savings:,} over {duration} months!")
            lines.append(f"\n_Pay upfront and enjoy extra {upfront_pct}% discount on your entire rental._")

            whatsapp_client.send_text_message(phone, "\n".join(lines))

            normalized = normalize_phone(phone)
            session_id = get_or_create_session(normalized, sender_name)
            log_event(normalized, "upfront_payment_shown", {"duration": duration, "upfront_pct": upfront_pct}, session_id=session_id)
            return jsonify({"status": "ok", "action": "upfront_payment"}), 200

        # ── Final Link (SALES mode) ───────────────────────────────
        elif button_id == "FINAL_LINK":
            ctx = session_context.get(phone, {})
            last_cart = ctx.get("last_cart", [])
            duration = ctx.get("last_duration", 12)

            matched_items = [it for it in last_cart if it.get("matched") and it.get("product_id")]
            if not matched_items:
                whatsapp_client.send_text_message(
                    phone,
                    "No valid products in your cart to generate a link. Please send your product list again."
                )
                return jsonify({"status": "ok", "action": "no_cart_for_link"}), 200

            # Build cart link using the same logic as browse flow
            cart_payload = []
            for item in matched_items:
                product = None
                try:
                    product = get_product_by_id(item["product_id"])
                except Exception:
                    pass
                amenity_type_id = item["product_id"]
                if isinstance(product, dict):
                    amenity_type_id = (
                        product.get("amenity_type_id")
                        or product.get("amenity_id")
                        or product.get("type_id")
                        or product.get("id")
                        or item["product_id"]
                    )
                cart_payload.append({
                    "amenity_type_id": int(amenity_type_id),
                    "count": int(item.get("qty", 1)),
                    "duration": int(duration),
                })

            encoded_items = quote(json.dumps(cart_payload, separators=(",", ":"), ensure_ascii=False), safe=":,")
            cart_link = f"{BROWSE_PRODUCTS_BASE_URL}?token={RENTBASKET_JWT}&referral_code={BROWSE_PRODUCTS_REFERRAL_CODE}&items={encoded_items}"

            whatsapp_client.send_text_message(
                phone,
                f"Here is your cart link with 5% additional discount for using our WhatsApp Bot:\n{cart_link}",
                preview_url=True,
            )

            normalized = normalize_phone(phone)
            session_id = get_or_create_session(normalized, sender_name)
            log_event(normalized, "final_link_sent", {"duration": duration, "items": len(matched_items)}, session_id=session_id)

            # Clear sales mode after final link
            ctx.pop("sales_mode", None)
            return jsonify({"status": "ok", "action": "final_link_sent"}), 200

        # ── Informational Flow Buttons ─────────────────────────────────
        elif button_id == "BROWSE_PRODUCTS":
            ctx = _browse_context(phone)
            existing_duration = ctx.get("browse_duration")
            if existing_duration:
                # Duration already set — go straight to room selection (Browse More flow)
                _set_browse_context(phone, browse_mode=True)
                _send_room_selection(phone)
            else:
                normalized = normalize_phone(phone)
                _save_browse_lead_data(normalized, {"lead_stage": "browse_started"})
                _send_duration_buttons(phone)
            return jsonify({"status": "ok", "action": "browse_products_started"}), 200

        elif button_id in ("BROWSE_DUR_3", "BROWSE_DUR_6", "BROWSE_DUR_12"):
            dur_map = {"BROWSE_DUR_3": 3, "BROWSE_DUR_6": 6, "BROWSE_DUR_12": 12}
            duration = dur_map[button_id]
            ctx = _set_browse_context(phone, browse_mode=True, browse_duration=duration)
            _save_browse_lead_data(normalize_phone(phone), {"duration_months": duration, "lead_stage": "browse_duration_set"})

            # If this is a direct-request flow, show product options instead of room selection
            if ctx.get("direct_request"):
                ctx["browse_step"] = "direct_await_selection"
                _send_direct_request_options(phone)
                return jsonify({"status": "ok", "action": f"direct_duration_{duration}"}), 200

            ctx["browse_step"] = "await_room"
            whatsapp_client.send_text_message(
                phone,
                f"Got it, {duration} months. Now pick a room to start browsing.",
                preview_url=False,
            )
            time.sleep(0.3)
            _send_room_selection(phone)
            return jsonify({"status": "ok", "action": f"browse_duration_{duration}"}), 200

        # ── Room-based browse hierarchy ─────────────────────────────
        elif button_id.startswith("ROOM_"):
            if button_id == "ROOM_1BHK":
                _send_1bhk_package_buttons(phone)
            else:
                _send_subcategory_selection(phone, button_id)
            return jsonify({"status": "ok", "action": "room_selected"}), 200

        elif button_id.startswith("SUBCAT_"):
            room_id = _browse_context(phone).get("browse_room", "")
            _send_variant_list(phone, room_id, button_id)
            return jsonify({"status": "ok", "action": "subcategory_selected"}), 200

        elif button_id.startswith("PKG_"):
            thread = threading.Thread(
                target=_handle_1bhk_package_selection,
                args=(phone, button_id, sender_name),
            )
            thread.start()
            return jsonify({"status": "ok", "action": "package_selected"}), 200

        elif button_id == "BROWSE_BACK_ROOM":
            _send_room_selection(phone)
            return jsonify({"status": "ok", "action": "back_to_rooms"}), 200

        elif button_id == "BROWSE_BACK_SUBCAT":
            room_id = _browse_context(phone).get("browse_room", "")
            if room_id == "ROOM_1BHK":
                _send_1bhk_package_buttons(phone)
            elif room_id:
                _send_subcategory_selection(phone, room_id)
            else:
                _send_room_selection(phone)
            return jsonify({"status": "ok", "action": "back_to_subcategories"}), 200

        elif button_id.startswith("BROWSE_ITEM_"):
            # User tapped a product variant from the list — add to cart
            try:
                product_id = int(button_id.split("_")[-1])
            except (ValueError, IndexError):
                whatsapp_client.send_text_message(phone, "Could not identify that product. Please try again.")
                return jsonify({"status": "ok", "action": "browse_item_invalid"}), 200
            thread = threading.Thread(
                target=_handle_browse_item_selection,
                args=(phone, sender_name, product_id),
            )
            thread.start()
            return jsonify({"status": "ok", "action": "browse_item_selected"}), 200

        elif button_id in ("BROWSE_SHOW_DETAILS", "SHOW_FULL_DETAILS"):
            _send_browse_full_details(phone, sender_name)
            return jsonify({"status": "ok", "action": "browse_show_details"}), 200

        elif button_id == "BROWSE_CHECKOUT":
            # Ask for delivery location before sending checkout link
            ctx = _set_browse_context(phone, browse_step="await_checkout_location")
            browse_quote = ctx.get("last_browse_quote", {})
            if not browse_quote.get("items"):
                whatsapp_client.send_text_message(phone, "No items in your cart yet. Please browse and add items first.")
                return jsonify({"status": "ok", "action": "browse_checkout_empty"}), 200
            whatsapp_client.send_text_message(
                phone,
                "Great, let us check if we can deliver to your location.\n\n"
                "Please share your delivery location and make sure to include the *pincode (6-digit number)*.\n\n"
                "Example: Sector 52, Gurugram 122003",
                preview_url=False,
            )
            return jsonify({"status": "ok", "action": "browse_checkout_ask_location"}), 200

        elif button_id == "BROWSE_MODIFY_CART":
            ctx = _browse_context(phone)
            browse_quote = ctx.get("last_browse_quote", {})
            items = browse_quote.get("items", [])

            if items:
                # Show current cart with numbered items and modify instructions
                ctx["browse_modify_mode"] = True
                ctx["browse_step"] = "browse_modify"
                item_lines = []
                for i, it in enumerate(items, 1):
                    name = it.get("product_name") or it.get("name") or "Product"
                    qty = int(it.get("qty", 1))
                    rent = int(it.get("rent") or 0)
                    item_lines.append(f"{i}. {name} (x{qty}) - Rs. {rent:,}/mo")

                whatsapp_client.send_text_message(
                    phone,
                    f"*Your current cart:*\n" + "\n".join(item_lines) + "\n\n"
                    f"Tell me what to change:\n"
                    f"- \"Remove the fridge\"\n"
                    f"- \"Add a study table\"\n"
                    f"- Or reply with an item number to remove it (e.g., 2)\n\n"
                    f"Or browse more products to add:",
                    preview_url=False,
                )
                time.sleep(0.3)
                buttons = [
                    {"id": "BROWSE_PRODUCTS", "title": "Browse More"},
                    {"id": "BROWSE_SHOW_DETAILS", "title": "View Cart"},
                ]
                whatsapp_client.send_interactive_buttons(
                    to_phone=phone,
                    body_text="Or pick an option:",
                    buttons=buttons,
                    header=BROWSE_FLOW_HEADER,
                )
            else:
                _send_room_selection(phone)
            return jsonify({"status": "ok", "action": "browse_modify_cart"}), 200

        elif button_id in ("BROWSE_CUSTOMER_REVIEWS", "CUSTOMER_REVIEWS"):
            # Send reviews as plain text (exceeds 1024 char interactive limit)
            whatsapp_client.send_text_message(phone, LATEST_REVIEWS_TEXT, preview_url=True)
            time.sleep(0.3)
            has_cart = bool(_browse_context(phone).get("last_browse_quote", {}).get("items"))
            if has_cart:
                follow_buttons = [
                    {"id": "BROWSE_SHOW_DETAILS", "title": "View Cart"},
                    {"id": "BROWSE_PRODUCTS", "title": "Browse More"},
                ]
            else:
                follow_buttons = [
                    {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
                ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text="What would you like to do next?",
                buttons=follow_buttons,
                header="Customer Reviews",
            )
            return jsonify({"status": "ok", "action": "browse_customer_reviews"}), 200

        elif button_id == "HOW_RENTING_WORKS":
            follow_buttons = [
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
                {"id": "WHY_RENTBASKET", "title": "Why RentBasket?"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text=HOW_RENTING_WORKS_TEXT,
                buttons=follow_buttons,
            )
            return jsonify({"status": "ok", "action": "how_renting_works"}), 200

        elif button_id == "WHY_RENTBASKET":
            follow_buttons = [
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
                {"id": "LATEST_REVIEWS", "title": "Latest 5 Reviews"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text=WHY_RENTBASKET_TEXT,
                buttons=follow_buttons,
            )
            return jsonify({"status": "ok", "action": "why_rentbasket"}), 200

        elif button_id == "LATEST_REVIEWS":
            # Send reviews as plain text (exceeds 1024 char interactive limit)
            whatsapp_client.send_text_message(phone, LATEST_REVIEWS_TEXT, preview_url=True)
            time.sleep(0.3)
            follow_buttons = [
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text="What would you like to do next?",
                buttons=follow_buttons,
            )
            return jsonify({"status": "ok", "action": "latest_reviews"}), 200

        else:
            # Unknown button — route to the LLM agent with the button title as context
            print(f"   Unknown button ID: {button_id}. Routing to agent with title: {button_title}")
            if button_title:
                thread = threading.Thread(
                    target=process_webhook_async,
                    args=(phone, button_title, sender_name, message_id, "text", None)
                )
                thread.start()
            else:
                whatsapp_client.send_text_message(phone, "How can I help you today? Tell me what you are looking to rent.")
            return jsonify({"status": "ok", "button": button_id}), 200
        
    except Exception as e:
        print(f"   ⚠️ Error handling interactive response: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def handle_media_message(phone: str, sender_name: str, media_type: str, media_id: str, caption: str, message_id: str):
    """
    Handle incoming media (image, video, document, audio).
    - Acknowledges receipt immediately.
    - Tags media_id to the active session and lead/ticket in Firestore.
    - Routes based on customer status:
        * active_customer  → likely support evidence; attach to ticket context.
        * lead / unknown   → likely a room photo or product inquiry; pass to sales flow.
    """
    print(f"   📎 Media received: type={media_type}, id={media_id}, caption={caption!r}")

    normalized_phone = normalize_phone(phone)
    session_id = get_or_create_session(phone, sender_name)

    # Acknowledge receipt
    type_label = {"image": "photo", "video": "video", "document": "document", "audio": "voice message"}.get(media_type, "file")
    ack_text = f"Got your {type_label}! I've noted it on your case."

    # Look up customer status from in-memory state
    with conversations_lock:
        state = conversations.get(phone)
    customer_status = (state or {}).get("collected_info", {}).get("customer_status", "unknown")

    if customer_status in ("active_customer", "past_customer"):
        # Attach to support ticket context
        ack_text = (
            f"Got your {type_label}!\n"
            f"I've attached it to your support case. Our team will review it shortly.\n\n"
            f"Is there anything else you'd like to describe about the issue?"
        )
        # Log media reference in Firestore ticket context via analytics
        log_event(phone, "media_received", {
            "media_type": media_type,
            "media_id": media_id,
            "caption": caption,
            "context": "support_evidence",
        }, session_id=session_id)
    else:
        # Lead / unknown — treat as room photo or product reference
        ack_text = (
            f"Thanks for sharing that {type_label}!\n"
            f"I'll use this to help find the best options for you.\n\n"
            f"Could you tell me a bit more about what you're looking for?"
        )
        log_event(phone, "media_received", {
            "media_type": media_type,
            "media_id": media_id,
            "caption": caption,
            "context": "sales_inquiry",
        }, session_id=session_id)

        # Update lead with media flag
        try:
            from utils.firebase_client import upsert_lead
            upsert_lead(normalized_phone, {"has_media": True, "media_ref": media_id})
        except Exception as e:
            print(f"   ⚠️ Lead media update failed (non-fatal): {e}")

    # Log to conversation
    log_conversation_turn(
        phone, sender_name,
        f"[{media_type.upper()} id={media_id} caption={caption!r}]",
        ack_text,
        session_id=session_id,
        agent_used="media_handler",
    )

    whatsapp_client.send_text_message(phone, ack_text)
    print(f"   ✅ Media acknowledged for {phone}")
    return jsonify({"status": "ok", "action": "media_handled"}), 200


def handle_fallback(phone: str, sender_name: str):
    """Send fallback message with dynamic examples."""
    examples = get_next_fallback_examples()
    response = f"""Oops! I'm still learning and didn't quite catch that.

You can try asking things like:

{examples}

Or choose how you'd like to proceed:"""
    
    fallback_buttons = [
        {"id": "TRY_AGAIN", "title": "Try Again"},
        {"id": "TALK_TO_TEAM", "title": "Talk to Team"}
    ]
    
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text=response,
        buttons=fallback_buttons
    )
    
    # Log the interaction
    session_id = get_or_create_session(phone, sender_name)
    log_conversation_turn(phone, sender_name, "[FALLBACK TRIGGERED]", response,
                          session_id=session_id)
    
    return jsonify({"status": "ok", "action": "fallback"}), 200


def parse_whatsapp_webhook(payload: dict) -> dict:
    """
    Parse incoming WhatsApp webhook payload.
    
    Returns message data or None if not a message event.
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        # Get messages array
        messages = value.get("messages", [])
        if not messages:
            return None
        
        message = messages[0]
        
        # Get contact info
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}
        
        # Handle different message types
        msg_type = message.get("type")
        text = None
        interactive = None
        reaction = None
        context_id = message.get("context", {}).get("id")
        
        media_id = None
        media_caption = None

        if msg_type == "text":
            text = message.get("text", {}).get("body")
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
        elif msg_type == "reaction":
            reaction = message.get("reaction", {})
            text = f"[Reaction: {reaction.get('emoji')}]"
        elif msg_type in ("image", "video", "document", "audio"):
            media_obj = message.get(msg_type, {})
            media_id = media_obj.get("id")
            media_caption = media_obj.get("caption", "")
            # Use caption as text if provided, else a placeholder
            text = media_caption if media_caption else f"[{msg_type.capitalize()} received]"

        return {
            "message_id": message.get("id"),
            "from_phone": message.get("from"),
            "sender_name": contact.get("profile", {}).get("name", ""),
            "timestamp": message.get("timestamp"),
            "type": msg_type,
            "text": text,
            "interactive": interactive,
            "reaction": reaction,
            "quoted_message_id": context_id,
            "media_id": media_id,
            "media_caption": media_caption,
        }
        
    except Exception as e:
        print(f"⚠️ Error parsing webhook: {e}")
        return None


# ========================================
# MAIN
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{BOT_NAME} WhatsApp Webhook Server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    
    args = parser.parse_args()
    
    # Render injects PORT env var; fall back to --port arg
    port = int(os.environ.get("PORT", args.port))
    
    print("\n" + "="*60)
    print(f"  🤖 {BOT_NAME} - WhatsApp Webhook Server")
    print("="*60)
    print(f"\n📍 Server running on: http://0.0.0.0:{port}")
    print(f"📍 Webhook URL: http://localhost:{port}/webhook")
    print("\n" + "-"*60 + "\n")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
