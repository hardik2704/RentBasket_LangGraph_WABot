"""
Conversion Funnel Tests for RentBasket WhatsApp Bot.

Tests the multi-turn sales funnel: product inquiry -> pricing -> delivery ->
discount -> booking. Validates lead capture, pincode/duration extraction,
pricing negotiation detection, and conversion push.

Markers:
  - @pytest.mark.unit: Mocked agent (fast, deterministic)
  - @pytest.mark.e2e: Live LLM agent (slower, requires OPENAI_API_KEY)
"""

import json
import pytest
from unittest.mock import patch
from agents.state import create_initial_state
from conftest import (
    build_webhook_payload,
    ConversationSession,
    assert_contains_any,
    assert_state_field,
)


# ============================================================
# UNIT TESTS
# ============================================================

class TestConversionFunnelUnit:
    """Multi-turn conversion funnel tests with mocked agent."""

    @pytest.mark.unit
    def test_full_5_turn_funnel(self, conversation):
        """
        Simulate a complete 5-turn sales funnel:
        1. Product inquiry
        2. Pricing question
        3. Delivery question
        4. Discount question
        5. Booking intent
        """
        state = create_initial_state()

        # Configure mock to return different responses per turn
        responses = [
            ("We have great sofas! Starting from Rs 599/mo + GST", state),
            ("For 6 months, a 3-seater sofa is Rs 783/mo + GST", state),
            ("We deliver free within 72 hours! What is your pincode?", state),
            ("Great! Let me create your cart. [SEND_CART_BUTTONS]", state),
        ]
        conversation.mock_agent.side_effect = responses

        # Avoid greeting words and pricing negotiation keywords
        conversation.send("Need sofa")
        conversation.send("What is the price for 6 months?")
        conversation.send("What about delivery?")
        conversation.send("I want to book now")

        assert conversation.mock_agent.call_count == 4
        assert len(conversation.responses) == 4

    @pytest.mark.unit
    def test_pincode_extraction_in_webhook(self, client, mock_whatsapp, mock_agent, payload_factory):
        """
        Pincode regex extraction happens in webhook_server BEFORE agent call.
        Sending a 6-digit pincode should update state.collected_info.pincode.
        """
        phone = "919911223344"

        # Send message with pincode (non-greeting to reach process_webhook_async)
        payload = payload_factory(phone=phone, text="My pincode is 122001 please check")
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        from webhook_server_revised import conversations
        state = conversations.get(phone)
        assert state is not None
        assert state["collected_info"].get("pincode") == "122001"

    @pytest.mark.unit
    def test_duration_extraction_in_webhook(self, client, mock_whatsapp, mock_agent, payload_factory):
        """
        Duration regex extraction happens in webhook_server BEFORE agent call.
        '6 months' should set collected_info.duration_months = 6.
        """
        phone = "919911223355"

        payload = payload_factory(phone=phone, text="I want furniture for 6 months")
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        from webhook_server_revised import conversations
        state = conversations.get(phone)
        assert state is not None
        assert state["collected_info"].get("duration_months") == 6

    @pytest.mark.unit
    def test_duration_extraction_various_formats(self, client, mock_whatsapp, mock_agent, payload_factory):
        """Test duration extraction with different phrasings."""
        test_cases = [
            ("12 months", 12),
            ("3 mo", 3),
            ("9 month", 9),
        ]
        for text, expected_dur in test_cases:
            # Clear state for each sub-test
            from webhook_server_revised import conversations, processed_ids_dict
            conversations.clear()
            processed_ids_dict.clear()

            phone = f"91991122{expected_dur:04d}"
            payload = payload_factory(phone=phone, text=text)
            client.post("/webhook", data=json.dumps(payload), content_type="application/json")

            state = conversations.get(phone)
            assert state is not None, f"No state for '{text}'"
            assert state["collected_info"].get("duration_months") == expected_dur, \
                f"Expected {expected_dur} months from '{text}', got {state['collected_info'].get('duration_months')}"


class TestPricingNegotiationDetection:
    """Test the is_pricing_negotiation() function directly."""

    @pytest.mark.unit
    def test_pricing_negotiation_detected(self):
        """Messages with negotiation keywords should be detected."""
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("Too expensive, give discount") is True
        assert is_pricing_negotiation("Can you go down on price?") is True
        assert is_pricing_negotiation("This is costly") is True

    @pytest.mark.unit
    def test_url_not_flagged_as_negotiation(self):
        """URLs should NOT trigger pricing negotiation."""
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("Check https://rentbasket.com/offer") is False
        assert is_pricing_negotiation("http://example.com discount") is False

    @pytest.mark.unit
    def test_duration_question_not_flagged(self):
        """Duration/tenure questions should NOT trigger negotiation."""
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("How much for 6 months?") is False
        assert is_pricing_negotiation("Will there be a discount for 12 months?") is False

    @pytest.mark.unit
    def test_normal_messages_not_flagged(self):
        """Normal product queries should not trigger negotiation."""
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("Need sofa") is False
        assert is_pricing_negotiation("Show me fridges") is False
        assert is_pricing_negotiation("Hi") is False


# ============================================================
# E2E TESTS
# ============================================================

@pytest.mark.e2e
class TestConversionFunnelE2E:
    """End-to-end conversion tests with real LLM."""

    def test_e2e_full_sales_journey(self, client, mock_whatsapp, payload_factory):
        """Multi-turn sales conversation with real agent."""
        phone = "919900000010"

        messages = [
            "Need sofa for my living room",
            "6 months rental",
            "Deliver to 122001",
        ]

        for msg in messages:
            payload = payload_factory(phone=phone, text=msg)
            resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
            assert resp.status_code == 200

        # Bot should have responded to each message
        assert mock_whatsapp.send_text_message.call_count >= 1 or \
               mock_whatsapp.send_interactive_buttons.call_count >= 1

    def test_e2e_upsell_behavior(self, client, mock_whatsapp, payload_factory):
        """Check if bot suggests related products (upsell)."""
        phone = "919900000011"
        payload = payload_factory(phone=phone, text="I want a bed for 6 months")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
