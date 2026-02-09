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
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Ensure parent packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import BOT_NAME, SALES_PHONE_GURGAON, SALES_PHONE_NOIDA
from agents.sales_agent import run_agent
from agents.state import create_initial_state
from whatsapp.client import WhatsAppClient
from utils.logger import log_conversation_turn, start_new_session

# ========================================
# CONFIGURATION
# ========================================

# WhatsApp API credentials from .env
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "12345")
VERSION = os.getenv("VERSION", "v23.0")

# Validate credentials
if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
    print("❌ Error: Missing WhatsApp credentials in .env file")
    print("   Required: PHONE_NUMBER_ID, ACCESS_TOKEN")
    sys.exit(1)

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
# FLASK APP
# ========================================

app = Flask(__name__)

# Store conversations per phone number
conversations = {}  # phone_number -> ConversationState

# Store session context for interactive button handling
session_context = {}  # phone_number -> {last_product, handoff_needed, intent}

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


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Handle incoming WhatsApp messages (POST request).
    """
    try:
        payload = request.get_json()
        
        # Log incoming payload for debugging
        print(f"\n📨 Incoming webhook payload:")
        print(f"   {payload}")
        
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
        
        print(f"\n💬 Message from {sender_name} ({phone}):")
        print(f"   Type: {message_type}")
        print(f"   Text: {text}")
        
        # Send read receipt first (marks message with blue ticks)
        if message_id:
            whatsapp_client.send_read_and_typing_indicator(message_id)
        
        # Send typing indicator separately (this works EVERY time!)
        whatsapp_client.send_typing_indicator(phone)
        
        # Handle interactive button responses
        if message_type == "interactive" and interactive_response:
            return handle_interactive_response(phone, sender_name, interactive_response, message_id)
        
        if not text:
            # Skip non-text messages (images, audio, etc.)
            print("   ⚠️ Skipping non-text message")
            return jsonify({"status": "non_text_message"}), 200
        
        # Get or create conversation state for this user
        if phone not in conversations:
            conversations[phone] = create_initial_state()
            start_new_session(phone, sender_name)
            print(f"   📝 New conversation started for {phone}")
        
        state = conversations[phone]
        
        # Check for pricing negotiation intent BEFORE processing with agent
        if is_pricing_negotiation(text):
            print(f"   💰 Pricing negotiation detected!")
            return handle_pricing_negotiation(phone, sender_name, text, message_id)
        
        # Process message with the agent
        print(f"   🤖 Processing with {BOT_NAME}...")
        response, new_state = run_agent(text, state)
        
        # Update conversation state
        conversations[phone] = new_state
        
        # Send response via WhatsApp
        print(f"   📤 Sending response...")
        whatsapp_client.send_text_message(phone, response)
        
        # Log the conversation
        log_conversation_turn(phone, sender_name, text, response)
        
        print(f"   ✅ Response sent successfully!")
        
        return jsonify({"status": "ok"}), 200
        
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
    
    # Send interactive buttons
    buttons = [
        {"id": "CALL_ME", "title": "📞 Callback in 15 min"},
        {"id": "WHATSAPP", "title": "💬 Continue here"}
    ]
    
    body_text = """I understand you're looking for the best deal! 😊

I've flagged this for our sales team who can offer special pricing.

**How would you like to proceed?**"""
    
    whatsapp_client.send_interactive_buttons(
        to_phone=phone,
        body_text=body_text,
        buttons=buttons,
        header="💰 Best Price Request",
        footer=f"Sales: {SALES_PHONE_GURGAON}"
    )
    
    # Log the interaction
    log_conversation_turn(phone, sender_name, text, "[Sent interactive pricing buttons]")
    
    print(f"   ✅ Interactive buttons sent!")
    return jsonify({"status": "ok", "action": "pricing_negotiation"}), 200


def handle_interactive_response(phone: str, sender_name: str, interactive: dict, message_id: str):
    """
    Handle user's response to interactive buttons.
    """
    try:
        # Get button ID from response
        button_reply = interactive.get("button_reply", {})
        button_id = button_reply.get("id", "")
        button_title = button_reply.get("title", "")
        
        print(f"   🔘 Button pressed: {button_id} ({button_title})")
        
        # Get stored context
        context = session_context.get(phone, {})
        
        if button_id == "CALL_ME":
            # Handle callback request
            response = f"""📞 **Callback Confirmed!**

Our sales team will call you within **15 minutes** to discuss the best pricing options.

**Your callback is queued!**
• Priority: High
• Estimated wait: 10-15 mins

If urgent, call directly:
• Gurgaon: {SALES_PHONE_GURGAON}
• Noida: {SALES_PHONE_NOIDA}

Thank you for choosing RentBasket! 😊"""
            
            # TODO: Placeholder for sales lead API
            # create_sales_lead(phone, sender_name, context)
            print(f"   📋 [Placeholder] Would create sales lead for {phone}")
            
        elif button_id == "WHATSAPP":
            # Continue on WhatsApp - placeholder for negotiator agent
            response = f"""💬 **Great, let's continue here!**

To help our sales team give you the best quote, please share:

1️⃣ **Products needed**: What items are you looking for?
2️⃣ **Location**: Your delivery pincode?
3️⃣ **Duration**: How many months?
4️⃣ **Budget**: Any budget range in mind?

Our team will review and get back with a special offer! 🎁"""
            
            # TODO: Placeholder for negotiator agent
            # route_to_negotiator_agent(phone, context)
            print(f"   🤝 [Placeholder] Would route to negotiator agent")
            
        else:
            response = "I received your selection. How can I help you further?"
        
        # Send response
        whatsapp_client.send_text_message(phone, response)
        
        # Log
        log_conversation_turn(phone, sender_name, f"[Button: {button_title}]", response)
        
        print(f"   ✅ Button response handled!")
        return jsonify({"status": "ok", "button": button_id}), 200
        
    except Exception as e:
        print(f"   ⚠️ Error handling interactive response: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


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
        
        if msg_type == "text":
            text = message.get("text", {}).get("body")
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
        
        return {
            "message_id": message.get("id"),
            "from_phone": message.get("from"),
            "sender_name": contact.get("profile", {}).get("name", ""),
            "timestamp": message.get("timestamp"),
            "type": msg_type,
            "text": text,
            "interactive": interactive,
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
    
    print("\n" + "="*60)
    print(f"  🤖 {BOT_NAME} - WhatsApp Webhook Server")
    print("="*60)
    print(f"\n📍 Server running on: http://localhost:{args.port}")
    print(f"📍 Webhook URL: http://localhost:{args.port}/webhook")
    print(f"\n⚡ To expose to internet, run in another terminal:")
    print(f"   ngrok http {args.port}")
    print("\n" + "-"*60 + "\n")
    
    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
