# Human Handoff Tool for RentBasket WhatsApp Bot
# Escalation to human agents for complex cases

from langchain_core.tools import tool

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALES_PHONE_GURGAON, SALES_PHONE_NOIDA, SUPPORT_EMAIL, WEBSITE


# Scenarios that should trigger human handoff
HANDOFF_TRIGGERS = [
    "price negotiation",
    "previous quote",
    "complaint",
    "damaged product",
    "refund",
    "angry customer",
    "bulk order",
    "special request",
    "corporate inquiry",
    "callback request",
]


@tool
def request_human_handoff_tool(reason: str, preferred_contact: str = "whatsapp") -> str:
    """
    Escalate conversation to a human sales agent.
    Use this when:
    - Customer is negotiating price or mentions old quotes
    - Customer has a complaint or is unhappy
    - Complex bulk orders (5+ items)
    - Customer explicitly asks to talk to a person
    - Situation requires human judgment
    
    Args:
        reason: Brief reason for handoff (e.g., "price negotiation", "complaint", "bulk order")
        preferred_contact: Customer's preferred contact method ("whatsapp", "call", "email")
    
    Returns:
        Handoff confirmation with contact details
    """
    reason_lower = reason.lower()
    
    # Price negotiation / old quote
    if any(word in reason_lower for word in ["price", "negotiat", "old", "previous", "quote", "discount", "pahle", "bola"]):
        return f"""
🙏 **I understand you're looking for the best deal!**

I'm raising a best-price request with our team. They'll review your requirements and offer the best available rate.

**How would you like to proceed?**
[SEND_HANDOFF_BUTTONS]
"""
    
    # Complaint or issue
    if any(word in reason_lower for word in ["complaint", "issue", "problem", "damaged", "broken", "not working", "angry", "unhappy"]):
        return f"""
🙏 **I apologize for the inconvenience!**

I'm escalating this to our support team for immediate attention.

**Please provide:**
• Your order ID (if you have one)
• Brief description of the issue
• Photos (if applicable)

**Priority Support Contacts:**
• 📞 Call: {SALES_PHONE_GURGAON}
• 📧 Email: {SUPPORT_EMAIL}
• 🌐 App: Report via RentBasket app

Our team will reach out within 24 hours.
"""
    
    # Bulk order
    if any(word in reason_lower for word in ["bulk", "multiple", "many", "office", "corporate", "5+", "10+"]):
        return f"""
🏢 **Thanks for your bulk order inquiry!**

For 5+ items or corporate orders, our senior sales team can offer:
• Special bulk pricing
• Priority delivery
• Dedicated account manager

**How would you like to proceed?**
[SEND_HANDOFF_BUTTONS]
"""
    
    # General human request
    if preferred_contact == "call":
        return f"""
📞 **Connecting you to our team!**

**How would you like to proceed?**
[SEND_HANDOFF_BUTTONS]
"""
    
    if preferred_contact == "email":
        return f"""
📧 **Email Support**

Reach us at: {SUPPORT_EMAIL}

Please include:
• Your name & phone number
• Requirements or concern
• Preferred callback time

We respond within 24 hours!
"""
    
    # Default WhatsApp handoff
    return f"""
👋 **I'll connect you with our team!**

A human agent will review this chat shortly.

**How would you like to proceed?**
[SEND_HANDOFF_BUTTONS]
"""


def should_trigger_handoff(message: str) -> bool:
    """
    Check if a message should trigger human handoff.
    
    Args:
        message: User message to analyze
        
    Returns:
        True if handoff should be triggered
    """
    message_lower = message.lower()
    
    # Check for explicit requests
    if any(phrase in message_lower for phrase in ["talk to human", "speak to person", "call me", "callback", "agent please"]):
        return True
    
    # Check for trigger scenarios
    return any(trigger in message_lower for trigger in HANDOFF_TRIGGERS)
