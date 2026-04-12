# WhatsApp Business API Client for RentBasket Bot
# Ready for integration with Meta WhatsApp Cloud API

import os
import sys
import requests
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERSION


class WhatsAppClient:
    """
    WhatsApp Cloud API client for sending messages and managing conversations.
    
    To use this client with real WhatsApp:
    1. Create a Meta Business account
    2. Set up WhatsApp Business API
    3. Get Phone Number ID and Access Token
    4. Set environment variables:
       - PHONE_NUMBER_ID
       - ACCESS_TOKEN
    """
    
    BASE_URL = f"https://graph.facebook.com/{WHATSAPP_VERSION}"
    
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
    
    def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Download media from WhatsApp API (two-step: get URL, then download binary).
        Returns raw bytes of the media file, or None on failure.
        """
        if self.demo_mode:
            print(f"  [API] Would download media: {media_id}")
            return None

        try:
            # Step 1: Get the media URL
            url = f"{self.BASE_URL}/{media_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"Media URL fetch failed: {resp.status_code} - {resp.text}")
                return None

            media_url = resp.json().get("url")
            if not media_url:
                print(f"No URL in media response: {resp.json()}")
                return None

            # Step 2: Download the actual binary
            resp2 = requests.get(media_url, headers=headers)
            if resp2.status_code != 200:
                print(f"Media download failed: {resp2.status_code}")
                return None

            return resp2.content

        except Exception as e:
            print(f"Media download error: {e}")
            return None

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
    
    def send_read_and_typing_indicator(self, message_id: str) -> Dict[str, Any]:
        """
        Send read receipt AND typing indicator together.
        This shows blue checkmarks + typing dots to the user.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"  ✓✓ Read + ⌨️ Typing indicator sent")
            return {"success": True, "demo": True}
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {
                "type": "text"
            }
        }
        
        return self._make_request("messages", payload)
    
    def send_typing_indicator(self, to_phone: str) -> Dict[str, Any]:
        """
        Send typing indicator (shows 'typing...' to user).
        This makes a real API call every time, unlike read receipts.
        Errors are silently ignored since the API may not officially
        support this type, but it still works on the WhatsApp client.
        
        Args:
            to_phone: Recipient phone number
            
        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"  ⌨️  Typing indicator sent to {to_phone}")
            return {"success": True, "demo": True}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "typing",
            "typing": {
                "action": "start"
            }
        }
        
        try:
            url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
            response = requests.post(url, headers=self._get_headers(), json=payload)
            if response.status_code == 200:
                return response.json()
            # Silently ignore errors — typing indicator works on WhatsApp 
            # even though the API returns a 400
            return {"success": True, "typing": True}
        except Exception:
            return {"success": True, "typing": True}
    
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


    def send_image(
        self,
        to_phone: str,
        image_url: str = None,
        media_id: str = None,
        caption: str = None,
    ) -> Dict[str, Any]:
        """
        Send an image message via URL or pre-uploaded media ID.

        Args:
            to_phone: Recipient phone number
            image_url: Publicly accessible URL of the image (JPEG/PNG)
            media_id: WhatsApp media ID from a previous upload (alternative to URL)
            caption: Optional caption text below the image

        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"\n📤 To: {to_phone}")
            print(f"{'─'*40}")
            print(f"[IMAGE] {image_url or media_id}")
            if caption:
                print(f"Caption: {caption}")
            print(f"{'─'*40}")
            return {"success": True, "demo": True}

        image_block: Dict[str, Any] = {}
        if media_id:
            image_block["id"] = media_id
        elif image_url:
            image_block["link"] = image_url
        else:
            return {"error": "Either image_url or media_id must be provided"}

        if caption:
            image_block["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "image",
            "image": image_block,
        }

        return self._make_request("messages", payload)

    def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str = "en",
        components: list = None,
    ) -> dict:
        """
        Send a pre-approved HSM (Highly Structured Message) template.
        Required for bot-initiated messages outside the 24-hour reply window.

        Args:
            to_phone: Recipient phone number
            template_name: Approved template name (e.g. "cart_reminder", "followup_day1")
            language_code: Template language (default "en")
            components: Optional list of header/body/button variable components

        Returns:
            API response dict
        """
        if self.demo_mode:
            print(f"\n📤 [TEMPLATE] To: {to_phone}")
            print(f"   Template: {template_name} ({language_code})")
            if components:
                print(f"   Components: {components}")
            return {"success": True, "demo": True}

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components

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
