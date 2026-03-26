# Orchestrator for RentBasket WhatsApp Bot "Ku"
# Routes incoming messages to the appropriate agent based on intent.
# PLUG-AND-PLAY: Agents are registered in AGENT_REGISTRY and can be toggled on/off.

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Callable, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import ConversationState, create_initial_state
from agents.sales_agent import run_agent
from agents.recommendation_agent import run_recommendation_agent
from agents.support_agent import run_support_agent
from tools.customer_tools import verify_customer_status

# ========================================
# AGENT REGISTRY (plug-and-play)
# ========================================

AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "sales": {
        "enabled": True,
        "runner": run_agent,
        "description": "Handles pricing, quotes, policies, greetings, and general queries",
    },
    "recommendation": {
        "enabled": True,
        "runner": run_recommendation_agent,
        "description": "Helps customers discover products, browse catalogue, compare, and filter by budget",
    },
    "support": {
        "enabled": True,
        "runner": run_support_agent,
        "description": "Handles maintenance, billing, relocation, and operations for existing customers",
    },
}

DEFAULT_AGENT = "sales"


# ========================================
# INTENT CLASSIFIER
# ========================================

CLASSIFIER_PROMPT = """You are a message router for a WhatsApp rental furniture bot for RentBasket.

Your job is to classify the user's message into one of these intents:

SUPPORT — The user is an EXISTING CUSTOMER and wants help with:
- Item maintenance or repairs (broken appliance, sofa damage)
- Billing, payments, invoices, or deposit refunds
- Relocating their current furniture to a new home
- Closing their account or returning all items
- Reporting an issue with a recent delivery or installation

RECOMMENDATION — The user wants to:
- Browse or explore the product catalogue
- Get suggestions for furnishing a room or home
- Compare products or find items within a budget

SALES — The user wants to:
- Get a specific price/quote for a new product
- Check delivery serviceability (pincode)
- Ask about general policies for new orders
- Place a new order or finalize a rental

GENERAL — Greeting or casual conversation.

Respond with ONLY one word: SUPPORT, RECOMMENDATION, SALES, or GENERAL.
Do not explain your reasoning."""


def classify_intent(
    user_message: str, 
    state: ConversationState
) -> str:
    """
    Classify the user's message intent using a lightweight LLM call.
    """
    try:
        # If the user is verified, we prioritize SUPPORT intent
        is_verified = state["collected_info"].get("is_verified_customer", False)
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        recent_messages = []
        if state and state.get("messages"):
            for msg in list(state["messages"])[-4:]:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                if content:
                    recent_messages.append(f"{role}: {content[:200]}")
        
        context = ""
        if recent_messages:
            context = f"\n\nRecent conversation:\n" + "\n".join(recent_messages)
        
        verification_hint = "\nNote: This user is already a RentBasket customer." if is_verified else ""

        response = llm.invoke([
            SystemMessage(content=CLASSIFIER_PROMPT + verification_hint),
            HumanMessage(content=f"Classify this message:{context}\n\nNew message: {user_message}")
        ])
        
        intent = response.content.strip().upper()
        
        if intent == "SUPPORT":
            return "support"
        elif intent == "RECOMMENDATION":
            return "recommendation"
        elif intent == "SALES":
            return "sales"
        else:
            return "general"
            
    except Exception as e:
        print(f"  ⚠️ Intent classification failed: {e}")
        return "general"


# ========================================
# ROUTING LOGIC
# ========================================

def route_and_run(
    user_message: str, 
    state: ConversationState = None
) -> Tuple[str, ConversationState]:
    """
    Route a user message to the appropriate agent and run it.
    """
    if state is None:
        state = create_initial_state()
    
    # 1. VERIFICATION LAYER
    # Check if we already have the phone or extracted it
    phone = state["collected_info"].get("phone")
    if phone and not state["collected_info"].get("is_verified_customer"):
        print(f"  🔍 Verifying customer status for: {phone}")
        verification = verify_customer_status(phone)
        if verification["is_verified"]:
            state["collected_info"]["is_verified_customer"] = True
            state["collected_info"]["customer_profile"] = verification["profile"]
            state["collected_info"]["active_rentals"] = verification["active_rentals"]
            state["collected_info"]["customer_name"] = verification["profile"]["name"]
            print(f"  ✅ Verified Customer: {verification['profile']['name']}")
        else:
            print("  👤 New Lead (Not a verified customer)")

    # 2. Get the current active agent
    current_agent = state.get("active_agent", DEFAULT_AGENT)
    
    # 3. Classify intent
    intent = classify_intent(user_message, state)
    print(f"  🧭 Intent: {intent} (current agent: {current_agent})")
    
    # 4. Determine target agent
    if intent == "support":
        target_agent = "support"
    elif intent == "recommendation":
        target_agent = "recommendation"
    elif intent == "sales":
        target_agent = "sales"
    else:
        # "general" — sticky: keep the current agent
        target_agent = current_agent
    
    # Check if target agent is enabled; fallback if not
    agent_entry = AGENT_REGISTRY.get(target_agent)
    if not agent_entry or not agent_entry.get("enabled"):
        print(f"  ⚠️ Agent '{target_agent}' is disabled, routing to '{DEFAULT_AGENT}'")
        target_agent = DEFAULT_AGENT
    
    # Log routing decision
    if target_agent != current_agent:
        print(f"  🔀 Switching agent: {current_agent} → {target_agent}")
    else:
        print(f"  ➡️ Staying with agent: {target_agent}")
    
    # 5. Handle agent switch logic (Greeting etc.)
    if target_agent == "support" and current_agent != "support":
        # Pre-pended notification of switch if needed
        # (Could be handled inside the runner too)
        pass

    state["active_agent"] = target_agent
    
    # 6. Run the agent
    runner = _get_agent_runner(target_agent)
    response, new_state = runner(user_message, state)
    
    # Ensure active_agent persists in new state
    new_state["active_agent"] = target_agent
    
    # Attach routing metadata for the caller (webhook_server)
    new_state["_routing_meta"] = {
        "intent": intent,
        "agent_used": target_agent,
    }
    
    return response, new_state
