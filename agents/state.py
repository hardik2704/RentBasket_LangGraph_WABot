# Conversation State for RentBasket WhatsApp Bot
# Maintains state across the conversation

from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CollectedInfo(TypedDict, total=False):
    """Information collected during the conversation."""
    pincode: Optional[str]
    city: Optional[str]
    duration_months: Optional[int]
    items: List[Dict[str, Any]]  # For new leads: {product_id, product_name, quantity}
    is_serviceable: Optional[bool]
    customer_name: Optional[str]
    phone: Optional[str]
    is_bulk_order: bool
    special_requests: Optional[str]
    
    # --- Dual-Mode / Verification Upgrades ---
    customer_status: str              # active_customer, past_customer, lead, unknown
    is_verified_customer: bool        # Logic based on phone match
    customer_profile: Optional[Dict[str, Any]] # Full record from DB
    active_rentals: List[Dict[str, Any]] # List of items if active_customer
    last_button_selection: Optional[str] # WhatsApp interactive button ID
    workflow_stage: str               # e.g., "triage", "details", "confirmation"
    escalation_requested: bool        # Flag if user asked for human or is angry
    recent_summary: str               # 1-2 sentence summary of last 3 turns


class SupportContext(TypedDict, total=False):
    """Context for operational support issues."""
    issue_type: str               # maintenance, billing, relocation, closure
    sub_intent: str               # e.g., "washing_machine_not_working"
    priority_hint: str            # high, medium, low (extracted from sentiment/keywords)
    ticket_id: Optional[str]      # Assigned ticket ID if logged
    product_context: Optional[str] # The specific item the issue is about
    issue_description: str        # Summary of the problem
    is_escalated: bool            # True if user requested human or agent failed


class ConversationState(TypedDict):
    """
    Full conversation state for the sales and support agents.
    
    Attributes:
        messages: List of conversation messages (auto-accumulated)
        collected_info: Customer information collected during conversation
        needs_human: Flag to escalate to human agent
        conversation_stage: Current stage (greeting, inquiry, pricing, support_triage, handoff)
        support_context: Operational context for existing customers
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    collected_info: CollectedInfo
    needs_human: bool
    conversation_stage: str
    active_agent: str        # "sales" | "recommendation" | "support"
    support_context: SupportContext


def create_initial_state() -> ConversationState:
    """Create a fresh conversation state with support fields initialized."""
    return {
        "messages": [],
        "collected_info": {
            "items": [],
            "is_bulk_order": False,
            "is_verified_customer": False,
            "active_rentals": [],
            "customer_status": "unknown",
            "workflow_stage": "greeting",
            "escalation_requested": False,
            "recent_summary": "",
        },
        "needs_human": False,
        "conversation_stage": "greeting",
        "active_agent": "sales",
        "support_context": {
            "is_escalated": False,
            "issue_description": "",
        },
    }


def update_collected_info(
    state: ConversationState, 
    updates: Dict[str, Any]
) -> ConversationState:
    """Update collected info with new data."""
    new_info = {**state.get("collected_info", {}), **updates}
    return {**state, "collected_info": new_info}
