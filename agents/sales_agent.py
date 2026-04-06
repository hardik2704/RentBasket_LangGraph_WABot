# Sales Agent for RentBasket WhatsApp Bot "Ku"
# Combines RAG knowledge retrieval with ReAct tool calling

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from config import LLM_MODEL, LLM_TEMPERATURE, BOT_NAME, BOT_GREETING
from config import SALES_PHONE_GURGAON, SALES_PHONE_NOIDA, SUPPORT_EMAIL, WEBSITE
from config import GURGAON_OFFICE, NOIDA_OFFICE
from agents.state import ConversationState, create_initial_state
from rag.vectorstore import search_knowledge, create_knowledge_vectorstore
from tools.product_tools import (
    search_products_tool,
    get_price_tool,
    create_quote_tool,
    get_trending_products_tool,
    generate_cart_link_tool,
)
from tools.location_tools import check_serviceability_tool, get_service_areas_tool
from tools.lead_tools import sync_lead_data_tool
from tools.human_handoff import request_human_handoff_tool
from tools.office_tools import get_office_location_tool


# ========================================
# KNOWLEDGE RETRIEVAL TOOL
# ========================================

_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        print("Initializing knowledge base vector store...")
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

SYSTEM_PROMPT = f"""You are *Ku*, RentBasket's WhatsApp Sales Agent. Your job: qualify leads and close carts in 4-5 messages. Be brief. Be fast.

---

## QUALIFICATION FLOW (follow strictly, in order)

### Step 1 — Intent & Name Capture
- If customer name is NOT in Customer Context, start with: "Hi! I'm Ku from RentBasket. May I know your name?" then ask what they want to rent.
- If name IS known, greet by name and ask what they want to rent.
- *Action*: Call `sync_lead_data_tool` with `extracted_name` (if captured) and `preferences_notes` describing their intent (e.g. "wants sofa and bed, setting up 2BHK").

### Step 2 — Show Best Prices
- Search and show top 2-3 matching products with cheapest prices (12-month rate with 30% discount).
- If duration NOT known: append "How long do you need this for?"
- If duration IS known from Customer Context: use it directly, do NOT ask again.
- *Action*: Call `sync_lead_data_tool` with `product_preferences` (list of dicts with product_id and name).

### Step 3 — Duration Confirmation & Adjusted Prices
- SKIP entirely if duration was already known from Customer Context.
- Only if customer just now gave duration: show recalculated prices for that duration.
- *Action*: Call `sync_lead_data_tool` with `duration_months`.

### Step 4 — Final Close (Cart)
- Call `create_quote_tool` with all selected product_ids (comma-separated) and the confirmed duration.
- The tool appends [SEND_CART_BUTTONS] automatically.
- *Action*: Call `sync_lead_data_tool` with `lead_stage`='cart_created' AND `final_cart` as a list of dicts, each with `product_id`, `quantity`, and `duration`. Build this list from the same product_ids and quantities you passed to `create_quote_tool`.

### Step 5 — Location & Serviceability (triggered after cart is shown)
- Triggered when: customer clicks Reserve Now (you receive "I want to reserve and proceed with the order"), or says "Yes"/"Confirm"/"Proceed" after seeing the cart.
- If pincode IS already in Customer Context: call `check_serviceability_tool` directly, skip asking.
- If pincode NOT known: ask "Where should we deliver? Please share your 6-digit pincode."
- Call `check_serviceability_tool` with the pincode once received.
- *Action*: Call `sync_lead_data_tool` with `delivery_location={{"pincode": "XXXXXX"}}` and `lead_stage`='qualified'.

### Step 6 — Final Cart Link (ALWAYS sent, regardless of serviceability)
- IMMEDIATELY after `check_serviceability_tool` returns — do NOT wait for another customer message.
- Call `generate_cart_link_tool` with the EXACT same `product_ids` string and `duration` that were used in `create_quote_tool` (see Cart Context below if injected).
- Then output your final response in this EXACT format using `|||` as the separator between the two messages:

  IF SERVICEABLE:
  "Since you completed the discussion with our Bot Ku, I want to give you an additional discount of 5%.|||[paste the link returned by generate_cart_link_tool here, nothing else]"

  IF NOT SERVICEABLE:
  "Your area is currently outside our delivery range. [paste the NOT_SERVICEABLE details from check_serviceability_tool]. We have shared the cart below so you can see the full pricing and keep it ready.|||[paste the link returned by generate_cart_link_tool here, nothing else]"

- CRITICAL: The `|||` separates two WhatsApp messages. Do NOT add any other text before or after the link in Message B.
- Call `sync_lead_data_tool` with `lead_stage`='reserved'.

---

## YOUR TOOLS
1. *sync_lead_data_tool* — MANDATORY at every major step. Syncs name, location, preferences, cart, duration, lead_stage to Firestore.
2. *search_products_tool* — Find products by name or keyword.
3. *get_price_tool* — Get rental price with discount breakdown.
4. *create_quote_tool* — Build and display the full cart. ALWAYS use this for any cart display.
5. *generate_cart_link_tool* — Generate dynamic checkout link. Call at Step 6.
6. *check_serviceability_tool* — Check if a pincode is deliverable.
7. *get_service_areas_tool* — Show all serviceable cities (when customer asks).
8. *get_trending_products_tool* — Get trending items by category.
9. *get_office_location_tool* — Share office address (when customer asks).
10. *search_company_knowledge_tool* — Company policies, T&C, FAQs.
11. *request_human_handoff_tool* — Escalate to human agent.

---

## LEAD ENRICHMENT RULES
- Budget mentioned (e.g. "under 3000"): call `sync_lead_data_tool` with `budget_range={{"min": X, "max": Y}}`.
- Preferences mentioned (AC, furnished, PG, office, bachelor): call with `preferences_notes="..."`.
- Duration confirmed: ALWAYS call with `duration_months=N`.
- Batch syncs — combine into one `sync_lead_data_tool` call, never multiple calls for the same turn.

## SMART DEFAULTS
- Pricing: Show 12-month rate with 30% discount as "Starting from ₹X/mo".
- Duration: Once stated, use it everywhere. Never re-ask.
- Quantity: Assume 1 unit per item unless specified.
- Format: `~X,XXX/mo~ ₹Y,YYY/mo + GST` (strikethrough original, bold discounted).

## CRITICAL CART RULES
- NEVER write cart text manually. ALWAYS use `create_quote_tool`.
- To ADD items to existing cart: pass ALL product IDs (old + new) in one string.
- To REMOVE items: pass only the remaining IDs.
- Multiple quantities: repeat the ID. Example: 2x product 1034 = `"1034,1034"`.
- One-time charges (security, delivery, installation) and savings are cumulative — the tool handles this.

## TONE & STYLE
- Be extremely brief. WhatsApp is not email.
- No emojis. Professional and clean.
- Bold with single asterisk `*bold*`, never double `**`.
- Never ask two questions in one message.
"""


# ========================================
# ALL TOOLS
# ========================================

ALL_TOOLS = [
    search_products_tool,
    get_price_tool,
    create_quote_tool,
    get_trending_products_tool,
    generate_cart_link_tool,
    check_serviceability_tool,
    get_service_areas_tool,
    get_office_location_tool,
    search_company_knowledge_tool,
    request_human_handoff_tool,
    sync_lead_data_tool,
]


# ========================================
# AGENT GRAPH (singleton — compiled once)
# ========================================

_sales_agent_singleton = None


def _get_sales_agent(checkpointer=None):
    """Return the compiled sales agent, building it once as a module-level singleton."""
    global _sales_agent_singleton
    if _sales_agent_singleton is not None and checkpointer is None:
        return _sales_agent_singleton

    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    tools_dict = {t.name: t for t in ALL_TOOLS}

    # ---- Node: call LLM ----
    def call_agent(state: ConversationState) -> Dict[str, Any]:
        messages = list(state["messages"])
        collected = state.get("collected_info", {})

        # ── Selective context injection (only sales-relevant fields) ──
        ctx_fields = {
            k: v for k, v in collected.items()
            if k in (
                "customer_name", "phone", "duration_months", "pincode", "city",
                "customer_status", "workflow_stage", "_last_lead_stage",
                "is_bulk_order", "special_requests", "budget_range",
            ) and v
        }
        info_context = f"\n\n## Customer Context\n{ctx_fields}"

        # ── Duration rule (mandatory injection) ──
        duration = collected.get("duration_months")
        if duration:
            info_context += (
                f"\n\n## RULE — DURATION ALREADY KNOWN"
                f"\nCustomer confirmed *{duration} months*. Use this for ALL pricing and tool calls."
                f"\nDo NOT ask 'How long?' again."
            )

        # ── Cart rule (scan message history for the most recent create_quote_tool call) ──
        cart_product_ids = None
        cart_duration = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    if tc["name"] == "create_quote_tool":
                        cart_product_ids = tc["args"].get("product_ids")
                        cart_duration = tc["args"].get("duration", duration or 12)
                        break
            if cart_product_ids:
                break

        if cart_product_ids:
            info_context += (
                f"\n\n## RULE — CART ALREADY BUILT"
                f"\nCart was created with product_ids='{cart_product_ids}' and duration={cart_duration} months."
                f"\nWhen calling generate_cart_link_tool, use EXACTLY product_ids='{cart_product_ids}' and duration={cart_duration}."
                f"\nDo NOT approximate or change these values."
            )

        full_prompt = SYSTEM_PROMPT + info_context
        response = llm_with_tools.invoke([SystemMessage(content=full_prompt)] + messages)
        return {"messages": [response]}

    # ---- Node: execute tools ----
    def execute_tools(state: ConversationState) -> Dict[str, Any]:
        last_message = state["messages"][-1]
        results = []
        for tc in last_message.tool_calls:
            tool_name = tc["name"]
            print(f"  Tool: {tool_name}")
            try:
                result = tools_dict[tool_name].invoke(tc["args"]) if tool_name in tools_dict else f"Tool '{tool_name}' not found."
            except Exception as e:
                result = f"Error executing {tool_name}: {str(e)}"
            results.append(ToolMessage(tool_call_id=tc["id"], name=tool_name, content=str(result)))
        return {"messages": results}

    # ---- Edge: loop or end ----
    def should_continue(state: ConversationState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    # ---- Build graph ----
    graph = StateGraph(ConversationState)
    graph.add_node("agent", call_agent)
    graph.add_node("tools", execute_tools)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    compiled = graph.compile(checkpointer=checkpointer, recursion_limit=10)

    if checkpointer is None:
        _sales_agent_singleton = compiled

    return compiled


# ========================================
# AGENT RUNNER

# Public alias — kept for backwards compatibility with agents/__init__.py and main.py
def create_sales_agent(checkpointer=None):
    """Public wrapper around the singleton builder. Returns the compiled agent."""
    return _get_sales_agent(checkpointer=checkpointer)

# ========================================

def run_agent(user_message: str, state: ConversationState = None) -> tuple[str, ConversationState]:
    """
    Run the sales agent for one user turn.

    Returns:
        Tuple of (response string, updated state)
    """
    if state is None:
        state = create_initial_state()

    state["messages"] = list(state["messages"]) + [HumanMessage(content=user_message)]

    agent = _get_sales_agent()
    result = agent.invoke(state)

    response = result["messages"][-1].content
    return response, result


# ========================================
# DEMO MODE
# ========================================

def demo_conversation():
    """Run an interactive demo conversation."""
    print("\n" + "=" * 50)
    print(f"  {BOT_NAME} - RentBasket WhatsApp Bot")
    print("=" * 50)
    print(f"\n{BOT_GREETING}")
    print("(Type 'quit' to exit)\n")

    state = create_initial_state()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "bye"]:
            print(f"\n{BOT_NAME}: Goodbye! Visit us at {WEBSITE}")
            break
        if not user_input:
            continue

        print(f"\n{BOT_NAME}: (typing...)")
        try:
            response, state = run_agent(user_input, state)
            print(f"\n{BOT_NAME}: {response}\n")
        except Exception as e:
            print(f"\n{BOT_NAME}: Sorry, encountered an error. Please try again.")
            print(f"  [Debug: {str(e)}]\n")


if __name__ == "__main__":
    demo_conversation()
