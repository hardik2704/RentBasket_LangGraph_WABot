"""
Tools for handling operational support requests (maintenance, billing, logistics).
Interacts with the operations_tickets table in the database.
"""

import os
import sys
from typing import Dict, Any, Optional

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db
from langchain_core.tools import tool
from datetime import datetime

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
    Log a new support ticket in Firestore for a customer issue.
    Types: maintenance, billing, relocation, closure.
    """
    db = get_db()
    if not db:
        return "⚠️ Ticketing system currently offline. We have noted your issue locally and our team will be notified! [SEND_HANDOFF_BUTTONS]"

    try:
        # Normalize phone for clean indexing
        import re
        clean = re.sub(r'\D', '', str(phone_number))
        normalized_phone = clean[-10:] if len(clean) >= 10 else clean

        # Create a new ticket document with auto-ID
        ticket_ref = db.collection("tickets").document()
        ticket_data = {
            "phone_number": normalized_phone,
            "issue_type": issue_type,
            "sub_intent": sub_intent,
            "summary": summary,
            "description": description,
            "priority": priority,
            "is_urgent": is_urgent,
            "escalation_flag": escalation_flag,
            "media_refs": media_refs,
            "status": "open",
            "created_at": datetime.utcnow()
        }
        
        ticket_ref.set(ticket_data)
        ticket_id = ticket_ref.id
        
        urgency_icon = "🔥" if is_urgent or priority == "high" else "📋"
        return f"✅ Ticket #{ticket_id} has been logged successfully. {urgency_icon} | Priority: {priority}"
        
    except Exception as e:
        print(f"⚠️ Error logging ticket to Firebase: {e}")
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
def check_ticket_status_tool(ticket_id: str) -> str:
    """
    Check the status of an existing support ticket in Firestore.
    """
    db = get_db()
    if not db:
        return "⚠️ Database unavailable."
        
    try:
        doc = db.collection("tickets").document(ticket_id).get()
        if doc.exists:
            data = doc.to_dict()
            status = data.get("status", "open")
            created = data.get("created_at")
            desc = data.get("description", "")
            
            created_str = created.strftime('%Y-%m-%d') if created else "Unknown"
            return f"🎫 Ticket #{ticket_id} Status: *{status.upper()}*\nLog Date: {created_str}\nIssue: {desc}"
        return "❌ Ticket ID not found."
    except Exception as e:
        return f"❌ Error checking ticket: {str(e)}"
