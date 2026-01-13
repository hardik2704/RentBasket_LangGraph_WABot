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
    items: List[Dict[str, Any]]  # List of {product_id, product_name, quantity}
    is_serviceable: Optional[bool]
    customer_name: Optional[str]
    phone: Optional[str]
    is_bulk_order: bool
    special_requests: Optional[str]


class ConversationState(TypedDict):
    """
    Full conversation state for the sales agent.
    
    Attributes:
        messages: List of conversation messages (auto-accumulated)
        collected_info: Customer information collected during conversation
        needs_human: Flag to escalate to human agent
        conversation_stage: Current stage (greeting, inquiry, quote, checkout)
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    collected_info: CollectedInfo
    needs_human: bool
    conversation_stage: str  # greeting, inquiry, pricing, quote, handoff


def create_initial_state() -> ConversationState:
    """Create a fresh conversation state."""
    return {
        "messages": [],
        "collected_info": {
            "items": [],
            "is_bulk_order": False,
        },
        "needs_human": False,
        "conversation_stage": "greeting"
    }


def update_collected_info(
    state: ConversationState, 
    updates: Dict[str, Any]
) -> ConversationState:
    """Update collected info with new data."""
    new_info = {**state.get("collected_info", {}), **updates}
    return {**state, "collected_info": new_info}
