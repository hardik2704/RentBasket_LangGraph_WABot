"""
Edge Case Tests for RentBasket WhatsApp Bot.

Tests system stability under adversarial/unexpected inputs:
malformed payloads, empty messages, gibberish, XSS, concurrency,
deduplication, and exception handling.

All tests are @pytest.mark.unit.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from conftest import build_webhook_payload


# ============================================================
# PAYLOAD EDGE CASES
# ============================================================

class TestPayloadEdgeCases:
    """Test webhook behavior with malformed or unusual payloads."""

    @pytest.mark.unit
    def test_empty_payload(self, client, mock_whatsapp):
        """Empty JSON body should return 200 without crashing."""
        resp = client.post("/webhook", data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_no_entry_field(self, client, mock_whatsapp):
        """Payload missing 'entry' key should return 200 (no_message)."""
        resp = client.post(
            "/webhook",
            data=json.dumps({"object": "whatsapp_business_account"}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_empty_messages_array(self, client, mock_whatsapp):
        """Payload with empty messages array should return 200."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [],
                                "messages": [],
                            },
                            "field": "messages",
                        }
                    ]
                }
            ],
        }
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_status_update_payload(self, client, mock_whatsapp, mock_agent):
        """
        WhatsApp sends status updates (delivered, read) -- these have 'statuses'
        instead of 'messages'. Should NOT call agent.
        """
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "123", "phone_number_id": "123"},
                                "statuses": [
                                    {
                                        "id": "wamid.status_123",
                                        "status": "delivered",
                                        "timestamp": "1234567890",
                                        "recipient_id": "919958448249",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ]
                }
            ],
        }
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
        mock_agent.assert_not_called()

    @pytest.mark.unit
    def test_non_json_body(self, client, mock_whatsapp):
        """Non-JSON body should not crash the server."""
        resp = client.post("/webhook", data="this is not json", content_type="text/plain")
        # Might return 400 or 500 but should NOT crash
        assert resp.status_code in (200, 400, 415, 500)

    @pytest.mark.unit
    def test_interactive_button_payload(self, client, mock_whatsapp, mock_agent):
        """Interactive button reply payload (HOW_RENTING_WORKS) should be handled."""
        payload = build_webhook_payload(
            msg_type="interactive",
            interactive={
                "type": "button_reply",
                "button_reply": {"id": "HOW_RENTING_WORKS", "title": "How Renting Works?"},
            },
        )
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_interactive_callback_button(self, client, mock_whatsapp, mock_agent):
        """TALK_TO_TEAM callback button should return 200."""
        payload = build_webhook_payload(
            msg_type="interactive",
            interactive={
                "type": "button_reply",
                "button_reply": {"id": "TALK_TO_TEAM", "title": "Talk to Team"},
            },
        )
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200


# ============================================================
# MESSAGE CONTENT EDGE CASES
# ============================================================

class TestMessageContentEdgeCases:
    """Test with unusual message content."""

    @pytest.mark.unit
    def test_empty_text_message(self, conversation):
        """Empty string message should not crash."""
        conversation.send("")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_very_long_message(self, conversation):
        """5000+ character message should process without crash."""
        long_msg = "I need furniture for my house. " * 200  # ~6000 chars
        conversation.send(long_msg)
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_gibberish_message(self, conversation):
        """Random gibberish should not crash."""
        conversation.send("asdkjhaskjdhkajshd kzxcnvkjzxnv")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_emoji_only_message(self, conversation):
        """Emoji-only message should process."""
        conversation.send("👍🏠🛋️")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_xss_attempt(self, conversation):
        """XSS-like input should be harmless."""
        conversation.send('<script>alert("xss")</script>')
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_sql_injection_attempt(self, conversation):
        """SQL injection attempt should be harmless."""
        conversation.send("'; DROP TABLE users; --")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_multiple_questions_one_message(self, conversation):
        """Multiple questions in one message should process once."""
        conversation.send("What sofas do you have? Also what's the price of fridge? And do you deliver to Noida?")
        assert conversation.last_status_code == 200
        assert conversation.mock_agent.call_count == 1

    @pytest.mark.unit
    def test_special_characters(self, conversation):
        """Special characters should not crash."""
        conversation.send("Price ₹500? 100% discount? #1 rated! @mention &more")
        assert conversation.last_status_code == 200


# ============================================================
# CONCURRENCY & STATE EDGE CASES
# ============================================================

class TestConcurrencyEdgeCases:
    """Test concurrency safety, deduplication, and state isolation."""

    @pytest.mark.unit
    def test_deduplication_same_msg_id(self, client, mock_whatsapp, mock_agent):
        """Same message_id sent twice should be deduplicated."""
        msg_id = "wamid.DUPE_TEST_001"
        # Use non-greeting text to ensure it goes through to the agent path
        payload = build_webhook_payload(text="Need sofa for my living room", msg_id=msg_id)

        resp1 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        resp2 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Second request should be deduped
        resp2_json = resp2.get_json()
        assert resp2_json.get("status") == "duplicate"

    @pytest.mark.unit
    def test_state_isolation_between_phones(self, make_conversation):
        """Two different phone numbers should have independent states."""
        session1 = make_conversation(phone="919900001111")
        session2 = make_conversation(phone="919900002222")

        session1.send("Need sofa")
        session2.send("Need fridge")

        # Both should have their own state
        assert session1.state is not None
        assert session2.state is not None
        assert session1.phone != session2.phone

    @pytest.mark.unit
    def test_rapid_sequential_same_phone(self, client, mock_whatsapp, mock_agent, payload_factory):
        """Multiple non-greeting messages from same phone should all reach agent."""
        phone = "919900003333"
        # Use non-greeting messages to ensure they all route to the agent
        messages = ["Need sofa", "6 months rental", "Deliver to Gurgaon"]

        for msg in messages:
            payload = payload_factory(phone=phone, text=msg)
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            assert resp.status_code == 200

        assert mock_agent.call_count == 3

    @pytest.mark.unit
    def test_agent_exception_handled_gracefully(self, client, mock_whatsapp, mock_agent, payload_factory):
        """If agent raises an exception, webhook should still return 200."""
        mock_agent.side_effect = Exception("LLM timeout error")

        payload = payload_factory(text="Need sofa")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        # Webhook returns 200 immediately before background processing
        assert resp.status_code == 200

    @pytest.mark.unit
    def test_conversation_auto_created_for_new_phone(self, client, mock_whatsapp, mock_agent, payload_factory):
        """First message from a new phone should auto-create conversation state."""
        phone = "919900004444"
        payload = payload_factory(phone=phone, text="Hi")
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        from webhook_server_revised import conversations
        assert phone in conversations
        assert conversations[phone]["conversation_stage"] == "greeting"

    @pytest.mark.unit
    def test_none_text_does_not_crash(self, client, mock_whatsapp, mock_agent):
        """Payload with no text body should not crash."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [{"profile": {"name": "Test"}, "wa_id": "919900005555"}],
                                "messages": [
                                    {
                                        "from": "919900005555",
                                        "id": "wamid.notext_001",
                                        "timestamp": "1234567890",
                                        "type": "image",
                                        "image": {"id": "IMG_001", "mime_type": "image/jpeg"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ]
                }
            ],
        }
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
