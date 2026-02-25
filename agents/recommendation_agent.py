# Recommendation Agent for RentBasket WhatsApp Bot "Ku"
# Helps customers discover and explore products from the full catalogue
# PLUG-AND-PLAY: follows standard interface run_recommendation_agent(message, state) -> (response, state)

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END

from config import LLM_MODEL, LLM_TEMPERATURE, BOT_NAME
from config import SALES_PHONE_GURGAON, SALES_PHONE_NOIDA
from agents.state import ConversationState, create_initial_state
from tools.catalogue_tools import (
    get_full_catalogue_overview_tool,
    browse_category_tool,
    compare_products_tool,
    get_room_package_tool,
    filter_by_budget_tool,
)
from tools.product_tools import get_price_tool, create_quote_tool
from tools.location_tools import check_serviceability_tool


# ========================================
# SYSTEM PROMPT
# ========================================

RECOMMENDATION_SYSTEM_PROMPT = f"""You are *{BOT_NAME}*, RentBasket's friendly Home Setup Consultant on WhatsApp. 😊

## Your Role
You are a product discovery specialist. You help customers explore our catalogue, find the right products, compare options, and build the perfect rental package for their home.

## Your Personality
- Warm, enthusiastic, and knowledgeable about all products.
- Use emojis like 🏠, 📦, 🛋️, ✨ to make conversations friendly.
- Be concise — WhatsApp messages should be short and scannable.
- Use bullet points for clarity.
- **CRITICAL FORMATTING RULE**: Always use a single asterisk `*` for bold (e.g., *this is bold*). NEVER use double asterisks `**`.

## Your Capabilities
You have access to these tools:
1. *get_full_catalogue_overview_tool* — Show all categories with starting prices
2. *browse_category_tool* — Show all products in a category with pricing
3. *compare_products_tool* — Compare 2-3 products side by side
4. *get_room_package_tool* — Suggest curated room packages (combo pricing coming soon)
5. *filter_by_budget_tool* — Find products within a budget range
6. *get_price_tool* — Get detailed pricing for a specific product
7. *create_quote_tool* — Create a rental quote for multiple items
8. *check_serviceability_tool* — Check if location is serviceable

## Pricing Display Rules
- *Always show starting prices first*: 12-month rate with 10% upfront payment discount.
- Frame this as: "Starting from ₹X/month (12-month plan with upfront discount)"
- If customer asks about different durations, use get_price_tool for full breakdown.
- *Default comparison duration*: 12 months. Only change if customer requests it.
- **NEVER show internal product IDs in your response.**

## Conversation Flow
1. *Understand* — What does the customer need? Room type? Specific products? Budget?
2. *Explore* — Show relevant categories or full catalogue overview.
3. *Narrow Down* — Compare products, filter by budget, suggest trending options.
4. *Quote* — Create a bundle quote when they've decided. Ask for pincode if not given.

## Key Rules
- ALWAYS use tools to get accurate prices — never guess!
- When showing products, lead with the *best price* (12mo + upfront discount).
- If customer asks general "what do you offer?" — use get_full_catalogue_overview_tool.
- If customer mentions a specific room (bedroom, kitchen, etc.) — use get_room_package_tool.
- For budget-based queries — use filter_by_budget_tool.
- Frame everything as value: "You get premium quality at just ₹X/month!"
- If the customer is ready to buy or needs specific pricing for shorter durations, let them know your sales colleague can help with exact pricing and order placement.

## Contact Info (if needed)
- Sales (Gurgaon): {SALES_PHONE_GURGAON}
- Sales (Noida): {SALES_PHONE_NOIDA}

Remember: Your goal is to help customers *discover* the perfect products. Show them the value, compare options, and make their home setup journey enjoyable! Always use *single asterisks* for formatting!
"""


# ========================================
# AGENT TOOLS
# ========================================

RECOMMENDATION_TOOLS = [
    get_full_catalogue_overview_tool,
    browse_category_tool,
    compare_products_tool,
    get_room_package_tool,
    filter_by_budget_tool,
    get_price_tool,
    create_quote_tool,
    check_serviceability_tool,
]


# ========================================
# AGENT GRAPH
# ========================================

def create_recommendation_agent():
    """Create and return the recommendation agent graph."""
    
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    llm_with_tools = llm.bind_tools(RECOMMENDATION_TOOLS)
    
    tools_dict = {tool.name: tool for tool in RECOMMENDATION_TOOLS}
    
    # ---- Node Functions ----
    
    def call_agent(state: ConversationState) -> Dict[str, Any]:
        """Call the LLM with current state and tools."""
        messages = list(state["messages"])
        
        info_context = f"\n\n## Current Customer Context\n{state.get('collected_info', {})}"
        full_system_prompt = RECOMMENDATION_SYSTEM_PROMPT + info_context
        
        messages = [SystemMessage(content=full_system_prompt)] + messages
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    def execute_tools(state: ConversationState) -> Dict[str, Any]:
        """Execute tool calls from the agent's response."""
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        results = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            
            print(f"  🔧 [Recommendation] Calling tool: {tool_name}")
            
            if tool_name not in tools_dict:
                result = f"Tool '{tool_name}' not found."
            else:
                try:
                    result = tools_dict[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
            
            results.append(ToolMessage(
                tool_call_id=tc["id"],
                name=tool_name,
                content=str(result)
            ))
        
        return {"messages": results}
    
    def should_continue(state: ConversationState) -> str:
        """Determine if we should continue to tools or end."""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        
        return "end"
    
    # ---- Build Graph ----
    
    graph = StateGraph(ConversationState)
    
    graph.add_node("agent", call_agent)
    graph.add_node("tools", execute_tools)
    
    graph.set_entry_point("agent")
    
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()


# ========================================
# AGENT RUNNER (standard plug-and-play interface)
# ========================================

def run_recommendation_agent(
    user_message: str, 
    state: ConversationState = None
) -> tuple[str, ConversationState]:
    """
    Run the recommendation agent with a user message.
    
    Standard plug-and-play interface:
        run_recommendation_agent(message, state) -> (response, state)
    
    Args:
        user_message: The user's message
        state: Optional existing conversation state
        
    Returns:
        Tuple of (agent response, updated state)
    """
    if state is None:
        state = create_initial_state()
    
    # Add user message
    state["messages"] = list(state["messages"]) + [HumanMessage(content=user_message)]
    
    # Create and run agent
    agent = create_recommendation_agent()
    result = agent.invoke(state)
    
    # Extract response
    response = result["messages"][-1].content
    
    return response, result
