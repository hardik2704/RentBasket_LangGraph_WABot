"""
Database-backed conversation logger for RentBasket WhatsApp Bot.
Drop-in replacement for utils/logger.py — same function signatures.
Falls back to file-based logging if DATABASE_URL is not set.
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_NAME
from utils.db import is_db_available, execute_query, execute_query_one

# Import file-based logger as fallback
from utils import logger as file_logger


# ========================================
# SESSION MANAGEMENT
# ========================================

def start_new_session(phone_number: str, user_name: str = None) -> Optional[int]:
    """
    Start a new conversation session.
    Returns the session_id if DB is available.
    """
    # Always do file-based logging too (as backup)
    file_logger.start_new_session(phone_number, user_name)

    if not is_db_available():
        return None

    try:
        row = execute_query_one(
            """INSERT INTO sessions (phone_number, user_name)
               VALUES (%s, %s)
               RETURNING id""",
            (phone_number, user_name),
        )
        return row[0] if row else None
    except Exception as e:
        print(f"⚠️  DB start_new_session error: {e}")
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
    session_id: int,
    conversation_stage: str = None,
    active_agent: str = None,
    collected_info: dict = None,
    needs_human: bool = None,
    handoff_reason: str = None,
) -> None:
    """Update session metadata from ConversationState."""
    if not is_db_available() or session_id is None:
        return

    try:
        updates = ["last_active_at = NOW()"]
        params = []

        if conversation_stage is not None:
            updates.append("conversation_stage = %s")
            params.append(conversation_stage)

        if active_agent is not None:
            updates.append("active_agent = %s")
            params.append(active_agent)

        if needs_human is not None:
            updates.append("needs_human = %s")
            params.append(needs_human)

        if handoff_reason is not None:
            updates.append("handoff_reason = %s")
            params.append(handoff_reason)

        if collected_info:
            if collected_info.get("pincode"):
                updates.append("pincode = %s")
                params.append(collected_info["pincode"])
            if collected_info.get("city"):
                updates.append("city = %s")
                params.append(collected_info["city"])
            if collected_info.get("duration_months"):
                updates.append("duration_months = %s")
                params.append(collected_info["duration_months"])
            if collected_info.get("items"):
                updates.append("items = %s")
                params.append(json.dumps(collected_info["items"]))
            if collected_info.get("is_bulk_order"):
                updates.append("is_bulk_order = %s")
                params.append(collected_info["is_bulk_order"])

        # Increment message count
        updates.append("total_messages = total_messages + 1")

        params.append(session_id)
        execute_query(
            f"UPDATE sessions SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )
    except Exception as e:
        print(f"⚠️  DB update_session error: {e}")


# ========================================
# MESSAGE LOGGING
# ========================================

def log_message(
    phone_number: str,
    sender_name: str,
    message: str,
    is_bot: bool = False,
    session_id: int = None,
    agent_used: str = None,
    tools_called: List[str] = None,
    intent: str = None,
    wa_message_id: str = None,
    quoted_message_id: str = None,
    reaction_emoji: str = None,
) -> None:
    """
    Log a single message to the database (and file as backup).
    Drop-in compatible with logger.log_message().
    """
    # Always write to file too
    file_logger.log_message(phone_number, sender_name, message, is_bot)

    if not is_db_available():
        return

    try:
        sender = "bot" if is_bot else "user"
        execute_query(
            """INSERT INTO messages
               (session_id, phone_number, sender, sender_name, message,
                wa_message_id, agent_used, tools_called, intent,
                quoted_message_id, reaction_emoji)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                session_id,
                phone_number,
                sender,
                sender_name if not is_bot else BOT_NAME,
                message,
                wa_message_id,
                agent_used,
                tools_called,  # PostgreSQL TEXT[] accepts Python list
                intent,
                quoted_message_id,
                reaction_emoji
            ),
        )
    except Exception as e:
        print(f"⚠️  DB log_message error: {e}")


def log_conversation_turn(
    phone_number: str,
    user_name: str,
    user_message: str,
    bot_response: str,
    session_id: int = None,
    agent_used: str = None,
    tools_called: List[str] = None,
    intent: str = None,
    wa_message_id: str = None,
    quoted_message_id: str = None,
    reaction_emoji: str = None,
) -> None:
    """
    Log a complete conversation turn (user message + bot response).
    Uses a single transaction for atomicity and efficiency.
    """
    # Always write to file too (as reliable backup)
    file_logger.log_conversation_turn(phone_number, user_name, user_message, bot_response)

    if not is_db_available():
        return

    from utils.db import get_connection, put_connection

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 1. Log user message
            cur.execute(
                """INSERT INTO messages
                   (session_id, phone_number, sender, sender_name, message,
                    wa_message_id, intent, quoted_message_id, reaction_emoji)
                   VALUES (%s, %s, 'user', %s, %s, %s, %s, %s, %s)""",
                (session_id, phone_number, user_name, user_message, wa_message_id, intent, quoted_message_id, reaction_emoji),
            )
            
            # 2. Log bot response
            cur.execute(
                """INSERT INTO messages
                   (session_id, phone_number, sender, sender_name, message,
                    agent_used, tools_called)
                   VALUES (%s, %s, 'bot', %s, %s, %s, %s)""",
                (
                    session_id,
                    phone_number,
                    BOT_NAME,
                    bot_response,
                    agent_used,
                    tools_called,
                ),
            )
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"⚠️  DB log_conversation_turn error: {e}")
    finally:
        if conn:
            put_connection(conn)


def log_system_message(
    phone_number: str,
    message: str,
    session_id: int = None,
) -> None:
    """Log a system message (e.g., session start)."""
    file_logger.log_system_message(phone_number, message)

    if not is_db_available():
        return

    try:
        execute_query(
            """INSERT INTO messages
               (session_id, phone_number, sender, sender_name, message)
               VALUES (%s, %s, 'system', 'system', %s)""",
            (session_id, phone_number, message),
        )
    except Exception as e:
        print(f"⚠️  DB log_system_message error: {e}")


# ========================================
# ANALYTICS EVENTS
# ========================================

def log_event(
    phone_number: str,
    event_type: str,
    event_data: dict = None,
    session_id: int = None,
) -> None:
    """
    Log a business event for analytics.

    Event types:
        - pricing_negotiation
        - human_handoff
        - quote_created
        - pincode_check
        - product_search
        - button_pressed
        - support_ticket_created
        - support_escalation
    """
    if not is_db_available():
        return

    try:
        execute_query(
            """INSERT INTO analytics_events
               (phone_number, session_id, event_type, event_data)
               VALUES (%s, %s, %s, %s)""",
            (phone_number, session_id, event_type, json.dumps(event_data or {})),
        )
    except Exception as e:
        print(f"⚠️  DB log_event error: {e}")


# ========================================
# QUERY HELPERS
# ========================================

def get_conversation_history(phone_number: str) -> Optional[str]:
    """
    Get formatted conversation history for a phone number.
    Falls back to file if DB not available.
    """
    if not is_db_available():
        return file_logger.get_conversation_history(phone_number)

    try:
        rows = execute_query(
            """SELECT sender_name, message, timestamp
               FROM messages
               WHERE phone_number = %s
               ORDER BY timestamp ASC""",
            (phone_number,),
            fetch=True,
        )
        if not rows:
            return file_logger.get_conversation_history(phone_number)

        lines = []
        for sender_name, message, ts in rows:
            ts_str = ts.strftime("%d/%m/%y, %I:%M %p").lower() if ts else ""
            lines.append(f"{ts_str} - {sender_name}: {message}")
        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️  DB get_conversation_history error: {e}")
        return file_logger.get_conversation_history(phone_number)
