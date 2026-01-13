# WhatsApp Business API Client for RentBasket Bot
# Ready for integration with Meta WhatsApp Cloud API

import os
import sys
import requests
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN


class WhatsAppClient:
    """
    WhatsApp Cloud API client for sending messages and managing conversations.
    
    To use this client with real WhatsApp:
    1. Create a Meta Business account
    2. Set up WhatsApp Business API
    3. Get Phone Number ID and Access Token
    4. Set environment variables:
       - WHATSAPP_PHONE_NUMBER_ID
       - WHATSAPP_ACCESS_TOKEN
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(
        self, 
        phone_number_id: str = None, 
        access_token: str = None,
        demo_mode: bool = True
    ):
        """
        Initialize WhatsApp client.
        
        Args:
            phone_number_id: WhatsApp Business Phone Number ID
            access_token: Meta Access Token
            demo_mode: If True, print messages instead of sending
        """
        self.phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        self.access_token = access_token or WHATSAPP_ACCESS_TOKEN
        self.demo_mode = demo_mode or not (self.phone_number_id and self.access_token)
        
        if self.demo_mode:
            print("📱 WhatsApp Client running in DEMO mode (messages printed to console)")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to WhatsApp."""
        if self.demo_mode:
            print(f"  [API] Would send to {endpoint}: {payload.get('type', 'message')}")
            return {"success": True, "demo": True}
        
        url = f"{self.BASE_URL}/{self.phone_number_id}/{endpoint}"
        response = requests.post(url, headers=self._get_headers(), json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return {"error": response.text}
    
    def send_text_message(
        self, 
        to_phone: str, 
        message: str,
        preview_url: bool = False
    ) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user.
        
        Args:
            to_phone: Recipient phone number (with country code, no +)
            message: Message text to send
            preview_url: Whether to show URL previews
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            # Pretty print for demo
            print(f"\n📤 To: {to_phone}")
            print(f"{'─'*40}")
            print(message)
            print(f"{'─'*40}")
            return {"success": True, "demo": True}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message
            }
        }
        
        return self._make_request("messages", payload)
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read (blue checkmarks).
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"  ✓✓ Marked as read: {message_id[:20]}...")
            return {"success": True, "demo": True}
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        return self._make_request("messages", payload)
    
    def send_typing_indicator(self, to_phone: str) -> None:
        """
        Send typing indicator (shows "typing..." to user).
        Note: WhatsApp Cloud API doesn't have native typing indicator support.
        This is a placeholder for custom implementations.
        
        Args:
            to_phone: Recipient phone number
        """
        if self.demo_mode:
            print(f"  ⌨️  Typing indicator sent to {to_phone}")
        # In real implementation, you might use a workaround or third-party service
    
    def send_interactive_buttons(
        self,
        to_phone: str,
        body_text: str,
        buttons: list,
        header: str = None,
        footer: str = None
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons.
        
        Args:
            to_phone: Recipient phone number
            body_text: Main message body
            buttons: List of buttons [{"id": "btn_1", "title": "Button 1"}, ...]
            header: Optional header text
            footer: Optional footer text
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"\n📤 To: {to_phone}")
            print(f"{'─'*40}")
            if header:
                print(f"**{header}**")
            print(body_text)
            print("\n[Buttons]")
            for btn in buttons:
                print(f"  [{btn['title']}]")
            if footer:
                print(f"\n_{footer}_")
            print(f"{'─'*40}")
            return {"success": True, "demo": True}
        
        button_list = [
            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
            for b in buttons[:3]  # Max 3 buttons
        ]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": button_list}
            }
        }
        
        if header:
            payload["interactive"]["header"] = {"type": "text", "text": header}
        if footer:
            payload["interactive"]["footer"] = {"text": footer}
        
        return self._make_request("messages", payload)
    
    def send_list_message(
        self,
        to_phone: str,
        body_text: str,
        button_text: str,
        sections: list,
        header: str = None,
        footer: str = None
    ) -> Dict[str, Any]:
        """
        Send an interactive list message.
        
        Args:
            to_phone: Recipient phone number
            body_text: Main message body
            button_text: Text on the list button
            sections: List of sections with rows
            header: Optional header text
            footer: Optional footer text
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"\n📤 To: {to_phone}")
            print(f"{'─'*40}")
            if header:
                print(f"**{header}**")
            print(body_text)
            print(f"\n[📋 {button_text}]")
            for section in sections:
                print(f"\n{section.get('title', 'Options')}:")
                for row in section.get('rows', []):
                    print(f"  • {row['title']}")
            if footer:
                print(f"\n_{footer}_")
            print(f"{'─'*40}")
            return {"success": True, "demo": True}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        
        if header:
            payload["interactive"]["header"] = {"type": "text", "text": header}
        if footer:
            payload["interactive"]["footer"] = {"text": footer}
        
        return self._make_request("messages", payload)


# Webhook handler for incoming messages
def parse_webhook_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse incoming webhook payload from WhatsApp.
    
    Args:
        payload: Raw webhook payload
        
    Returns:
        Parsed message dict or None if not a message
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        messages = value.get("messages", [])
        if not messages:
            return None
        
        message = messages[0]
        contact = value.get("contacts", [{}])[0]
        
        return {
            "message_id": message.get("id"),
            "from_phone": message.get("from"),
            "from_name": contact.get("profile", {}).get("name"),
            "timestamp": message.get("timestamp"),
            "type": message.get("type"),
            "text": message.get("text", {}).get("body") if message.get("type") == "text" else None,
            "interactive": message.get("interactive") if message.get("type") == "interactive" else None,
        }
    except Exception as e:
        print(f"Error parsing webhook: {e}")
        return None
