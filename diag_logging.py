import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from utils.db_logger import get_or_create_session, log_conversation_turn, log_event

phone = "919958448249"
name = "Hardik Test"

try:
    print(f"Creating/Getting session for {phone}...")
    session_id = get_or_create_session(phone, name)
    print(f"✅ Session ID: {session_id}")
    
    print("Logging conversation turn...")
    log_conversation_turn(
        phone, name, "Test message from diag script", "Bot response from diag script",
        session_id=session_id,
        agent_used="test_agent",
        intent="test_intent",
        wa_message_id="test_wa_id_123"
    )
    print("✅ Conversation turn logged!")
    
    print("Logging event...")
    log_event(phone, "test_event", {"data": "test"}, session_id=session_id)
    print("✅ Event logged!")
    
except Exception as e:
    print(f"❌ Diagnostic failed: {e}")
    import traceback
    traceback.print_exc()
