import sys
import os
import json
from datetime import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import route_and_run
from agents.state import create_initial_state
from utils.firebase_client import get_lead

def test_lead_qualification():
    print("\n🚀 STARTING LEAD QUALIFICATION TEST\n")
    
    test_phone = "919999999999"
    normalized_phone = "9999999999" # Orchestrator strips prefix
    test_push_name = "Hardik"
    
    # Initialize state
    state = create_initial_state()
    state["collected_info"]["phone"] = test_phone
    state["collected_info"]["customer_name"] = test_push_name
    
    # ---------------------------------------------------------
    # MESSAGE 1: INTENT
    # ---------------------------------------------------------
    print("--- MESSAGE 1 ---")
    msg1 = "Hi, looking for a sofa for my new flat."
    response1, state = route_and_run(msg1, state)
    print(f"User: {msg1}")
    print(f"Bot: {response1}\n")
    
    lead_after_1 = get_lead(normalized_phone)
    if not lead_after_1:
        print("❌ Lead not found in Firestore. Check orchestrator logic.")
        return
    print(f"Firestore Stage: {lead_after_1.get('lead_stage')}")
    print(f"Extracted Prefs: {lead_after_1.get('product_preferences', [])}\n")

    # ---------------------------------------------------------
    # MESSAGE 2: LOCATION
    # ---------------------------------------------------------
    print("--- MESSAGE 2 ---")
    msg2 = "I'm in Sector 62, Noida. Pincode is 201301."
    response2, state = route_and_run(msg2, state)
    print(f"User: {msg2}")
    print(f"Bot: {response2}\n")
    
    lead_after_2 = get_lead(test_phone)
    print(f"Firestore Stage: {lead_after_2.get('lead_stage') or 'qualified'}")
    print(f"Extracted Location: {lead_after_2.get('delivery_location')}\n")

    # ---------------------------------------------------------
    # MESSAGE 3: PRODUCT SELECTION / SUGGESTION
    # ---------------------------------------------------------
    print("--- MESSAGE 3 ---")
    msg3 = "I like the 5 seater fabric one. Can you add it?"
    response3, state = route_and_run(msg3, state)
    print(f"User: {msg3}")
    print(f"Bot: {response3}\n")
    
    lead_after_3 = get_lead(test_phone)
    print(f"Firestore Cart: {lead_after_3.get('final_cart', [])}\n")

    # ---------------------------------------------------------
    # MESSAGE 4: CLOSE
    # ---------------------------------------------------------
    print("--- MESSAGE 4 ---")
    msg4 = "Yes, please reserve it."
    response4, state = route_and_run(msg4, state)
    print(f"User: {msg4}")
    print(f"Bot: {response4}\n")
    
    final_lead = get_lead(test_phone)
    print("🏁 FINAL FIRESTORE STATE:")
    print(json.dumps(final_lead, indent=2, default=str))

if __name__ == "__main__":
    test_lead_qualification()
