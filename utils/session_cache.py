"""
Lightweight session cache for RentBasket WhatsApp Bot.
Stores compact operational facts for a 24-hour window to keep the bot contextually aware
without bloating the main conversation history or DB state.
"""

import time
from typing import Dict, Any, Optional

class SessionCache:
    """
    A simple in-memory cache for short-term conversation facts.
    In production, this would use Redis.
    """
    _cache: Dict[str, Dict[str, Any]] = {}
    _expiry_seconds: int = 86400  # 24 hours

    @classmethod
    def set(cls, phone: str, facts: Dict[str, Any]):
        """Store or update session facts for a phone number (normalized)."""
        if phone not in cls._cache:
            cls._cache[phone] = {
                "created_at": time.time(),
                "data": {}
            }
        
        # Update existing data with new flags/facts
        cls._cache[phone]["data"].update(facts)
        cls._cache[phone]["updated_at"] = time.time()

    @classmethod
    def get(cls, phone: str) -> Dict[str, Any]:
        """Retrieve session facts if valid and not expired."""
        entry = cls._cache.get(phone)
        if not entry:
            return {}
        
        # Check expiry
        if time.time() - entry["created_at"] > cls._expiry_seconds:
            del cls._cache[phone]
            return {}
            
        return entry.get("data", {})

    @classmethod
    def get_fact(cls, phone: str, key: str, default: Any = None) -> Any:
        """Get a specific fact for a user."""
        return cls.get(phone).get(key, default)

    @classmethod
    def clear(cls, phone: str):
        """Remove cache for a specific user."""
        if phone in cls._cache:
            del cls._cache[phone]

# Helpers for common fact capture
def update_user_facts(phone: str, **kwargs):
    """
    Capture useful operational facts.
    
    Expected facts:
    - customer_name, customer_status
    - primary_intent, support_sub_intent
    - severity (high/medium/low)
    - frustration_flag (true/false)
    - media_presence (true/false)
    - workflow_stage, active_agent
    """
    SessionCache.set(phone, kwargs)
