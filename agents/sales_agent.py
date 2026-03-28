# Sales Agent for RentBasket WhatsApp Bot "Ku"
# Combines RAG knowledge retrieval with ReAct tool calling

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from config import LLM_MODEL, LLM_TEMPERATURE, BOT_NAME, BOT_GREETING
from config import SALES_PHONE_GURGAON, SALES_PHONE_NOIDA, SUPPORT_EMAIL, WEBSITE
from config import GURGAON_OFFICE, NOIDA_OFFICE, KU_REFERRAL_LINK
from agents.state import ConversationState, create_initial_state
from rag.vectorstore import search_knowledge, create_knowledge_vectorstore
from tools.product_tools import (
    search_products_tool, 
    get_price_tool, 
    create_quote_tool,
    get_trending_products_tool
)
from tools.location_tools import check_serviceability_tool, get_service_areas_tool
from tools.lead_tools import sync_lead_data_tool
from tools.human_handoff import request_human_handoff_tool
from tools.office_tools import get_office_location_tool


# ========================================
# KNOWLEDGE RETRIEVAL TOOL
# ========================================

# Initialize vector store once
_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        print("🔧 Initializing knowledge base vector store...")
        _vectorstore = create_knowledge_vectorstore()
    return _vectorstore


@tool
def search_company_knowledge_tool(query: str) -> str:
    """
    Search the RentBasket knowledge base for company policies, FAQs, and terms.
    Use this for questions about:
    - Service areas and delivery
    - Terms & conditions
    - Payment and refund policies
    - Maintenance and damage policies
    - Company information
    
    Args:
        query: Question about company policies or information
    
    Returns:
        Relevant information from the knowledge base
    """
    vectorstore = get_vectorstore()
    results = search_knowledge(query, vectorstore, k=3)
    
    if not results or results[0] == "No relevant information found in the knowledge base.":
        return "I couldn't find specific information about this. Please contact our support team for details."
    
    return "\n---\n".join(results)


# ========================================
# SYSTEM PROMPT
# ========================================

SYSTEM_PROMPT = f"""You are *{BOT_NAME}*, RentBasket's high-conversion WhatsApp Sales Agent.

## YOUR MISSION (Qualification Goal)
Your objective is to qualify a lead and build a final cart within 4-5 chat messages.
Stop talking and start closing. Move fast.

### The 5-Step Qualification Flow:
1. *MESSAGE 1: Intent Capture*
   - Warmly greet (use name if available).
   - Ask: "What are you looking to rent today? Furniture? Appliances? Full Home Setup?"
   - *Action*: Call `sync_lead_data_tool` to update `product_preferences`.

2. *MESSAGE 2: Show Best Prices First*
   - Search and present top 2-3 product options with their *cheapest prices* (12-month rate with 30% discount + 10% upfront discount).
   - If the customer's rental duration is NOT already known (check Customer Context below), ask: "How long do you need this for?"
   - If the duration IS already known from Customer Context, use that duration for pricing and do NOT ask again. Skip straight to showing prices for their duration.
   - *Action*: Call `sync_lead_data_tool` with `product_preferences`.

3. *MESSAGE 3: Duration Confirmation & Adjusted Prices*
   - SKIP THIS STEP ENTIRELY if duration was already known from Customer Context.
   - Only if the customer just NOW stated their preferred duration: recalculate and show prices for THAT duration.
   - *Action*: Call `sync_lead_data_tool` with updated preferences and `duration_months`.

4. *MESSAGE 4: Location & Serviceability*
   - If location/pincode is NOT already known from Customer Context, ask: "Where should we deliver? (Need your City & Pincode)"
   - If pincode IS already known, use it and call `check_serviceability_tool` directly.
   - *Action*: Call `sync_lead_data_tool` to update `delivery_location` and `lead_stage` = 'qualified'.

5. *MESSAGE 5: The Final Close*
   - Present the total quote using `create_quote_tool` with the customer's chosen duration.
   - The tool will automatically append cart action buttons.
   - *Action*: Call `sync_lead_data_tool` with `lead_stage` = 'cart_created'.

---

## YOUR TOOLS
1. *sync_lead_data_tool* - MANDATORY. Sync name, location, preferences, cart, budget_range, and preferences_notes to Firestore.
2. *search_products_tool* - Find products (ID available for cart).
3. *get_price_tool* - Get rental prices (strikethrough + discounted format).
4. *create_quote_tool* - Create bundle quotes.
5. *check_serviceability_tool* - Check pincode.
6. *get_trending_products_tool* - Recommend top items.
7. *search_company_knowledge_tool* - Company policies/FAQs.
8. *request_human_handoff_tool* - Escalate if user is confused or stuck.

## LEAD ENRICHMENT RULES
- If the user mentions a budget (e.g. "under 3000", "2-4k/month"), call `sync_lead_data_tool` with `budget_range={{"min": X, "max": Y}}`.
- If the user mentions preferences (AC, non-AC, furnished, bachelor, family, PG, office), call `sync_lead_data_tool` with `preferences_notes="..."`.
- When the customer states a rental duration (e.g. "4 months", "6 mo", "1 year"), ALWAYS call `sync_lead_data_tool` with `duration_months=N` to persist it.
- These should be synced at the same time as location/product updates — not as separate calls.

---

## SMART DEFAULTS (No Decimals)
- *Initial Pricing*: Show 12-month rate (cheapest) with 30% flat discount to hook the customer. Then ask for their preferred duration.
- *Duration*: Once the customer states a duration, use THAT duration for all subsequent pricing. If they haven't stated one yet, show 12-month prices as the best deal.
- *Quantity*: Always assume 1 unit per item.
- Format: `~X,XXX/mo~ Y,YYY/mo + GST` (full strikethrough, Indian Rupees included).

## CART DISPLAY RULES
- Always append `+ GST` after every price (both line items and total).
- Never show inline savings on line items — savings go only in the Total Savings line at the bottom.
- Quantity prefix: `Nx Item Name` (e.g., `2x Single Bed`). Default is `1x`.
- Savings = `(original x qty) - (discounted x qty)` per line, then summed.
- Use Indian currency format: X,XXX (commas).

## CUSTOMER INFO
- Phone: Always available in `collected_info['phone']`. Use this for `sync_lead_data_tool`.
- Name: If `collected_info['customer_name']` is empty, use the first greeting to capture it.

## TONE & STYLE
- Be extremely brief. WhatsApp is for scrolling, not reading essays.
- Do NOT use emojis in any responses. Keep tone professional and clean.
- *BOLDING*: Use single asterisk `*bold*`, never double `**`.

Remember: Keep the lead moving. Use `sync_lead_data_tool` at every major information capture.
"""


# ========================================
# AGENT GRAPH
# ========================================

# All tools the agent can use
ALL_TOOLS = [
    search_products_tool,
    get_price_tool,
    create_quote_tool,
    get_trending_products_tool,
    check_serviceability_tool,
    get_service_areas_tool,
    search_company_knowledge_tool,
    get_office_location_tool,
    request_human_handoff_tool,
    sync_lead_data_tool,
]


def create_sales_agent(checkpointer=None):
    """Create and return the sales agent graph."""
    
    # Initialize LLM with tools
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    
    # Tool dictionary for execution
    tools_dict = {tool.name: tool for tool in ALL_TOOLS}
    
    # ---- Node Functions ----
    
    def call_agent(state: ConversationState) -> Dict[str, Any]:
        """Call the LLM with current state and tools."""
        messages = list(state["messages"])
        
        # Inject collected info into system prompt context
        collected = state.get('collected_info', {})
        info_context = f"\n\n## Current Customer Context\n{collected}"

        # Highlight stored duration so the LLM uses it
        duration = collected.get('duration_months')
        if duration:
            info_context += (
                f"\n\n## MANDATORY RULE -- DURATION ALREADY KNOWN"
                f"\nThe customer has already confirmed a *{duration}-month* rental duration."
                f"\nYou MUST use {duration} months for ALL pricing, get_price_tool calls, and create_quote_tool calls."
                f"\nDo NOT ask 'How long do you need this for?' -- the duration is already known."
                f"\nDo NOT default to 12 months. Use {duration} months."
            )

        full_system_prompt = SYSTEM_PROMPT + info_context
        
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
            
            print(f"  🔧 Calling tool: {tool_name}")
            
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
        
        # Check if there are tool calls
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        
        return "end"
    
    # ---- Build Graph ----
    
    graph = StateGraph(ConversationState)
    
    # Add nodes
    graph.add_node("agent", call_agent)
    graph.add_node("tools", execute_tools)
    
    # Set entry point
    graph.set_entry_point("agent")
    
    # Add edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    graph.add_edge("tools", "agent")
    
    # Compile and return
    return graph.compile(checkpointer=checkpointer)


# ========================================
# AGENT RUNNER
# ========================================

def run_agent(user_message: str, state: ConversationState = None) -> tuple[str, ConversationState]:
    """
    Run the agent with a user message.
    
    Args:
        user_message: The user's message
        state: Optional existing conversation state
        
    Returns:
        Tuple of (agent response, updated state)
    """
    # Initialize state if needed
    if state is None:
        state = create_initial_state()
    
    # Add user message
    state["messages"] = list(state["messages"]) + [HumanMessage(content=user_message)]
    
    # Create and run agent
    agent = create_sales_agent()
    result = agent.invoke(state)
    
    # Extract response
    response = result["messages"][-1].content
    
    return response, result


# ========================================
# DEMO MODE
# ========================================

def demo_conversation():
    """Run an interactive demo conversation."""
    print("\n" + "="*50)
    print(f"  🤖 {BOT_NAME} - RentBasket WhatsApp Bot v1.0")
    print("="*50)
    print(f"\n{BOT_GREETING}")
    print("What would you like on rent today?\n")
    print("(Type 'quit' to exit)\n")
    
    state = create_initial_state()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["quit", "exit", "bye"]:
            print(f"\n{BOT_NAME}: Goodbye! Visit us at {WEBSITE} 👋")
            break
        
        if not user_input:
            continue
        
        print(f"\n{BOT_NAME}: (typing...)")
        
        try:
            response, state = run_agent(user_input, state)
            print(f"\n{BOT_NAME}: {response}\n")
        except Exception as e:
            print(f"\n{BOT_NAME}: Sorry, I encountered an error. Please try again or contact support.")
            print(f"  [Debug: {str(e)}]\n")


if __name__ == "__main__":
    demo_conversation()
