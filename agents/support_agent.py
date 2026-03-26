"""
Support Agent for RentBasket WhatsApp Bot "Ku"
Handles maintenance, billing, relocation, and operations for existing customers.
"""

import os
import sys
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END

from config import LLM_MODEL, LLM_TEMPERATURE, BOT_NAME, SUPPORT_EMAIL
from agents.state import ConversationState, create_initial_state
from tools.support_tools import log_support_ticket_tool, check_ticket_status_tool
from agents.sales_agent import search_company_knowledge_tool  # Reuse knowledge tool

# ========================================
# SYSTEM PROMPT
# ========================================

SUPPORT_SYSTEM_PROMPT = f"""You are *{BOT_NAME}*, RentBasket's friendly Operations & Support assistant. 👋

You are talking to an EXISTING CUSTOMER (verified). Your goal is to resolve their issues efficiently and politely.

## Your Focus Areas
1. **Maintenance & Repair**: "My washing machine is leaking", "The sofa leg is loose".
   - RentBasket provides **FREE maintenance** for normal wear and tear. 🛠️
   - Ask for the specific item and the problem description.
   - For serious issues, log a ticket immediately.
2. **Billing & Payments**: "Why was I charged a late fee?", "Send me my invoice".
   - Check their payment status or explain policies using the knowledge tool.
3. **Logistics & Relocation**: "I am moving to a new flat", "Pick up my furniture".
   - We offer relocation services (usually paid if within the same city).
   - Pickup requests should be logged at least 7 days in advance.
4. **Account Closure**: Help with deposit refund questions (from knowledge base).

## Rules
- **CRITICAL FORMATTING RULE**: Always use a single asterisk `*` for bold (e.g., *this is bold*). NEVER use double asterisks `**`.
- Speak like a helpful friend. Use emojis like 🐢, 🛠️, 💳, 🚚.
- If you can't resolve it, use `log_support_ticket_tool` to escalate it to the operations team.
- Always confirm the customer's specific item if they have multiple rentals.

## Current Customer Profile
{{profile_context}}

## Active Tutorials
{{active_rentals}}
"""

# ========================================
# AGENT GRAPH
# ========================================

SUPPORT_TOOLS = [
    log_support_ticket_tool,
    check_ticket_status_tool,
    search_company_knowledge_tool
]

def create_support_agent(checkpointer=None):
    """Create and return the support agent graph."""
    
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    llm_with_tools = llm.bind_tools(SUPPORT_TOOLS)
    
    tools_dict = {tool.name: tool for tool in SUPPORT_TOOLS}
    
    def call_support_agent(state: ConversationState) -> Dict[str, Any]:
        """Call the LLM with support context."""
        messages = list(state["messages"])
        
        # Inject Profile & Rentals into system prompt
        profile = state["collected_info"].get("customer_profile", "Unknown Profile")
        rentals = state["collected_info"].get("active_rentals", [])
        
        profile_str = f"Name: {profile.get('name')}\nLocation: {profile.get('location')}"
        rentals_str = "\n".join([f"- {r['name']} (Started: {r.get('start_date')})" for r in rentals]) if rentals else "No active rentals found."
        
        full_prompt = SUPPORT_SYSTEM_PROMPT.format(
            profile_context=profile_str,
            active_rentals=rentals_str
        )
        
        messages = [SystemMessage(content=full_prompt)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    def execute_support_tools(state: ConversationState) -> Dict[str, Any]:
        """Execute support tool calls."""
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        results = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            
            # Injection of phone number for ticketing if needed
            if tool_name == "log_support_ticket_tool" and "phone_number" not in tool_args:
                tool_args["phone_number"] = state["collected_info"].get("phone")
                
            print(f"  🛠️ Support Tool: {tool_name}")
            
            if tool_name not in tools_dict:
                result = f"Tool '{tool_name}' not found."
            else:
                try:
                    result = tools_dict[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"Error: {str(e)}"
            
            results.append(ToolMessage(tool_call_id=tc["id"], name=tool_name, content=str(result)))
            
        return {"messages": results}
    
    def should_continue(state: ConversationState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        return "end"

    graph = StateGraph(ConversationState)
    graph.add_node("agent", call_support_agent)
    graph.add_node("tools", execute_support_tools)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    
    return graph.compile(checkpointer=checkpointer)

# ========================================
# AGENT RUNNER
# ========================================

def run_support_agent(user_message: str, state: ConversationState = None) -> tuple[str, ConversationState]:
    """Run the support agent with a user message."""
    if state is None:
        state = create_initial_state()
    
    # Add user message
    state["messages"] = list(state["messages"]) + [HumanMessage(content=user_message)]
    
    # Create and run agent
    agent = create_support_agent()
    result = agent.invoke(state)
    
    # Extract response
    response = result["messages"][-1].content
    return response, result

if __name__ == "__main__":
    # Test stub
    print("Testing Support Agent Runner...")
