#!/usr/bin/env python3
"""
RentBasket WhatsApp Bot "Ku" v1.0
Main entry point with demo mode for testing

Usage:
    python main.py              # Interactive demo mode
    python main.py --test       # Run sample conversation tests
"""

import os
import sys
import argparse
import time

# Ensure parent packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import BOT_NAME, BOT_GREETING, WEBSITE
from agents.sales_agent import create_sales_agent, run_agent
from agents.state import create_initial_state
from whatsapp.client import WhatsAppClient
from whatsapp.indicators import simulate_read_indicator, simulate_typing_indicator
from utils.logger import log_demo_turn, start_new_session, get_log_file_path


# ========================================
# DEMO MODE
# ========================================

def run_demo():
    """Run interactive demo conversation in terminal."""
    print("\n" + "="*60)
    print(f"  🤖 {BOT_NAME} - RentBasket WhatsApp Bot v1.0 (Demo Mode)")
    print("="*60)
    print(f"\n{BOT_GREETING}")
    print("What would you like on rent today?\n")
    print("Type 'quit' to exit | 'reset' to start fresh\n")
    print("-"*60 + "\n")
    
    state = create_initial_state()
    session_id = "demo_user"
    
    # Start new logging session
    start_new_session(session_id, "Demo User")
    print(f"📁 Conversation log: {get_log_file_path(session_id)}\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{BOT_NAME}: Goodbye! 👋")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ["quit", "exit", "bye"]:
            print(f"\n🤖 {BOT_NAME}: Goodbye! Visit us at {WEBSITE} 👋")
            break
        
        if user_input.lower() == "reset":
            state = create_initial_state()
            session_id = f"demo_user_{int(time.time())}"
            start_new_session(session_id, "Demo User")
            print(f"\n🔄 Conversation reset.")
            print(f"📁 New log: {get_log_file_path(session_id)}\n")
            print(f"🤖 {BOT_NAME}: {BOT_GREETING}")
            print("What would you like on rent today?\n")
            continue
        
        # Simulate WhatsApp indicators
        simulate_read_indicator()
        simulate_typing_indicator(1.5)
        
        try:
            response, state = run_agent(user_input, state)
            print(f"\n🤖 {BOT_NAME}: {response}\n")
            
            # Log the conversation turn
            log_demo_turn(user_input, response, session_id)
        except Exception as e:
            print(f"\n🤖 {BOT_NAME}: Sorry, I encountered an error. Please try again.")
            print(f"   [Debug: {type(e).__name__}: {str(e)[:100]}]\n")


# ========================================
# TEST SCENARIOS
# ========================================

SAMPLE_CONVERSATIONS = [
    {
        "name": "Simple Greeting",
        "messages": ["Hey"]
    },
    {
        "name": "Product Search",
        "messages": [
            "Hi",
            "I need a dining table",
            "4 seater for 6 months",
        ]
    },
    {
        "name": "Multiple Items Bundle",
        "messages": [
            "Hi I need: bed, fridge, sofa, washing machine",
            "6 months in Gurgaon sector 45",
            "122001"
        ]
    },
    {
        "name": "AC Rental with Location Check",
        "messages": [
            "1.5 ton window AC rent???",
            "Noida sector 62, 3 months"
        ]
    },
    {
        "name": "Non-serviceable Area",
        "messages": [
            "Need a bed",
            "Saket Delhi",
            "110017"
        ]
    },
    {
        "name": "Policy Question (RAG)",
        "messages": [
            "What is your refund policy?",
            "And what about early termination?"
        ]
    },
]


def run_test_scenarios():
    """Run sample conversation scenarios for testing."""
    print("\n" + "="*60)
    print(f"  🧪 {BOT_NAME} - Test Scenarios")
    print("="*60 + "\n")
    
    for i, scenario in enumerate(SAMPLE_CONVERSATIONS, 1):
        print(f"\n{'─'*60}")
        print(f"📋 TEST {i}: {scenario['name']}")
        print(f"{'─'*60}")
        
        state = create_initial_state()
        
        for msg in scenario["messages"]:
            print(f"\n👤 User: {msg}")
            
            try:
                response, state = run_agent(msg, state)
                print(f"\n🤖 {BOT_NAME}: {response}")
            except Exception as e:
                print(f"\n❌ Error: {type(e).__name__}: {str(e)[:100]}")
        
        print(f"\n✅ Scenario complete.\n")
        time.sleep(1)  # Brief pause between scenarios
    
    print("\n" + "="*60)
    print("  🎉 All test scenarios completed!")
    print("="*60 + "\n")


# ========================================
# WEBHOOK SERVER (for real WhatsApp integration)
# ========================================

def run_webhook_server(port: int = 5000):
    """
    Run a Flask webhook server for real WhatsApp integration.
    
    This is a placeholder - implement when you have WhatsApp API credentials.
    """
    print(f"\n📡 Webhook server would start on port {port}")
    print("To implement this:")
    print("1. Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN")
    print("2. Set up webhook URL in Meta Business dashboard")
    print("3. Uncomment and configure Flask app below")
    print()
    
    # Uncomment below for real implementation:
    """
    from flask import Flask, request, jsonify
    from whatsapp.client import WhatsAppClient, parse_webhook_payload
    
    app = Flask(__name__)
    client = WhatsAppClient(demo_mode=False)
    conversations = {}  # phone -> state
    
    @app.route("/webhook", methods=["GET"])
    def verify_webhook():
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return challenge, 200
        return "Forbidden", 403
    
    @app.route("/webhook", methods=["POST"])
    def handle_message():
        payload = request.get_json()
        message = parse_webhook_payload(payload)
        
        if not message or not message.get("text"):
            return jsonify({"status": "no_message"}), 200
        
        phone = message["from_phone"]
        text = message["text"]
        
        # Mark as read
        client.mark_as_read(message["message_id"])
        client.send_typing_indicator(phone)
        
        # Get or create conversation state
        state = conversations.get(phone, create_initial_state())
        
        # Process with agent
        response, state = run_agent(text, state)
        conversations[phone] = state
        
        # Send response
        client.send_text_message(phone, response)
        
        return jsonify({"status": "ok"}), 200
    
    app.run(host="0.0.0.0", port=port, debug=True)
    """


# ========================================
# MAIN
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{BOT_NAME} - RentBasket WhatsApp Bot v1.0"
    )
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Run sample conversation test scenarios"
    )
    parser.add_argument(
        "--server",
        action="store_true", 
        help="Run webhook server for real WhatsApp integration"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for webhook server (default: 5000)"
    )
    
    args = parser.parse_args()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set.")
        print("   Create a .env file with: OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    if args.server:
        run_webhook_server(args.port)
    elif args.test:
        run_test_scenarios()
    else:
        run_demo()


if __name__ == "__main__":
    main()
