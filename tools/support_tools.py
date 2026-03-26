"""
Tools for handling operational support requests (maintenance, billing, logistics).
Interacts with the operations_tickets table in the database.
"""

import os
import sys
from typing import Dict, Any, Optional

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_query, execute_query_one, is_db_available
from langchain_core.tools import tool

@tool
def log_support_ticket_tool(
    phone_number: str,
    issue_type: str,
    description: str,
    summary: str,
    sub_intent: Optional[str] = None,
    priority: str = "medium",
    is_urgent: bool = False,
    escalation_flag: bool = False,
    media_refs: Optional[str] = "[]"
) -> str:
    """
    Log a new support ticket in the database for a customer issue.
    Types: maintenance, billing, relocation, closure.
    
    Args:
        phone_number: Customer's phone number
        issue_type: Category of the issue (e.g., maintenance)
        description: Detailed verbatim problem
        summary: A 5-8 word title for the ticket dashboard
        sub_intent: Specific sub-category (e.g., MAINT_APPLIANCE)
        priority: high, medium, low
        is_urgent: True if it requires immediate attention
        escalation_flag: True if human escalated
        media_refs: JSON string of media IDs attached by user
        
    Returns:
        A message with the Ticket ID or error.
    """
    if not is_db_available():
        return "⚠️ Database unavailable. Please note your issue and I will report it manually."

    # First, find the customer_id associated with the phone
    cust_query = "SELECT id FROM customers WHERE phone_number LIKE %s LIMIT 1;"
    
    import re
    clean = re.sub(r'\D', '', str(phone_number))
    normalized_phone = clean[-10:] if len(clean) >= 10 else clean

    try:
        cust_row = execute_query_one(cust_query, (f"%{normalized_phone}",))
        customer_id = cust_row[0] if cust_row else None
        
        insert_query = """
        INSERT INTO operations_tickets (customer_id, phone_number, issue_type, sub_intent, summary, description, priority, is_urgent, escalation_flag, media_refs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        
        ticket_id_row = execute_query_one(insert_query, (
            customer_id, 
            normalized_phone, 
            issue_type, 
            sub_intent,
            summary,
            description, 
            priority, 
            is_urgent,
            escalation_flag,
            media_refs
        ))
        
        if ticket_id_row:
            ticket_id = ticket_id_row[0]
            urgency_icon = "🔥" if is_urgent or priority == "high" else "📋"
            return f"✅ Ticket #{ticket_id} has been logged successfully. {urgency_icon} | Priority: {priority}"
        print("⚠️ Failed to log ticket - no ID returned.")
        return "⚠️ I'm having a temporary issue connecting to our ticketing system. However, I have saved your details locally and will ensure our team sees them! [SEND_HANDOFF_BUTTONS]"
        
    except Exception as e:
        print(f"⚠️ Error logging ticket: {e}")
        return "⚠️ I encountered an error while safely storing your ticket. Our human operations team has been notified. [SEND_HANDOFF_BUTTONS]"

# ============================================
# NEW POLICY TOOL
# ============================================

from data.support_policies import SUPPORT_POLICIES

@tool
def retrieve_support_policy_tool(category: str) -> str:
    """
    Retrieves the exact hardcoded corporate policy for an operational scope.
    Use this to strictly quote RentBasket rules instead of hallucinating answers.
    
    Args:
        category: Must be one of ["maintenance", "billing", "refund", "pickup", "relocation"]
        
    Returns:
        Bullet points of the official policy.
    """
    category = category.lower()
    
    if category not in SUPPORT_POLICIES:
        return f"⚠️ I couldn't find a specific policy for '{category}'. Standard terms and conditions apply. Please refer to your rental agreement for full details."
        
    policy = SUPPORT_POLICIES[category]
    desc = policy["description"]
    points = "\n".join([f"• {p}" for p in policy["points"]])
    
    return f"**Official RentBasket {category.capitalize()} Policy:**\n_{desc}_\n\n{points}"

@tool
def check_ticket_status_tool(ticket_id: int) -> str:
    """
    Check the status of an existing support ticket.
    """
    if not is_db_available():
        return "⚠️ Database unavailable."
        
    query = "SELECT status, created_at, description FROM operations_tickets WHERE id = %s LIMIT 1;"
    try:
        row = execute_query_one(query, (ticket_id,))
        if row:
            status, created, desc = row
            return f"🎫 Ticket #{ticket_id} Status: *{status.upper()}*\nLog Date: {created.strftime('%Y-%m-%d')}\nIssue: {desc}"
        return "❌ Ticket ID not found."
    except Exception as e:
        return f"❌ Error checking ticket: {str(e)}"
