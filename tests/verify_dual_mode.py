"""
Verification script for Dual-Mode Routing.
Tests if the Orchestrator correctly identifies a customer and routes to the Support Agent.
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import route_and_run
from agents.state import create_initial_state
from dotenv import load_dotenv

load_dotenv()

def test_routing():
    print("\n--- 🧪 Testing Dual-Mode Bot Routing ---\n")
    
    # 1. Test New Lead (Unknown Phone)
    state_lead = create_initial_state()
    state_lead["collected_info"]["phone"] = "910000000000"
    
    print("Test 1: New Lead asking for price")
    msg1 = "What is the rent for a 3-seater sofa?"
    resp1, state_lead = route_and_run(msg1, state_lead)
    print(f"   Agent Used: {state_lead['_routing_meta']['agent_used']}")
    print(f"   Intent: {state_lead['_routing_meta']['intent']}")
    
    # 2. Test Existing Customer (Hardik Sharma - 9958448249)
    state_cust = create_initial_state()
    state_cust["collected_info"]["phone"] = "9958448249"
    
    print("\nTest 2: Verified Customer asking for maintenance")
    msg2 = "My washing machine is making a loud noise, please help."
    
    # Note: This will attempt an LLM call if OPENAI_API_KEY is present
    try:
        resp2, state_cust = route_and_run(msg2, state_cust)
        print(f"   Agent Used: {state_cust['_routing_meta']['agent_used']}")
        print(f"   Intent: {state_cust['_routing_meta']['intent']}")
        print(f"   Verified: {state_cust['collected_info']['is_verified_customer']}")
        print(f"   Customer Name: {state_cust['collected_info']['customer_name']}")
    except Exception as e:
        print(f"   ⚠️ LLM Call failed (likely no API key): {e}")
        print("   Checking verification logic directly...")
        from tools.customer_tools import verify_customer_status
        v = verify_customer_status("9958448249")
        print(f"   Direct Verification for 9958448249: {v['is_verified']}")
        if v['is_verified']:
            print(f"   Name found: {v['profile']['name']}")

if __name__ == "__main__":
    test_routing()
