"""
Support Agent for RentBasket WhatsApp Bot "Ku"
Handles maintenance, billing, relocation, and operations for existing customers.
Now upgraded with a Hybrid interactive (Button/List) and Free Text flow.
"""

import os
import sys
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import LLM_MODEL, LLM_TEMPERATURE, BOT_NAME
from agents.state import ConversationState, create_initial_state
from tools.support_tools import log_support_ticket_tool, retrieve_support_policy_tool
from tools.support_escalation import escalate_support_issue_tool

# ========================================
# HYBRID STATE MACHINE LOGIC
# ========================================

def run_support_agent(user_message: str, state: ConversationState = None) -> tuple[str, ConversationState]:
    """
    Run the support agent.
    If the user clicks a button, we process it deterministically.
    If they type free text, we use the LLM guided by the current workflow_stage.
    """
    if state is None:
        state = create_initial_state()
        
    # Ensure support context exists
    if "support_context" not in state:
        state["support_context"] = {}
        
    msg = user_message.strip()
    stage = state["collected_info"].get("workflow_stage", "greeting")
    
    # ---------------------------------------------
    # 1. BUTTON / EXPLICIT INTENT ROUTING
    # ---------------------------------------------
    
    # Main Menu Actions
    if msg == "SUP_TYPE_MAINTENANCE":
        state["collected_info"]["workflow_stage"] = "awaiting_maint_type"
        state["support_context"]["issue_type"] = "maintenance"
        return "[SEND_SUPPORT_LIST:MAINTENANCE_MENU]", state
        
    elif msg == "SUP_TYPE_BILLING":
        state["collected_info"]["workflow_stage"] = "awaiting_billing_type"
        state["support_context"]["issue_type"] = "billing"
        return "[SEND_SUPPORT_LIST:BILLING_MENU]", state
        
    elif msg == "SUP_TYPE_REFUND":
        state["collected_info"]["workflow_stage"] = "awaiting_refund_type"
        state["support_context"]["issue_type"] = "refund"
        return "[SEND_SUPPORT_LIST:REFUND_MENU]", state
        
    elif msg == "SUP_TYPE_PICKUP":
        state["collected_info"]["workflow_stage"] = "awaiting_pickup_type"
        state["support_context"]["issue_type"] = "pickup"
        return "[SEND_SUPPORT_LIST:PICKUP_MENU]", state
        
    elif msg == "SUP_TYPE_RELOCATION":
        state["collected_info"]["workflow_stage"] = "awaiting_relocation_type"
        state["support_context"]["issue_type"] = "relocation"
        return "[SEND_SUPPORT_LIST:RELOCATION_MENU]", state
        
    elif msg in ("SUP_TALK_TEAM", "ESCALATION"):
        state["collected_info"]["workflow_stage"] = "escalated"
        state["support_context"]["is_escataled"] = True
        return process_escalation(state, "Customer explicitly requested human agent.")

    # Maintenance Flow Actions
    if msg.startswith("MAINT_"):
        state["support_context"]["sub_intent"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_maint_product"
        
        # Dynamically build a product selection list based on active_rentals
        active_rentals = state["collected_info"].get("active_rentals", [])
        if active_rentals:
            rows = [{"id": f"PROD_{item['id']}", "title": item['name'][:24]} for item in active_rentals]
            rows.append({"id": "PROD_OTHER", "title": "Other / Not Listed"})
            
            # Since we can't hardcode dynamic JSONs in menus.py, we return a special dynamic tag
            # But the simplest text fallback for now that WhatsApp supports without complex list building:
            active_list_str = "\n".join([f"• {r['title']}" for r in rows])
            return f"Which item needs maintenance?\nPlease type the name of the item:\n\n{active_list_str}", state
        else:
            return "Which item needs maintenance? Please type its name.", state
            
    if msg.startswith("PROD_") or (stage == "awaiting_maint_product"):
        state["support_context"]["product_context"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_maint_severity"
        return "[SEND_SUPPORT_BUTTONS:MAINTENANCE_SEVERITY_BUTTONS|🔧 How severe is the damage?|Please let us know so we can prioritize the technician visit.|]", state

    if msg.startswith("SEV_"):
        state["support_context"]["priority_hint"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_issue_desc"
        return "Could you briefly type out the exact problem you're facing? (e.g., 'The washing machine is making a loud noise')", state

    # Billing Flow Actions
    if msg.startswith("BILL_"):
        state["support_context"]["sub_intent"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_issue_desc"
        return "Please type a short description of your query, and I'll pull up the billing policy for you! 💳", state

    # Refund Flow Actions
    if msg.startswith("REF_"):
        state["support_context"]["sub_intent"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_issue_desc"
        return "Please provide any relevant details (like your closure date), and I'll verify the refund status parameters! 💸", state

    # Pickup Flow Actions
    if msg.startswith("PICK_"):
        state["support_context"]["sub_intent"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_issue_desc"
        return "Got it. When would you ideally like the pickup to happen? Please type your request. 🚚", state

    # Relocation Actions
    if msg.startswith("MOVE_"):
        state["support_context"]["sub_intent"] = msg
        state["collected_info"]["workflow_stage"] = "awaiting_issue_desc"
        return "Where are you moving to? Please type your new Pincode and a brief query. 🏠", state

    # Media Capture Actions
    if msg == "SUP_WILL_SEND":
        state["collected_info"]["workflow_stage"] = "awaiting_media"
        return "Great! Please upload the photo/video here in chat. 📸", state
        
    if msg == "SUP_NO_PHOTO":
        state["collected_info"]["workflow_stage"] = "ready_to_log"
        return process_ticket_logging(state)


    # ---------------------------------------------
    # 2. FREE TEXT / HYBRID LLM AGENT ROUTING
    # ---------------------------------------------
    
    # If the user is just saying "help", show the main menu
    if stage in ("greeting", "triage") and not state["support_context"].get("issue_type"):
        return "[SEND_SUPPORT_LIST:MAIN_SUPPORT_MENU]", state

    # If we were awaiting a description, process it via LLM + Policy Tool
    if stage == "awaiting_issue_desc":
        state["support_context"]["issue_description"] = msg
        
        # Call LLM strictly to check policy and summarize
        response_text = call_policy_llm(state)
        
        # After giving policy info, ask for photo if it's maintenance/damage
        if state["support_context"].get("issue_type") == "maintenance":
            state["collected_info"]["workflow_stage"] = "awaiting_photo_decision"
            return response_text + "\n\n[SEND_SUPPORT_BUTTONS:MEDIA_REQUEST_BUTTONS|📸 Photo Request|Do you have a photo or video of the issue so our technicians can prepare the right parts?|]", state
        else:
            state["collected_info"]["workflow_stage"] = "ready_to_log"
            ticket_msg, state = process_ticket_logging(state)
            return response_text + "\n\n" + ticket_msg, state

    # If awaiting media but they typed text
    if stage == "awaiting_media":
        state["collected_info"]["workflow_stage"] = "ready_to_log"
        return process_ticket_logging(state)

    # Fallback to general LLM chatting
    response_text = call_policy_llm(state)
    return response_text, state


def call_policy_llm(state: ConversationState) -> str:
    """Invokes the LLM strictly to look up policies and formulate a polite response."""
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1) # Low temp for strict policy adherence
    llm_with_tools = llm.bind_tools([retrieve_support_policy_tool])
    
    issue_type = state["support_context"].get("issue_type", "general")
    desc = state["support_context"].get("issue_description", "")
    
    prompt = f"""You are {BOT_NAME}, RentBasket's Operations Assistant.
    
    The customer has described an issue regarding: {issue_type.upper()}.
    Description: "{desc}"
    
    YOUR GOAL: Provide a helpful, policy-backed response.
    
    RULES:
    1. ALWAYS use the `retrieve_support_policy_tool` to look up the rule for {issue_type}.
    2. Do NOT invent policies. If the tool says 7 days, you say 7 days.
    3. Do NOT waive fees or promise instant refunds.
    4. Keep the message under 3 sentences. Be polite and use emojis.
    5. Don't mention that you are opening a ticket, the system will append that automatically.
    """
    
    messages = [SystemMessage(content=prompt), HumanMessage(content="Please review my issue.")]
    result = llm_with_tools.invoke(messages)
    
    if result.tool_calls:
        # Execute tool
        tool_call = result.tool_calls[0]
        tool_res = retrieve_support_policy_tool.invoke(tool_call["args"])
        messages.append(AIMessage(content="", tool_calls=result.tool_calls))
        messages.append(HumanMessage(content=f"Tool Output:\n{tool_res}\n\nNow provide the final short response to the user."))
        final_result = llm.invoke(messages)
        return final_result.content
        
    return result.content


def process_ticket_logging(state: ConversationState) -> tuple[str, ConversationState]:
    """Logs the ticket deterministically and updates state."""
    phone = state["collected_info"].get("phone", "Unknown")
    issue_type = state["support_context"].get("issue_type", "unknown")
    sub_intent = state["support_context"].get("sub_intent", "unknown")
    desc = state["support_context"].get("issue_description", "No description provided.")
    priority = "high" if state["support_context"].get("priority_hint") == "SEV_UNUSABLE" else "medium"
    
    ticket_msg = log_support_ticket_tool.invoke({
        "phone_number": phone,
        "issue_type": issue_type,
        "description": desc,
        "summary": f"{issue_type} - {sub_intent}",
        "sub_intent": sub_intent,
        "priority": priority,
        "is_urgent": priority == "high",
        "escalation_flag": False,
        "media_refs": "[]"
    })
    
    state["collected_info"]["workflow_stage"] = "ticket_logged"
    return ticket_msg, state


def process_escalation(state: ConversationState, reason: str) -> tuple[str, ConversationState]:
    """Handles structured escalation output."""
    phone = state["collected_info"].get("phone", "Unknown")
    name = state["collected_info"].get("customer_name", "Customer")
    issue_type = state["support_context"].get("issue_type", "General Support")
    desc = state["support_context"].get("issue_description", "-")
    
    esc_msg = escalate_support_issue_tool.invoke({
        "phone_number": phone,
        "customer_name": name,
        "issue_type": issue_type,
        "urgency": "high",
        "summary": desc,
        "reason_for_escalation": reason
    })
    
    state["collected_info"]["workflow_stage"] = "escalated"
    return esc_msg, state
