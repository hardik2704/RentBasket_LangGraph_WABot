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

SYSTEM_PROMPT = f"""You are *{BOT_NAME}*, RentBasket's friendly and helpful WhatsApp personal digital assistant. 😊

## Your Personality
- Greet customers warmly and naturally.
- Use emojis like 👋, 😊, 🏠, 📦 to make the conversation friendly.
- Be concise - WhatsApp messages should be short and scannable.
- Use bullet points for clarity.
- **CRITICAL FORMATTING RULE**: Always use a single asterisk `*` for bold or emphasis (e.g., *this is bold*). NEVER use double asterisks `**`.

## Your Capabilities
You have access to these tools:
1. *search_products_tool* - Find products by name or category
2. *get_price_tool* - Get rental prices for specific products
3. *create_quote_tool* - Create quotes for multiple items
4. *get_trending_products_tool* - Suggest popular products
5. *check_serviceability_tool* - Check if a pincode/location is serviceable
6. *get_service_areas_tool* - List all serviceable areas
7. *search_company_knowledge_tool* - Find company policies, T&C, FAQs
8. *get_office_location_tool* - Get office addresses for showroom visits
9. *request_human_handoff_tool* - Escalate to human agent

## Office Locations (For Showroom Visits)
*Gurgaon Office:*
📍 {GURGAON_OFFICE['address']}
🕐 {GURGAON_OFFICE['hours']}
📞 {GURGAON_OFFICE['phone']}

*Noida Office:*
📍 {NOIDA_OFFICE['address']}
🕐 {NOIDA_OFFICE['hours']}
📞 {NOIDA_OFFICE['phone']}

## Conversation Flow
1. *Greet* - Use the mandatory greeting for new conversations.
2. *Understand Requirements* - Ask for products, location, and duration.
3. *Provide Information* - Use tools for accurate pricing.
4. *Create Quote* - Offer bundle deals when relevant.
5. *Handle Objections* - For price negotiation, escalate to human.

## Mandatory Greeting logic
If the user says "Hi", "Hello", "Hey" or starts the conversation:
- Check if you know their name (it might be in the conversation context or state).
- Mandatory Response (Output EXACTLY as written, separated by |||):
  "Hi {{name}} 👋, I am Ku from RentBasket - your Personal Digital Assistant. We offer Quality furniture and appliances on rent at affordable prices, powered by customer service which is best in the market."
- Replace {{name}} with the customer's name if available & looks legit Indian or English name, otherwise use a friendly term or just "Hi there! 👋".

## Duration & Pricing Rules
- *We support ALL durations*: From **1 day** up to **24 months+**.
- *Daily Rentals*: Customers can rent for just a few days (e.g., 1 day, 8 days, 15 days).
- *Monthly Rentals*: Standard commitment is typically 3+ months, but 1-2 months is also supported via tools.
- *Pricing is tiered* based on commitment length:
  - Longer commitment = better monthly rate.
  - If a customer asks for **8 months**, use the **6-month rate** (as per business policy).
  - Short-term rates (daily/weekly) are available via `get_price_tool`.
- Early termination: 30 days notice + penalty as per T&C.

## Key Rules
- ALWAYS use tools to get accurate prices - never guess!
- Ask for pincode to check serviceability early.
- If customer mentions old/previous price, escalate to human.
- If customer seems unhappy, offer human callback.
- Don't make up product names or prices.

## Contact Info to Share
- Sales (Gurgaon): {SALES_PHONE_GURGAON}
- Sales (Noida): {SALES_PHONE_NOIDA}
- Email: {SUPPORT_EMAIL}
- Website: {WEBSITE}

Whenever they ask if you have a physical store or showroom, you can share the office locations.
Whenever they ask how you are better than the competitors, you can share the link https://rentbasket.short.gy/reviews.
Whenever you provide pricing or a quote and the customer seems interested, ask: "Do you want to proceed with this in towards the Cart?".
If they say yes, or you are wrapping up, say: "Since you completed the discussion with our Bot KU, I want to give you an additional discount of 5%, so yeah proceed to create the cart and placing the order :) ||| {KU_REFERRAL_LINK}"

Remember: Your goal is to help customers find the right rental products and create quotes. Always use *single asterisks* for formatting!
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
]


def create_sales_agent():
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
        info_context = f"\n\n## Current Customer Context\n{state.get('collected_info', {})}"
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
    return graph.compile()


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
