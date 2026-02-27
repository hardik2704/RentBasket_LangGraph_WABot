# Conversation Logger for RentBasket WhatsApp Bot
# Logs conversations in WhatsApp-like format to .txt files

import os
from datetime import datetime
from typing import Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LOGS_DIRECTORY, BOT_NAME


def ensure_logs_directory():
    """Create logs directory if it doesn't exist."""
    if not os.path.exists(LOGS_DIRECTORY):
        os.makedirs(LOGS_DIRECTORY)


def get_log_file_path(phone_number: str) -> str:
    """
    Get the path to the log file for a phone number.
    Standardizes on the 91 prefix for Indian numbers.
    """
    ensure_logs_directory()
    # Clean the phone number (remove spaces, symbols)
    clean = phone_number.replace(" ", "").replace("-", "").replace("+", "")
    
    # Standardize Indian numbers: if 10 digits, add 91. If 12 digits starting with 91, keep it.
    if len(clean) == 10:
        clean = "91" + clean
    elif len(clean) == 12 and clean.startswith("91"):
        pass 
    
    return os.path.join(LOGS_DIRECTORY, f"{clean}.txt")


def format_timestamp() -> str:
    """Get current timestamp in WhatsApp format: DD/MM/YY, HH:MM am/pm"""
    now = datetime.now()
    return now.strftime("%d/%m/%y, %I:%M %p").lower()


def log_message(
    phone_number: str, 
    sender_name: str, 
    message: str,
    is_bot: bool = False
) -> None:
    """
    Log a single message to the conversation file.
    """
    log_path = get_log_file_path(phone_number)
    timestamp = format_timestamp()
    
    # Ensure phone number is clean for display
    display_phone = phone_number.replace("+", "")
    if len(display_phone) == 10:
        display_phone = "91" + display_phone

    if is_bot:
        sender = BOT_NAME
    else:
        # Include both name and number for better tracking/knowledge
        name = sender_name or "User"
        sender = f"{name} ({display_phone})"
    
    # Format: DD/MM/YY, HH:MM am - Sender: Message
    log_entry = f"{timestamp} - {sender}: {message}\n"
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)


def log_conversation_turn(
    phone_number: str,
    user_name: str,
    user_message: str,
    bot_response: str
) -> None:
    """
    Log a complete conversation turn (user message + bot response).
    
    Args:
        phone_number: User's phone number
        user_name: User's name (from WhatsApp profile or phone number)
        user_message: What the user said
        bot_response: What the bot responded
    """
    # Log user message
    log_message(phone_number, user_name, user_message, is_bot=False)
    
    # Log bot response
    log_message(phone_number, BOT_NAME, bot_response, is_bot=True)


def log_system_message(phone_number: str, message: str) -> None:
    """
    Log a system message (like connection notices).
    
    Args:
        phone_number: User's phone number
        message: System message content
    """
    log_path = get_log_file_path(phone_number)
    timestamp = format_timestamp()
    
    # System messages in WhatsApp don't have a sender prefix
    log_entry = f"{timestamp} - {message}\n"
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)


def get_conversation_history(phone_number: str) -> Optional[str]:
    """
    Read the full conversation history for a phone number.
    
    Args:
        phone_number: User's phone number
        
    Returns:
        Full conversation log or None if not found
    """
    log_path = get_log_file_path(phone_number)
    
    if not os.path.exists(log_path):
        return None
    
    with open(log_path, "r", encoding="utf-8") as f:
        return f.read()


def start_new_session(phone_number: str, user_name: str = None) -> None:
    """
    Log the start of a new conversation session.
    
    Args:
        phone_number: User's phone number
        user_name: User's name if known
    """
    log_path = get_log_file_path(phone_number)
    timestamp = format_timestamp()
    
    # Add a session separator if file already exists
    if os.path.exists(log_path):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'-'*50}\n")
            f.write(f"{timestamp} - New session started\n")
    else:
        # First message in a new file
        with open(log_path, "w", encoding="utf-8") as f:
            name_display = user_name if user_name else phone_number
            f.write(f"Conversation with {name_display}\n")
            f.write(f"{'='*50}\n")


# Demo helper for terminal mode
def log_demo_turn(user_input: str, bot_response: str, session_id: str = "demo_user") -> None:
    """
    Log a demo conversation turn.
    
    Args:
        user_input: What the user typed
        bot_response: What the bot responded
        session_id: Session identifier (default: demo_user)
    """
    log_conversation_turn(
        phone_number=session_id,
        user_name="Demo User",
        user_message=user_input,
        bot_response=bot_response
    )
