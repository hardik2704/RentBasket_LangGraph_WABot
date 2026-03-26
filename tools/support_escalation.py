"""
Tools for Escalating Support Issues.
Formats the incident in a structured schema so humans can pick it up efficiently.
"""

from langchain_core.tools import tool
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALES_PHONE_GURGAON

@tool
def escalate_support_issue_tool(
    phone_number: str,
    customer_name: str,
    issue_type: str,
    urgency: str,
    summary: str,
    reason_for_escalation: str
) -> str:
    """
    Escalate a complex, angry, or policy-blocked customer issue to a human support agent.
    
    Args:
        phone_number: The customer's 10-digit number.
        customer_name: The customer's name.
        issue_type: Maintenance, Billing, Refund, etc.
        urgency: High, Medium, Low.
        summary: A 1-2 sentence description of the problem.
        reason_for_escalation: Why the bot couldn't solve it (e.g. "Angry customer", "Custom request", "System error").
        
    Returns:
        Structured message for the customer and an internal system log.
    """
    
    # In a real system, you would push this alert to Slack / Zendesk here.
    print("\n🚨 [HUMAN ESCALATION ALERT] 🚨")
    print(f"Customer: {customer_name} ({phone_number})")
    print(f"Urgency:  {urgency.upper()}")
    print(f"Issue:    {issue_type}")
    print(f"Summary:  {summary}")
    print(f"Reason:   {reason_for_escalation}")
    print("----------------------------------\n")
    
    # Safe output formatting for WhatsApp Customer Side
    return f"""
🙏 **I understand this requires special attention.**

I have immediately flagged this issue directly to our **Senior Escalation Team**.

**Escalation Protocol Activated:**
• Customer: {customer_name}
• Issue: {issue_type}
• Urgency: {urgency.upper()}

A specialist will review your case and message/call you within **24 hours**.
For immediate assistance, please call: {SALES_PHONE_GURGAON}.
"""
