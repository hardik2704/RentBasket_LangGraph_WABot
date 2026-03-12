# Utils module exports
from .logger import (
    log_message,
    log_conversation_turn,
    log_system_message,
    log_demo_turn,
    get_conversation_history,
    start_new_session,
)

# DB-backed logger (graceful fallback to file-based if DATABASE_URL not set)
from .db_logger import (
    log_conversation_turn as db_log_conversation_turn,
    start_new_session as db_start_new_session,
    get_or_create_session,
    update_session,
    log_event,
    get_conversation_history as db_get_conversation_history,
)
