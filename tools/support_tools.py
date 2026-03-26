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
    sub_intent: Optional[str] = None,
    priority: str = "medium",
    is_urgent: bool = False
) -> str:
    """
    Log a new support ticket in the database for a customer issue.
    Types: maintenance, billing, relocation, closure.
    
    Args:
        phone_number: Customer's phone number
        issue_type: Category of the issue
        description: Detailed summary of the problem
        sub_intent: Specific sub-category (optional)
        priority: high, medium, low
        is_urgent: True if it requires immediate attention
        
    Returns:
        A message with the Ticket ID or error.
    """
    if not is_db_available():
        return "⚠️ Database unavailable. Please note your issue and I will report it manually."

    # First, find the customer_id associated with the phone
    cust_query = "SELECT id FROM customers WHERE phone_number = %s OR phone_number = %s LIMIT 1;"
    clean_phone = phone_number.replace("+", "").strip()
    short_phone = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
    
    try:
        cust_row = execute_query_one(cust_query, (clean_phone, short_phone))
        customer_id = cust_row[0] if cust_row else None
        
        insert_query = """
        INSERT INTO operations_tickets (customer_id, phone_number, issue_type, sub_intent, description, priority, is_urgent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        
        ticket_id_row = execute_query_one(insert_query, (
            customer_id, 
            clean_phone, 
            issue_type, 
            sub_intent, 
            description, 
            priority, 
            is_urgent
        ))
        
        if ticket_id_row:
            ticket_id = ticket_id_row[0]
            return f"✅ Ticket #{ticket_id} has been logged successfully. Our operations team is on it! | Priority: {priority}"
        return "❌ Failed to log ticket."
        
    except Exception as e:
        print(f"⚠️ Error logging ticket: {e}")
        return f"❌ Error logging ticket: {str(e)}"

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
