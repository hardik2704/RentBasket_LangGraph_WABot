#!/usr/bin/env python3
"""
RentBasket WhatsApp Bot "Ku" - Webhook Server
Flask server for handling real WhatsApp Business API integration

Usage:
    python webhook_server.py                    # Run on default port 5000
    python webhook_server.py --port 8000        # Run on custom port
    ngrok http 5000                             # Expose locally (separate terminal)
"""

import os
import sys
import argparse
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Ensure parent packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import BOT_NAME
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
# FLASK APP
# ========================================

app = Flask(__name__)

# Store conversations per phone number
conversations = {}  # phone_number -> ConversationState

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
        
        print(f"\n💬 Message from {sender_name} ({phone}):")
        print(f"   {text}")
        
        if not text:
            # Skip non-text messages (images, audio, etc.)
            print("   ⚠️ Skipping non-text message")
            return jsonify({"status": "non_text_message"}), 200
        
        # Mark message as read
        if message_id:
            whatsapp_client.mark_as_read(message_id)
        
        # Send typing indicator
        whatsapp_client.send_typing_indicator(phone)
        
        # Get or create conversation state for this user
        if phone not in conversations:
            conversations[phone] = create_initial_state()
            start_new_session(phone, sender_name)
            print(f"   📝 New conversation started for {phone}")
        
        state = conversations[phone]
        
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
        
        return {
            "message_id": message.get("id"),
            "from_phone": message.get("from"),
            "sender_name": contact.get("profile", {}).get("name", ""),
            "timestamp": message.get("timestamp"),
            "type": message.get("type"),
            "text": message.get("text", {}).get("body") if message.get("type") == "text" else None,
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
        default=5000,
        help="Port to run the server on (default: 5000)"
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
