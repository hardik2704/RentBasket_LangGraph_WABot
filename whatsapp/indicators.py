# Read and Typing Indicators for WhatsApp Bot
# Manages showing "read" and "typing..." status to users

import time
import threading
from typing import Callable, Optional

from .client import WhatsAppClient


class IndicatorManager:
    """
    Manages read receipts and typing indicators for WhatsApp conversations.
    
    Usage:
        manager = IndicatorManager(whatsapp_client)
        
        # Mark message as read immediately
        manager.mark_read(message_id)
        
        # Show typing while processing
        with manager.typing_context(phone_number):
            response = agent.process(message)
        
        # Or manually
        manager.start_typing(phone_number)
        response = agent.process(message)
        manager.stop_typing(phone_number)
    """
    
    def __init__(self, client: WhatsAppClient):
        """
        Initialize indicator manager.
        
        Args:
            client: WhatsApp client instance
        """
        self.client = client
        self._typing_threads = {}
        self._typing_active = {}
    
    def mark_read(self, message_id: str) -> None:
        """
        Mark a message as read (blue checkmarks).
        Should be called immediately when message is received.
        
        Args:
            message_id: ID of the received message
        """
        self.client.mark_as_read(message_id)
    
    def send_typing(self, to_phone: str) -> None:
        """
        Send a single typing indicator.
        
        Args:
            to_phone: Recipient phone number
        """
        self.client.send_typing_indicator(to_phone)
    
    def start_typing(self, to_phone: str, interval: float = 3.0) -> None:
        """
        Start sending typing indicators at regular intervals.
        Call stop_typing() when done.
        
        Args:
            to_phone: Recipient phone number
            interval: Seconds between typing indicators
        """
        if to_phone in self._typing_active and self._typing_active[to_phone]:
            return  # Already typing
        
        self._typing_active[to_phone] = True
        
        def typing_loop():
            while self._typing_active.get(to_phone, False):
                self.send_typing(to_phone)
                time.sleep(interval)
        
        thread = threading.Thread(target=typing_loop, daemon=True)
        self._typing_threads[to_phone] = thread
        thread.start()
    
    def stop_typing(self, to_phone: str) -> None:
        """
        Stop sending typing indicators for a phone number.
        
        Args:
            to_phone: Recipient phone number
        """
        self._typing_active[to_phone] = False
        
        if to_phone in self._typing_threads:
            # Thread will stop on next iteration
            del self._typing_threads[to_phone]
    
    def typing_context(self, to_phone: str, interval: float = 3.0):
        """
        Context manager for showing typing indicator during processing.
        
        Usage:
            with manager.typing_context(phone):
                response = agent.process(message)
        
        Args:
            to_phone: Recipient phone number
            interval: Seconds between typing indicators
            
        Returns:
            Context manager
        """
        return TypingContext(self, to_phone, interval)


class TypingContext:
    """Context manager for typing indicators."""
    
    def __init__(self, manager: IndicatorManager, to_phone: str, interval: float):
        self.manager = manager
        self.to_phone = to_phone
        self.interval = interval
    
    def __enter__(self):
        self.manager.start_typing(self.to_phone, self.interval)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.stop_typing(self.to_phone)
        return False


# Demo mode helpers for terminal simulation

def simulate_read_indicator():
    """Print simulated read indicator for demo mode."""
    print("  ✓✓ Read")


def simulate_typing_indicator(duration: float = 1.0):
    """
    Print simulated typing indicator for demo mode.
    
    Args:
        duration: How long to show typing (seconds)
    """
    print("  ⌨️  Typing", end="", flush=True)
    for _ in range(int(duration * 2)):
        time.sleep(0.5)
        print(".", end="", flush=True)
    print()
