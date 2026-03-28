# Orchestrator for RentBasket WhatsApp Bot "Ku"
# Routes incoming messages to the appropriate agent based on intent.
# PLUG-AND-PLAY: Agents are registered in AGENT_REGISTRY and can be toggled on/off.

import os
import sys
from typing import Dict, Any, Callable, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import ConversationState, create_initial_state
from agents.sales_agent import run_agent
from agents.recommendation_agent import run_recommendation_agent
from agents.support_agent import run_support_agent
from tools.customer_tools import verify_customer_status
from utils.phone_utils import normalize_phone
from utils.firebase_client import upsert_lead, get_lead

# ========================================
# AGENT REGISTRY (plug-and-play)
# ========================================

AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "sales": {
        "enabled": True,
        "runner": run_agent,
        "description": "Handles pricing, quotes, policies, greetings, and discovery for leads",
    },
    "recommendation": {
        "enabled": True,
        "runner": run_recommendation_agent,
        "description": "Helps discover products, browse catalogue, and compare by budget",
    },
    "support": {
        "enabled": True,
        "runner": run_support_agent,
        "description": "Handles maintenance, billing, relocation, and operations for existing customers",
    },
    "support_intake": {
        "enabled": True,
        "runner": None, # Functional stub below
        "description": "Handles identity verification for unknown users with support-like queries",
    }
}

DEFAULT_AGENT = "sales"

def run_support_intake_stub(message, state):
    """Fallback for unknown users asking for support."""
    response = "I see you're asking about maintenance or an existing order, but I couldn't find your account with this number.\n\nCould you please share your *Registered Email ID* or *Customer ID*? Once verified, I can help you with your account."
    return response, state

AGENT_REGISTRY["support_intake"]["runner"] = run_support_intake_stub


# ========================================
# INTENT CLASSIFIER
# ========================================

CLASSIFIER_PROMPT = """You are a message router for a WhatsApp rental furniture bot for RentBasket.

Your job is to classify the user's message into one of these intents:

SUPPORT — The user needs help with:
- Item maintenance or repairs (broken fridge, loose sofa leg)
- Billing, invoices, or deposit refunds
- Moving/Relocating furniture
- Closing their account or returning items
- Tracking an existing pickup or delivery

RECOMMENDATION — The user wants to:
- Browse the catalogue
- Get suggestions for furnishing a home
- Compare products

SALES — The user wants to:
- Get a specific price/quote for a new rental
- Check pincode serviceability
- Ask about terms for new orders
- Select or mention a product by name (for renting)

ESCALATION — The user is frustrated, or explicitly asking for a human agent.

GENERAL — Greeting or casual talk.

CRITICAL CONTEXT:
- If the user is a LEAD (not an existing customer) and mentions a product name, category, or anything related to renting/buying, classify as SALES — never SUPPORT.
- Only classify a LEAD's message as SUPPORT if they explicitly mention a broken item, repair, billing issue, or return.
- If the user is an ACTIVE_CUSTOMER and mentions a product name while in a SUPPORT context, classify as SUPPORT.
- If the user is currently talking to the SUPPORT agent, tend towards SUPPORT unless they are clearly starting a new SALES journey.

Respond with ONLY one word: SUPPORT, RECOMMENDATION, SALES, ESCALATION, or GENERAL.
Do not explain your reasoning."""


def classify_intent(
    user_message: str, 
    state: ConversationState
) -> str:
    """
    Classify the user's message intent using LLM and state context.
    """
    try:
        status = state["collected_info"].get("customer_status", "unknown")
        
        # 1. DETERMINISTIC ID ROUTING (Escalation Logic Synchronization)
        # Intercept structured IDs to bypass LLM lag and potential misclassification
        upper_msg = user_message.strip().upper()
        if upper_msg in ("SUP_TALK_TEAM", "ESCALATION"):
            return "escalation"
        
        # If it's a support menu ID, it's definitely support
        if upper_msg.startswith("SUP_TYPE_") or upper_msg.startswith("MAINT_") or upper_msg.startswith("BILL_") or upper_msg.startswith("REF_"):
            return "support"

        # 2. KEYWORD ESCALATION
        lower_msg = user_message.lower()
        if any(kw in lower_msg for kw in ["human", "executive", "agent", "person", "call me"]):
            return "escalation"

        # 2.5 SALES FLOW STICKINESS: If user is a lead in an active sales flow,
        # keep them in sales unless they explicitly ask for support
        current_agent = state.get("active_agent", "sales")
        if current_agent == "sales" and status == "lead":
            support_keywords = ["broken", "repair", "fix", "maintenance", "billing", "invoice",
                                "refund", "pickup", "return", "complaint", "issue with"]
            if not any(kw in lower_msg for kw in support_keywords):
                return "sales"

        # 3. LLM CLASSIFICATION
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
        
        verification_hint = f"\nUser Status: {status.upper()}"
        verification_hint += f"\nCurrent Agent: {state.get('active_agent', 'sales')}"
        verification_hint += f"\nConversation Stage: {state.get('conversation_stage', 'unknown')}"

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
        elif intent == "ESCALATION":
            return "escalation"
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
    Enhanced Orchestrator with Priority/Intake routing.
    """
    if state is None:
        state = create_initial_state()
    
    # 1. VERIFICATION & NORMALIZATION
    raw_phone = state["collected_info"].get("phone")
    if raw_phone:
        normalized = normalize_phone(raw_phone)
        status = state["collected_info"].get("customer_status", "unknown")
        
        # Fresh lookup if unknown or if we need data
        if status == "unknown" or not state["collected_info"].get("is_verified_customer"):
            print(f"  🔍 Verifying normalized phone: {normalized}")
            verification = verify_customer_status(normalized)
            
            # Map result to state
            state["collected_info"]["customer_status"] = verification["status"]
            state["collected_info"]["is_verified_customer"] = verification["is_verified"]
            
            if verification["is_verified"]:
                state["collected_info"]["customer_profile"] = verification["profile"]
                state["collected_info"]["active_rentals"] = verification["active_rentals"]
                state["collected_info"]["customer_name"] = verification["profile"]["name"]
                print(f"  ✅ {verification['status'].upper()}: {verification['profile']['name']}")
            else:
                # If interaction started, we downgrade unknown to 'lead' for sales consistency
                if state["collected_info"]["customer_status"] == "unknown":
                    state["collected_info"]["customer_status"] = "lead"
                print(f"  👤 Status set to: {state['collected_info']['customer_status']}")

                # --- LEAD TRACKING INTEGRATION ---
                if state["collected_info"]["customer_status"] == "lead":
                    # Check if lead exists, if not create 'new' lead
                    existing_lead = get_lead(normalized)
                    if not existing_lead:
                        print(f"  🆕 Creating new lead for {normalized}")
                        upsert_lead(normalized, {
                            "name": state["collected_info"].get("customer_name") or "New Lead",
                            "phone": normalized,
                            "lead_stage": "new"
                        })
                    else:
                        # Sync existing lead name into state if local state is empty
                        if not state["collected_info"].get("customer_name") and existing_lead.get("name"):
                            state["collected_info"]["customer_name"] = existing_lead["name"]

    # 2. INTENT CLASSIFICATION
    intent = classify_intent(user_message, state)
    current_agent = state.get("active_agent", DEFAULT_AGENT)
    status = state["collected_info"].get("customer_status", "unknown")
    
    print(f"  🧭 Context -> Intent: {intent} | Status: {status} | Current: {current_agent}")
    
    # 3. ROUTING PRINCIPLES
    target_agent = current_agent # Default to sticky
    
    # Principle A: Frustration/Escalation -> Human
    if intent == "escalation":
        target_agent = "sales" # Send to sales for handoff logic
        state["escalation_requested"] = True
        state["needs_human"] = True
        print("  🚨 ESCALATION detected!")

    # Principle B: Customer + Support Query -> Support Agent
    elif intent == "support":
        if status in ("active_customer", "past_customer"):
            target_agent = "support"
        elif status == "lead":
            # Leads should not go to support - keep in sales
            target_agent = "sales"
            print("  -> Lead routed to sales despite SUPPORT classification")
        else:
            # Unknown asking for support -> Intake Mode
            target_agent = "support_intake"
            print("  -> Routing to Support Intake (No account found)")

    # Principle C: Recommendation Query -> Recommendation Agent
    elif intent == "recommendation":
        # Keep leads in the Sales Agent for consistent qualification
        if status == "lead":
            target_agent = "sales"
        else:
            target_agent = "recommendation"

    # Principle D: Pricing/Sales -> Sales Agent
    elif intent == "sales":
        target_agent = "sales"

    # 4. OVERRIDE Logic
    # If issue type changed significantly, we force a switch even if sticky
    if intent in ("support", "sales", "recommendation") and target_agent != current_agent:
        print(f"  🔀 Intent change: Switching to {target_agent}")

    # 5. EXECUTION
    state["active_agent"] = target_agent
    
    # Get runner from registry
    agent_entry = AGENT_REGISTRY.get(target_agent)
    if not agent_entry or not agent_entry.get("enabled"):
        target_agent = DEFAULT_AGENT
        agent_entry = AGENT_REGISTRY[target_agent]
        
    runner = agent_entry["runner"]
    if runner is None and target_agent == "support_intake":
        runner = run_support_intake_stub
     
    try:
        response, new_state = runner(user_message, state)
    except Exception as e:
        print(f"  ❌ CRITICAL: Agent runner '{target_agent}' failed: {e}")
        # Final safety fallback to prevent crash
        if target_agent == "support":
             from agents.support_agent import process_escalation
             response, new_state = process_escalation(state, f"Agent Failure: {str(e)}")
        else:
             response = "I encountered a temporary technical glitch. I've notified our team to assist you manually right away. [SEND_HANDOFF_BUTTONS]"
             new_state = state
             new_state["needs_human"] = True
    
    new_state["active_agent"] = target_agent
    new_state["_routing_meta"] = {"intent": intent, "agent_used": target_agent}
    
    return response, new_state
