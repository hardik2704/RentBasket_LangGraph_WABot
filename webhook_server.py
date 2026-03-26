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
import argparse
import threading
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Ensure parent packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import BOT_NAME, SALES_PHONE_GURGAON, SALES_PHONE_NOIDA
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
    {"id": "BROWSE_FURNITURE", "title": "Browse Furniture"},
    {"id": "BROWSE_APPLIANCES", "title": "Browse Appliances"},
    {"id": "COMPLETE_HOME_SETUP", "title": "Complete Home Setup"}
]

# Words that count as a greeting (first message or re-greeting)
GREETING_WORDS = {"hi", "hello", "hey", "hii", "hiii", "helo", "heloo", "helo", "helloo",
                  "namaste", "namaskar", "good morning", "good afternoon", "good evening",
                  "hola", "yo", "sup", "start"}

def is_greeting(text: str) -> bool:
    """Check if the incoming message is a greeting."""
    return text.strip().lower().rstrip("!.,?") in GREETING_WORDS

def handle_greeting(phone: str, sender_name: str):
    """
    Send the structured greeting message with interactive buttons.
    This bypasses the LLM entirely for a deterministic, instant response.
    """
    # Use proper name if it looks real, otherwise generic
    name = sender_name if sender_name and sender_name.strip() else "there"

    greeting_text = (
        f"Hi {name} \ud83d\udc4b\n"
        f"I'm Ku \ud83d\udc22 from RentBasket, your personal rental assistant.\n"
        f"\n"
        f"We offer quality furniture and appliances on rent at affordable prices, "
        f"powered by customer service which is best in the market.\n"
        f"\n"
        f"Check out our website for more details:\n"
        f"https://rentbasket.com"
    )

    try:
        result = whatsapp_client.send_interactive_buttons(
            to_phone=phone,
            body_text=greeting_text,
            buttons=GREETING_BUTTONS
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

    # Log to DB + file
    try:
        session_id = get_or_create_session(phone, sender_name)
        log_conversation_turn(phone, sender_name, "[Greeting]", greeting_text,
                              session_id=session_id)
        log_event(phone, "greeting_sent", {"buttons": [b["id"] for b in GREETING_BUTTONS]},
                  session_id=session_id)
    except Exception as e:
        print(f"   \u26a0\ufe0f Logging error (non-fatal): {e}")

    print(f"   \ud83d\udc4b Greeting + interactive buttons sent to {phone}")
    return jsonify({"status": "ok", "action": "greeting"}), 200


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
# FLASK APP
# ========================================

app = Flask(__name__)

# Store conversations per phone number
conversations = {}  # phone_number -> ConversationState

# Store session context for interactive button handling
session_context = {}  # phone_number -> {last_product, handoff_needed, intent}

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
                    start_new_session(phone, sender_name)
                    print(f"   📝 New conversation started for {phone} (Normalized: {normalized_phone})")
                state = conversations[phone]
            
            # Get or create DB session
            session_id = get_or_create_session(phone, sender_name)
            
            # Ensure customer name and phone are in state
            if sender_name and not state["collected_info"].get("customer_name"):
                state["collected_info"]["customer_name"] = sender_name
            
            # Always use normalized phone for state consistency
            state["collected_info"]["phone"] = normalized_phone
            
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
                
                # Standard handoff handler
                elif "[SEND_HANDOFF_BUTTONS]" in msg:
                    clean_msg = msg.replace("[SEND_HANDOFF_BUTTONS]", "").strip()
                    handoff_buttons = [
                        {"id": "CALL_ME", "title": "📞 Call me"},
                        {"id": "WHATSAPP", "title": "💬 Chat here"}
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
                phone, sender_name, text, log_response,
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
        
        if not text:
            # Skip non-text messages (images, audio, etc.)
            print("   ⚠️ Skipping non-text message")
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
    
    body_text = """I completely understand — let me help you find the absolute best value for your budget. 👍

How would you like to proceed?"""
    
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text=body_text,
        buttons=buttons,
        header="💰 Best Price Request",
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
            response = f"""📞 *Callback Confirmed!*

Our sales team will call you within *15 minutes* to discuss your requirements.

*Your callback is queued!*
• Priority: High
• Estimated wait: 10-15 mins

If urgent, call directly:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

Thank you for choosing RentBasket! 😊"""
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
                body_text="Great choice! 🛋️\nWhat type of furniture are you looking for?",
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
                body_text="Perfect! ❄️\nWhich appliance do you need?",
                button_text="Select Category",
                sections=sections
            )
            return jsonify({"status": "ok", "action": "list_appliances"}), 200

        elif button_id == "COMPLETE_HOME_SETUP":
            response = """Nice! 🏡  
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
            category_text = button_title
            print(f"   📋 List item selected: {category_text}. Routing to agent.")
            
            thread = threading.Thread(
                target=process_webhook_async,
                args=(phone, category_text, sender_name, message_id, "text", None)
            )
            thread.start()
            return jsonify({"status": "ok", "action": "list_route_to_agent"}), 200

        else:
            response = "I received your selection. How can I help you further?"
            whatsapp_client.send_text_message(phone, response)
            return jsonify({"status": "ok", "button": button_id}), 200
        
    except Exception as e:
        print(f"   ⚠️ Error handling interactive response: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def handle_fallback(phone: str, sender_name: str):
    """Send fallback message with dynamic examples."""
    examples = get_next_fallback_examples()
    response = f"""Oops! I'm still learning and didn't quite catch that. 🐢

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
        
        if msg_type == "text":
            text = message.get("text", {}).get("body")
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
        elif msg_type == "reaction":
            reaction = message.get("reaction", {})
            text = f"[Reaction: {reaction.get('emoji')}]"
        
        return {
            "message_id": message.get("id"),
            "from_phone": message.get("from"),
            "sender_name": contact.get("profile", {}).get("name", ""),
            "timestamp": message.get("timestamp"),
            "type": msg_type,
            "text": text,
            "interactive": interactive,
            "reaction": reaction,
            "quoted_message_id": context_id
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
