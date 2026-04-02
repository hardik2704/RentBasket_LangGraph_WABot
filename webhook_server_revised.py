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

from config import BOT_NAME, SALES_PHONE_GURGAON, SALES_PHONE_NOIDA, KU_REFERRAL_LINK
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
    """Check if message indicates pricing negotiation intent."""
    text_lower = text.lower()
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
    "\u2b50 Latest Customer Experiences with RentBasket \u2b50\n\n"
    "Abhinandh Prakash \u2b50\u2b50\u2b50\u2b50\u2b50 \u2022\n"
    "4 weeks ago\n\n"
    "\"Rented a fridge, bed, and sofa. The quality is excellent and Raj provided stellar service "
    "from start to finish. Very happy!\"\n\n"                       
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Samriddhi Kakkar \u2b50\u2b50\u2b50\u2b50\u2b50 \u2022\n"
    "6 weeks ago\n\n"
    "\"Renting since 2024. Great quality products and the service is incredibly quick. "
    "Highly recommend their washing machines and ACs.\"\n\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Nitu Kumari \u2b50\u2b50\u2b50\u2b50\u2b50 \u2022\n"
    "7 weeks ago\n\n"
    "\"Had a great experience for 3 years! Any issue and they are just one call away. "
    "Must recommend for anyone looking for reliability.\"\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Vivek Singh \u2b50\u2b50\u2b50\u2b50\u2b50 \u2022\n"
    "7 weeks ago\n\n"
    "\"Half my home is furnished by RentBasket. Most cost-efficient and quality products "
    "in the market. The transaction was seamless.\"\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "Shivam Sood \u2b50\u2b50\u2b50\u2b50\u2b50 \u2022\n"
    "2 weeks ago\n\n"
    "\"Very prompt service, delivery, and installation. A truly hassle-free experience!\"\n"
    "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    "\U0001f680 Comfort On Rent, Happiness Delivered."
)

# ========================================
# BROWSE PRODUCTS FLOW
# ========================================

BROWSE_PRODUCTS_OCCASION = os.getenv("BROWSE_PRODUCTS_OCCASION", "heavy discount offers")
BROWSE_PRODUCTS_REFERRAL_CODE = os.getenv("BROWSE_PRODUCTS_REFERRAL_CODE", "ATFU1NTg5")
BROWSE_PRODUCTS_BASE_URL = os.getenv(
    "BROWSE_PRODUCTS_BASE_URL",
    "https://testqr.rentbasket.com/lead-shopping",
)

BROWSE_FLOW_HEADER = "Browse Products"

BROWSE_CATEGORY_SECTIONS = [
    {
        "title": "Furniture",
        "rows": [
            {"id": "BROWSE_CAT_STORAGE_BED", "title": "Storage Bed"},
            {"id": "BROWSE_CAT_SOFA", "title": "Sofa"},
            {"id": "BROWSE_CAT_MATTRESS", "title": "Mattress"},
            {"id": "BROWSE_CAT_DINING_TABLE", "title": "Dining Table"},
            {"id": "BROWSE_CAT_WARDROBE", "title": "Wardrobe"},
        ],
    },
    {
        "title": "Appliances",
        "rows": [
            {"id": "BROWSE_CAT_SINGLE_DOOR_FRIDGE", "title": "Single Door Fridge"},
            {"id": "BROWSE_CAT_DOUBLE_DOOR_FRIDGE", "title": "Double Door Fridge"},
            {"id": "BROWSE_CAT_TOP_LOAD_WM", "title": "Top Load WM"},
            {"id": "BROWSE_CAT_SPLIT_AC", "title": "Split AC"},
            {"id": "BROWSE_CAT_WINDOW_AC", "title": "Window AC"},
        ],
    },
    {
        "title": "Storage & Work",
        "rows": [
            {"id": "BROWSE_CAT_STUDY_TABLE", "title": "Study Table"},
            {"id": "BROWSE_CAT_OFFICE_CHAIR", "title": "Office Chair"},
            {"id": "BROWSE_CAT_BOOKSHELF", "title": "Bookshelf"},
            {"id": "BROWSE_CAT_SHOE_RACK", "title": "Shoe Rack"},
            {"id": "BROWSE_CAT_STORAGE_CABINET", "title": "Storage Cabinet"},
        ],
    },
]

BROWSE_CATEGORY_LOOKUP = {
    row["id"]: row["title"]
    for section in BROWSE_CATEGORY_SECTIONS
    for row in section["rows"]
}

BROWSE_CATEGORY_SEARCH_TERMS = {
    "BROWSE_CAT_STORAGE_BED": ["storage bed", "bed", "double bed", "cot"],
    "BROWSE_CAT_SOFA": ["sofa", "3 seater sofa", "2 seater sofa"],
    "BROWSE_CAT_MATTRESS": ["mattress", "bed mattress"],
    "BROWSE_CAT_DINING_TABLE": ["dining table", "dining set"],
    "BROWSE_CAT_WARDROBE": ["wardrobe", "almirah", "cupboard"],
    "BROWSE_CAT_SINGLE_DOOR_FRIDGE": ["single door fridge", "fridge"],
    "BROWSE_CAT_DOUBLE_DOOR_FRIDGE": ["double door fridge", "refrigerator"],
    "BROWSE_CAT_TOP_LOAD_WM": ["top load washing machine", "washing machine"],
    "BROWSE_CAT_SPLIT_AC": ["split ac", "air conditioner"],
    "BROWSE_CAT_WINDOW_AC": ["window ac", "air conditioner"],
    "BROWSE_CAT_STUDY_TABLE": ["study table", "study desk", "work table"],
    "BROWSE_CAT_OFFICE_CHAIR": ["office chair", "chair"],
    "BROWSE_CAT_BOOKSHELF": ["bookshelf", "book shelf"],
    "BROWSE_CAT_SHOE_RACK": ["shoe rack", "rack"],
    "BROWSE_CAT_STORAGE_CABINET": ["storage cabinet", "cabinet", "storage rack"],
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
    for key in ("browse_mode", "browse_step", "browse_duration", "browse_requested_items", "last_browse_quote", "last_browse_category"):
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


def _send_browse_categories(phone: str) -> None:
    try:
        whatsapp_client.send_list_message(
            to_phone=phone,
            body_text="Great choice!!! Pick a category and I will narrow down the right products for you.",
            button_text="View Categories",
            sections=BROWSE_CATEGORY_SECTIONS,
            header=BROWSE_FLOW_HEADER,
        )
    except Exception as e:
        print(f"   Warning: category list failed for {phone}: {e}")
        fallback = [
            "Furniture: Storage Bed, Sofa, Mattress, Dining Table, Wardrobe",
            "Appliances: Single Door Fridge, Double Door Fridge, Top Load WM, Split AC, Window AC",
            "Storage & Work: Study Table, Office Chair, Bookshelf, Shoe Rack, Storage Cabinet",
        ]
        whatsapp_client.send_text_message(
            phone,
            "*Categories*\n" + "\n".join(fallback),
            preview_url=False,
        )


def _get_matching_products_for_category(category_id: str) -> List[dict]:
    terms = BROWSE_CATEGORY_SEARCH_TERMS.get(category_id, [])
    results: List[dict] = []
    seen = set()
    for term in terms:
        try:
            matches = search_products_by_name(term) or []
        except Exception as e:
            print(f"   Warning: search failed for {term}: {e}")
            matches = []
        for product in matches:
            pid = product.get("id") or product.get("product_id")
            key = pid or product.get("name")
            if key in seen:
                continue
            seen.add(key)
            results.append(product)
            if len(results) >= 6:
                return results
    return results


def _send_category_products(phone: str, category_id: str, sender_name: str) -> bool:
    category_title = BROWSE_CATEGORY_LOOKUP.get(category_id, "the selected category")
    products = _get_matching_products_for_category(category_id)

    context = _browse_context(phone)
    context["browse_step"] = "await_product_finalization"
    context["last_browse_category"] = category_id
    context["last_browse_category_title"] = category_title

    if not products:
        whatsapp_client.send_text_message(
            phone,
            f"I could not fetch products for *{category_title}* right now. Please type the exact item names you want and I will prepare the quote.",
            preview_url=False,
        )
        return True

    lines = [f"*{category_title} Options*", "Reply with the exact items you want, for example: 1 Storage Bed, 1 Split AC"]
    for idx, product in enumerate(products, 1):
        lines.append(f"{idx}. {product.get('name', 'Product')}")

    whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=False)
    return True


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
    encoded_items = quote(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), safe="")
    return f"{BROWSE_PRODUCTS_BASE_URL}?referral_code={BROWSE_PRODUCTS_REFERRAL_CODE}&items={encoded_items}"


def _format_browse_estimate(items: List[dict], duration: int) -> Tuple[str, int, int, int]:
    original_monthly = 0
    for item in items:
        original_monthly += int(item.get("original_rent") or item.get("rent") or 0) * int(item.get("qty", 1))
    discounted_monthly = int(round(original_monthly * 0.70))
    savings_total = max(0, (original_monthly - discounted_monthly) * int(duration))
    message = (
        f"Perfect, Great timing!!! At other times, it would have costed you Rs. {original_monthly:,} per month, "
        f"but as we are running heavy discount offers due to {BROWSE_PRODUCTS_OCCASION}, and today, it will cost you just Rs. {discounted_monthly:,} rent per month. "
        f"Great Saving Rs. {savings_total:,} in total."
    )
    return message, original_monthly, discounted_monthly, savings_total


def _send_browse_quote(phone: str, sender_name: str, source_text: str, items: List[dict], duration: int) -> None:
    normalized_phone = normalize_phone(phone)
    quote_text, original_monthly, discounted_monthly, savings_total = _format_browse_estimate(items, duration)
    cart_link = _build_browse_cart_link(items, duration)

    session_context[phone] = session_context.get(phone, {})
    session_context[phone]["last_browse_quote"] = {
        "items": items,
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

    whatsapp_client.send_text_message(phone, quote_text, preview_url=False)
    time.sleep(0.4)

    buttons = [
        {"id": "BROWSE_SHOW_DETAILS", "title": "Show full details"},
        {"id": "BROWSE_CUSTOMER_REVIEWS", "title": "Customer Reviews"},
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

    if not items:
        whatsapp_client.send_text_message(phone, "No browse quote found yet. Please share the product list again.")
        return True

    lines = ["*WhatsApp Message Cart*", f"Duration: {duration} months", ""]
    for idx, item in enumerate(items, 1):
        product_name = item.get("product_name") or item.get("name") or "Product"
        qty = int(item.get("qty", 1))
        per_unit = int(item.get("rent") or 0)
        total = per_unit * qty
        lines.append(f"{idx}. {product_name}")
        lines.append(f"   Qty: {qty} | Approx Rent: Rs. {total:,}/mo")

    lines.append("")
    lines.append("Should I checkout, just check the link to gain 5% Additional discount for using our WhatsApp Bot to place order!")
    lines.append(cart_link)

    whatsapp_client.send_text_message(phone, "\n".join(lines), preview_url=True)
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

    if step == "await_duration":
        duration = _parse_duration_from_text(raw_text)
        if duration is None:
            whatsapp_client.send_text_message(
                phone,
                "Great Choice!!! Let me know the Duration of rental first( e.g. 6 or 12 months)",
                preview_url=False,
            )
            return True

        ctx["browse_duration"] = duration
        ctx["browse_step"] = "await_items"
        _save_browse_lead_data(normalized_phone, {"duration_months": duration, "lead_stage": "browse_duration_set"})
        whatsapp_client.send_text_message(
            phone,
            "Thanks!!! Also share the list of items with type e.g. Storage Bed, Single Door Fridge, Split AC, to help me quickly get your details of what your are looking for.",
            preview_url=False,
        )
        _send_browse_categories(phone)
        return True

    if step in ("await_items", "await_product_finalization", "quote_ready"):
        duration = int(ctx.get("browse_duration") or _parse_duration_from_text(raw_text) or 12)
        items = parse_cart_items(raw_text)
        if not items:
            if step == "await_items":
                _send_browse_categories(phone)
                whatsapp_client.send_text_message(
                    phone,
                    "Please type the items again in a little more detail, for example: Storage Bed, Single Door Fridge, Split AC.",
                    preview_url=False,
                )
            else:
                whatsapp_client.send_text_message(
                    phone,
                    "I could not finalize the product list from that message. Please share the exact items or pick a category above.",
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
    # When user re-greets, restore their persisted data (duration, name, location)
    try:
        with conversations_lock:
            if phone not in conversations:
                conversations[phone] = create_initial_state()
            conversations[phone] = restore_lead_to_state(normalized_phone, conversations[phone])
            if sender_name:
                conversations[phone]["collected_info"]["customer_name"] = sender_name
            conversations[phone]["collected_info"]["phone"] = normalized_phone
    except Exception as e:
        print(f"   Warning: State restoration failed (non-fatal): {e}")

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
    t = t.replace(" and ", ", ")
    t = t.replace(" तथा ", ", ")  # harmless if transcript has mixed language

    # Split by commas / newlines / semicolons
    raw_segments = re.split(r"[,\n;]+", t)
    segments = [s.strip() for s in raw_segments if s.strip()]
    return segments


def clean_item_segment(segment: str) -> str:
    """
    Remove filler words that often appear in voice transcripts.
    """
    seg = normalize_text(segment)

    seg = re.sub(r"^\b(i want|need|want|please add|add|give me|get me|send me)\b\s*", "", seg)
    seg = re.sub(r"\b(please|kindly)\b", "", seg)
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
    """
    items = parse_cart_items(text)
    duration = items[0]["duration"] if items else DEFAULT_DURATION

    cart_text = format_sales_cart(items, duration)

    # Store cart in session for later actions like Upfront Payment / Modify Cart
    session_context[phone] = session_context.get(phone, {})
    session_context[phone]["last_cart"] = items
    session_context[phone]["last_duration"] = duration
    session_context[phone]["last_source"] = source
    session_context[phone]["last_raw_text"] = text

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


def process_sales_text_async(phone: str, sender_name: str, text: str, message_id: str):
    """
    Background thread: build cart from typed text in SALES mode.
    """
    with per_phone_locks_lock:
        if phone not in per_phone_locks:
            per_phone_locks[phone] = threading.Lock()
        user_lock = per_phone_locks[phone]

    with user_lock:
        try:
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
processed_ids = set()
MAX_CACHE_SIZE = 100

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
            if message_id in processed_ids:
                print(f"   ⏭️ Skipping duplicate message: {message_id}")
                return jsonify({"status": "duplicate"}), 200
            
            # Add to cache and prune if needed
            processed_ids.add(message_id)
            if len(processed_ids) > MAX_CACHE_SIZE:
                # Remove an old ID
                processed_ids.remove(next(iter(processed_ids)))

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
            # Route back to agent
            print(f"   💰 User requested budget options. Routing to agent.")
            thread = threading.Thread(
                target=process_webhook_async,
                args=(phone, "Show me cheaper alternatives in my budget.", sender_name, message_id, "text", None)
            )
            thread.start()
            return jsonify({"status": "ok", "action": "route_to_agent"}), 200
            
        elif button_id == "LONGER_TENURE":
            # Route back to agent
            print(f"   ⏳ User requested longer tenures. Routing to agent.")
            thread = threading.Thread(
                target=process_webhook_async,
                args=(phone, "What discounts do I get if I rent for 12 months?", sender_name, message_id, "text", None)
            )
            thread.start()
            return jsonify({"status": "ok", "action": "route_to_agent"}), 200
            
        elif button_id == "BROWSE_FURNITURE":
            # List Message for Furniture
            sections = [{
                "title": "Furniture Categories",
                "rows": [
                    {"id": "CAT_BEDS", "title": "Beds & Mattresses"},
                    {"id": "CAT_SOFAS", "title": "Sofas"},
                    {"id": "CAT_DINING", "title": "Dining Tables"},
                    {"id": "CAT_WFH", "title": "Work From Home Setup"},
                    {"id": "CAT_ALL_FURNITURE", "title": "View All Furniture"}
                ]
            }]
            whatsapp_client.send_list_message(
                to_phone=phone,
                body_text="Great choice!\nWhat type of furniture are you looking for?",
                button_text="Select Category",
                sections=sections
            )
            return jsonify({"status": "ok", "action": "list_furniture"}), 200

        elif button_id == "BROWSE_APPLIANCES":
            # List Message for Appliances
            sections = [{
                "title": "Appliance Categories",
                "rows": [
                    {"id": "CAT_FRIDGE", "title": "Refrigerators"},
                    {"id": "CAT_WASHING", "title": "Washing Machines"},
                    {"id": "CAT_AC", "title": "Air Conditioners"},
                    {"id": "CAT_RO", "title": "RO Water Purifiers"},
                    {"id": "CAT_ALL_APPLIANCES", "title": "View All Appliances"}
                ]
            }]
            whatsapp_client.send_list_message(
                to_phone=phone,
                body_text="Perfect!\nWhich appliance do you need?",
                button_text="Select Category",
                sections=sections
            )
            return jsonify({"status": "ok", "action": "list_appliances"}), 200

        elif button_id == "COMPLETE_HOME_SETUP":
            response = """Nice!
I can help you set up a complete home in minutes.

Please tell me:
• City / Location
• House Type (1RK / 1BHK / 2BHK)
• Budget per month

Example message:
"1BHK setup under ₹3000" """
            whatsapp_client.send_text_message(phone, response)
            return jsonify({"status": "ok", "action": "complete_home_setup"}), 200

        elif button_id.startswith("CAT_"):
            # Handle List Selection -> Route back to Agent as Text
            category_text = f"Show me {button_title} options with prices"
            print(f"   📋 List item selected: {button_title}. Routing to agent.")

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

            response = (
                f"Since you completed the discussion with our Bot Ku, "
                f"I want to give you an additional discount of 5%.\n\n"
                f"You can proceed to create the cart and place the order here: "
                f"{KU_REFERRAL_LINK}"
            )
            whatsapp_client.send_text_message(phone, response, preview_url=True)
            print(f"   Lead reserved for {phone}")
            return jsonify({"status": "ok", "action": "reserved"}), 200

        elif button_id == "MODIFY_CART":
            # ✏️  Handle objections — keep the lead warm
            normalized = normalize_phone(phone)
            try:
                from utils.firebase_client import upsert_lead
                upsert_lead(normalized, {"lead_stage": "cart_modification"})
            except Exception as e:
                print(f"   ⚠️ Lead update failed (non-fatal): {e}")

            print(f"   ✏️ Cart modification requested by {phone}. Routing to sales agent.")
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

        # ── Informational Flow Buttons ─────────────────────────────────
        elif button_id == "BROWSE_PRODUCTS":
            _set_browse_context(phone, browse_mode=True, browse_step="await_duration")
            normalized = normalize_phone(phone)
            _save_browse_lead_data(normalized, {"lead_stage": "browse_started"})
            whatsapp_client.send_text_message(
                phone,
                "Great Choice!!! Let me know the Duration of rental first( e.g. 6 or 12 months)",
                preview_url=False,
            )
            return jsonify({"status": "ok", "action": "browse_products_started"}), 200

        elif button_id.startswith("BROWSE_CAT_"):
            _send_category_products(phone, button_id, sender_name)
            return jsonify({"status": "ok", "action": "browse_category_selected"}), 200

        elif button_id in ("BROWSE_SHOW_DETAILS", "SHOW_FULL_DETAILS"):
            _send_browse_full_details(phone, sender_name)
            return jsonify({"status": "ok", "action": "browse_show_details"}), 200

        elif button_id in ("BROWSE_CUSTOMER_REVIEWS", "CUSTOMER_REVIEWS"):
            follow_buttons = [
                {"id": "BROWSE_SHOW_DETAILS", "title": "Show full details"},
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text=LATEST_REVIEWS_TEXT,
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
            follow_buttons = [
                {"id": "BROWSE_PRODUCTS", "title": "Browse Products"},
            ]
            whatsapp_client.send_interactive_buttons(
                to_phone=phone,
                body_text=LATEST_REVIEWS_TEXT,
                buttons=follow_buttons,
            )
            return jsonify({"status": "ok", "action": "latest_reviews"}), 200

        else:
            response = "I received your selection. How can I help you further?"
            whatsapp_client.send_text_message(phone, response)
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
