"""
Database-backed conversation logger for RentBasket WhatsApp Bot.
Drop-in replacement for utils/logger.py — same function signatures.
Falls back to file-based logging if DATABASE_URL is not set.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_NAME
from utils.firebase_client import get_db, log_session_msg, log_event as firebase_log_event

# Import file-based logger as fallback
from utils import logger as file_logger


# ========================================
# SESSION MANAGEMENT
# ========================================

def start_new_session(phone_number: str, user_name: str = None) -> Optional[str]:
    """
    Start a new conversation session in Firestore.
    Returns the session_id (string) if Firebase is available.
    """
    # Always do file-based logging too (as backup)
    file_logger.start_new_session(phone_number, user_name)

    db = get_db()
    if not db:
        return None

    try:
        # Create a new document with an auto-generated ID
        session_ref = db.collection("sessions").document()
        session_ref.set({
            "phone_number": phone_number,
            "user_name": user_name,
            "created_at": datetime.now(timezone.utc),
            "last_active_at": datetime.now(timezone.utc),
            "total_messages": 0,
            "conversation_stage": "greeting",
            "active_agent": "orchestrator",
            "is_active": True
        })
        return session_ref.id
    except Exception as e:
        print(f"⚠️  Firebase start_new_session error: {e}")
        return None


def get_or_create_session(phone_number: str, user_name: str = None) -> Optional[int]:
    """
    Get the most recent active session for this phone, or create a new one.
    A session is considered active if last message was within 30 minutes.
    """
    if not is_db_available():
        return None

    try:
        row = execute_query_one(
            """SELECT id FROM sessions
               WHERE phone_number = %s
                 AND last_active_at > NOW() - INTERVAL '30 minutes'
               ORDER BY last_active_at DESC
               LIMIT 1""",
            (phone_number,),
        )
        if row:
            return row[0]
        return start_new_session(phone_number, user_name)
    except Exception as e:
        print(f"⚠️  DB get_or_create_session error: {e}")
        return None


def update_session(
    session_id: str,
    conversation_stage: str = None,
    active_agent: str = None,
    collected_info: dict = None,
    needs_human: bool = None,
    handoff_reason: str = None,
) -> None:
    """Update session metadata in Firestore."""
    db = get_db()
    if not db or session_id is None:
        return

    try:
        updates = {
            "last_active_at": datetime.now(timezone.utc),
            "total_messages": firestore.Increment(1)
        }

        if conversation_stage is not None:
            updates["conversation_stage"] = conversation_stage

        if active_agent is not None:
            updates["active_agent"] = active_agent

        if needs_human is not None:
            updates["needs_human"] = needs_human

        if handoff_reason is not None:
            updates["handoff_reason"] = handoff_reason

        if collected_info:
            # Flatten or nest collected info
            info_updates = {}
            for key in ["pincode", "city", "duration_months", "is_bulk_order"]:
                if key in collected_info:
                    info_updates[key] = collected_info[key]
            
            if "items" in collected_info:
                info_updates["items"] = collected_info["items"]
            
            if info_updates:
                updates["collected_info"] = info_updates

        db.collection("sessions").document(session_id).update(updates)
    except Exception as e:
        print(f"⚠️  Firebase update_session error: {e}")


# ========================================
# MESSAGE LOGGING
# ========================================

def log_message(
    phone_number: str,
    sender_name: str,
    message: str,
    is_bot: bool = False,
    session_id: str = None,
    agent_used: str = None,
    tools_called: List[str] = None,
    intent: str = None,
    wa_message_id: str = None,
    quoted_message_id: str = None,
    reaction_emoji: str = None,
) -> None:
    """
    Log a single message to Firestore (and file as backup).
    """
    # Always write to file too (as backup)
    file_logger.log_message(phone_number, sender_name, message, is_bot)

    db = get_db()
    if not db or session_id is None:
        return

    try:
        sender = "bot" if is_bot else "user"
        log_session_msg(session_id, {
            "phone": phone_number,
            "sender": sender,
            "sender_name": sender_name if not is_bot else BOT_NAME,
            "message": message,
            "wa_message_id": wa_message_id,
            "agent_used": agent_used,
            "tools_called": tools_called,
            "intent": intent,
            "quoted_message_id": quoted_message_id,
            "reaction_emoji": reaction_emoji
        })
    except Exception as e:
        print(f"⚠️  Firebase log_message error: {e}")


def log_conversation_turn(
    phone_number: str,
    user_name: str,
    user_message: str,
    bot_response: str,
    session_id: str = None,
    agent_used: str = None,
    tools_called: List[str] = None,
    intent: str = None,
    wa_message_id: str = None,
    quoted_message_id: str = None,
    reaction_emoji: str = None,
) -> None:
    """
    Log a complete conversation turn (user message + bot response) to Firestore.
    """
    # Always write to file too (as reliable backup)
    file_logger.log_conversation_turn(phone_number, user_name, user_message, bot_response,
                                     agent_used=agent_used)

    db = get_db()
    if not db or session_id is None:
        return

    try:
        # 1. Log user message
        log_session_msg(session_id, {
            "phone": phone_number,
            "sender": "user",
            "sender_name": user_name,
            "message": user_message,
            "wa_message_id": wa_message_id,
            "intent": intent,
            "quoted_message_id": quoted_message_id,
            "reaction_emoji": reaction_emoji
        })
        
        # 2. Log bot response
        log_session_msg(session_id, {
            "phone": phone_number,
            "sender": "bot",
            "sender_name": BOT_NAME,
            "message": bot_response,
            "agent_used": agent_used,
            "tools_called": tools_called
        })
    except Exception as e:
        print(f"⚠️  Firebase log_conversation_turn error: {e}")


def log_system_message(
    phone_number: str,
    message: str,
    session_id: str = None,
) -> None:
    """Log a system message (e.g., session start) to Firestore."""
    file_logger.log_system_message(phone_number, message)

    db = get_db()
    if not db or session_id is None:
        return

    try:
        log_session_msg(session_id, {
            "phone": phone_number,
            "sender": "system",
            "sender_name": "system",
            "message": message
        })
    except Exception as e:
        print(f"⚠️  Firebase log_system_message error: {e}")


# ========================================
# ANALYTICS EVENTS
# ========================================

def log_event(
    phone_number: str,
    event_type: str,
    event_data: dict = None,
    session_id: str = None,
) -> None:
    """
    Log a business event for analytics to Firestore.
    """
    db = get_db()
    if not db:
        return

    try:
        firebase_log_event(phone_number, event_type, event_data, session_id)
    except Exception as e:
        print(f"⚠️  Firebase log_event error: {e}")


# ========================================
# QUERY HELPERS
# ========================================

def get_conversation_history(phone_number: str) -> Optional[str]:
    """
    Get formatted conversation history from Firestore.
    """
    db = get_db()
    if not db:
        return file_logger.get_conversation_history(phone_number)

    try:
        # 1. Find the latest session for this phone
        query = db.collection("sessions") \
                  .where("phone_number", "==", phone_number) \
                  .order_by("last_active_at", direction=firestore.Query.DESCENDING) \
                  .limit(1)
        
        sessions = query.get()
        if not sessions:
            return file_logger.get_conversation_history(phone_number)
            
        # 2. Get messages from sub-collection
        session_id = sessions[0].id
        messages = db.collection("sessions").document(session_id) \
                     .collection("messages") \
                     .order_by("timestamp", direction=firestore.Query.ASCENDING) \
                     .get()
        
        if not messages:
            return file_logger.get_conversation_history(phone_number)

        lines = []
        for m_doc in messages:
            m = m_doc.to_dict()
            ts = m.get("timestamp")
            ts_str = ts.strftime("%d/%m/%y, %I:%M %p").lower() if ts else ""
            lines.append(f"{ts_str} - {m.get('sender_name')}: {m.get('message')}")
        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️  Firebase get_conversation_history error: {e}")
        return file_logger.get_conversation_history(phone_number)
