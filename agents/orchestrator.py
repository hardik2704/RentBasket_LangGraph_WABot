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


# ========================================
# AGENT REGISTRY (plug-and-play)
# ========================================
# Set "enabled" to False to disable an agent without touching any other code.
# The orchestrator will fall back to the default agent ("sales") for disabled agents.

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
}

DEFAULT_AGENT = "sales"


# ========================================
# INTENT CLASSIFIER
# ========================================

CLASSIFIER_PROMPT = """You are a message router for a WhatsApp rental furniture bot.

Your job is to classify the user's message into one of these intents:

RECOMMENDATION — The user wants to:
- Browse or explore the product catalogue
- Know what products/categories are available
- Get suggestions for furnishing a room or home
- Compare products
- Find products within a budget
- General product discovery ("what do you offer?", "show me sofas", "help me set up my home")

SALES — The user wants to:
- Get a specific price/quote for a specific product
- Check delivery serviceability (pincode)
- Ask about policies, terms, refunds, maintenance
- Negotiate pricing or ask for discounts
- Place an order or finalize a rental
- Get contact info or office location

GENERAL — The user is:
- Greeting (Hi, Hello, Hey)
- Saying something casual or unclear
- Asking something unrelated to products

Respond with ONLY one word: RECOMMENDATION, SALES, or GENERAL.
Do not explain your reasoning."""


def classify_intent(
    user_message: str, 
    state: ConversationState
) -> str:
    """
    Classify the user's message intent using a lightweight LLM call.
    
    Args:
        user_message: The user's message text
        state: Current conversation state (for context)
        
    Returns:
        One of: "recommendation", "sales", "general"
    """
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Include recent conversation context for better classification
        recent_messages = []
        if state and state.get("messages"):
            # Take last 4 messages for context
            for msg in list(state["messages"])[-4:]:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                if content:
                    recent_messages.append(f"{role}: {content[:200]}")
        
        context = ""
        if recent_messages:
            context = f"\n\nRecent conversation:\n" + "\n".join(recent_messages)
        
        response = llm.invoke([
            SystemMessage(content=CLASSIFIER_PROMPT),
            HumanMessage(content=f"Classify this message:{context}\n\nNew message: {user_message}")
        ])
        
        intent = response.content.strip().upper()
        
        if intent == "RECOMMENDATION":
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

def _get_agent_runner(agent_name: str) -> Callable:
    """
    Get the runner function for an agent, with fallback to default.
    
    Args:
        agent_name: Name of the agent ("sales", "recommendation", etc.)
    
    Returns:
        Agent runner function
    """
    entry = AGENT_REGISTRY.get(agent_name)
    
    if entry and entry.get("enabled"):
        return entry["runner"]
    
    # Fallback to default agent
    print(f"  ⚠️ Agent '{agent_name}' not available, falling back to '{DEFAULT_AGENT}'")
    return AGENT_REGISTRY[DEFAULT_AGENT]["runner"]


def route_and_run(
    user_message: str, 
    state: ConversationState = None
) -> Tuple[str, ConversationState]:
    """
    Route a user message to the appropriate agent and run it.
    
    This is the main entry point used by webhook_server.py.
    Standard interface: route_and_run(message, state) -> (response, state)
    
    Routing logic:
    1. Check if there's a sticky active_agent from a previous turn.
    2. Classify the intent of the new message.
    3. If intent matches a different agent, switch.
    4. If intent is "general", keep the current agent (sticky).
    5. Run the selected agent and return the result.
    
    Args:
        user_message: The user's message text
        state: Optional existing conversation state
        
    Returns:
        Tuple of (agent response, updated state)
    """
    if state is None:
        state = create_initial_state()
    
    # Get the current active agent
    current_agent = state.get("active_agent", DEFAULT_AGENT)
    
    # Classify intent
    intent = classify_intent(user_message, state)
    print(f"  🧭 Intent: {intent} (current agent: {current_agent})")
    
    # Determine target agent
    if intent == "recommendation":
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
    
    # Update active agent in state
    state["active_agent"] = target_agent
    
    # Get and run the agent
    runner = _get_agent_runner(target_agent)
    response, new_state = runner(user_message, state)
    
    # Ensure active_agent persists in new state
    new_state["active_agent"] = target_agent
    
    return response, new_state
