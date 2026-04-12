"""
Customer Intent Flow Tests for RentBasket WhatsApp Bot.

Tests real customer message patterns: product search, pricing queries,
category browsing, vague/typo/Hindi/Hinglish messages.

Markers:
  - @pytest.mark.unit: Mocked agent (fast, deterministic)
  - @pytest.mark.e2e: Live LLM agent (slower, requires OPENAI_API_KEY)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from agents.state import create_initial_state
from conftest import (
    build_webhook_payload,
    assert_contains_any,
    assert_not_contains,
    assert_state_field,
)


# ============================================================
# UNIT TESTS (Mocked Agent)
# ============================================================

class TestCustomerIntentsUnit:
    """Test that customer messages reach the agent correctly via webhook."""

    @pytest.mark.unit
    def test_first_time_greeting(self, client, mock_whatsapp, mock_agent, payload_factory):
        """
        First-time customer sends 'Hi' -- greeting handler fires directly
        (bypasses agent). Sends interactive buttons.
        """
        payload = payload_factory(text="Hi")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
        # Greeting goes to handle_greeting(), not route_and_run
        mock_agent.assert_not_called()
        # Should send interactive buttons or text
        assert mock_whatsapp.send_interactive_buttons.called or mock_whatsapp.send_text_message.called

    @pytest.mark.unit
    def test_product_search_sofa(self, client, mock_whatsapp, mock_agent, payload_factory):
        """Customer searches for a specific product."""
        payload = payload_factory(text="Need sofa")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        assert "sofa" in call_args[0][0].lower() or "sofa" in str(call_args).lower()

    @pytest.mark.unit
    def test_product_search_fridge_with_location(self, conversation):
        """Customer asks for product + location in one message."""
        conversation.send("Fridge rent Gurgaon")
        assert conversation.last_status_code == 200
        assert conversation.mock_agent.called

    @pytest.mark.unit
    def test_category_search_beds(self, conversation):
        """Category-level search."""
        conversation.send("Show me beds")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    @pytest.mark.hinglish
    def test_pricing_query_hinglish(self, conversation):
        """Hinglish pricing query should route without crashing."""
        conversation.send("AC kitne ka hai")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_vague_query(self, conversation):
        """Vague query with no specific product should still process."""
        conversation.send("Room setup chahiye")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_typo_query(self, conversation):
        """Typo in product name should not crash."""
        conversation.send("frij rent")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_comparison_query(self, conversation):
        """Product comparison request."""
        conversation.send("Sofa vs bed price compare karo")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    @pytest.mark.hinglish
    def test_hindi_devanagari_script(self, conversation):
        """Pure Hindi in Devanagari script should process without error."""
        conversation.send("मुझे फ्रिज चाहिए")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    @pytest.mark.hinglish
    def test_hinglish_mixed(self, conversation):
        """Mixed Hindi-English message."""
        conversation.send("Washing machine ka rent batao")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_read_receipt_sent_on_message(self, client, mock_whatsapp, mock_agent, payload_factory):
        """Every incoming message should trigger a read receipt."""
        msg_id = "wamid.receipt_test_001"
        payload = payload_factory(text="Hi", msg_id=msg_id)
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        mock_whatsapp.send_read_and_typing_indicator.assert_called_with(msg_id)

    @pytest.mark.unit
    def test_sender_name_captured(self, client, mock_whatsapp, mock_agent, payload_factory):
        """Sender name from WhatsApp profile should be stored in state."""
        phone = "919900007777"
        payload = payload_factory(text="Need sofa", sender_name="Hardik Jain", phone=phone)
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert mock_agent.called
        # Verify name was passed through to state
        call_args = mock_agent.call_args
        state_arg = call_args[0][1]
        assert state_arg["collected_info"].get("customer_name") == "Hardik Jain"

    @pytest.mark.unit
    def test_urgency_message(self, conversation):
        """Urgent product request."""
        conversation.send("Need bed urgently for tomorrow")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_budget_query(self, conversation):
        """Customer mentions budget."""
        conversation.send("I have 5000 budget for furniture")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_multiple_products_single_message(self, conversation):
        """Customer asks for multiple items at once."""
        conversation.send("Need sofa, bed and fridge")
        assert conversation.last_status_code == 200


# ============================================================
# E2E TESTS (Live Agent)
# ============================================================

@pytest.mark.e2e
class TestCustomerIntentsE2E:
    """
    End-to-end tests with real LLM agent calls.
    Run with: pytest -m e2e
    Requires OPENAI_API_KEY environment variable.
    """

    def test_e2e_sofa_routes_to_sales(self, client, mock_whatsapp, payload_factory):
        """Product request should route to sales agent and mention the product."""
        payload = payload_factory(text="Need sofa for 6 months", phone="919900000001")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200

        # Check the bot replied
        assert mock_whatsapp.send_text_message.called or mock_whatsapp.send_interactive_buttons.called

    def test_e2e_hindi_routes_correctly(self, client, mock_whatsapp, payload_factory):
        """Hindi query should route to appropriate agent without errors."""
        payload = payload_factory(text="AC kitne ka hai", phone="919900000002")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200

    def test_e2e_catalogue_browse(self, client, mock_whatsapp, payload_factory):
        """Broad browsing query should work end-to-end."""
        payload = payload_factory(text="Show me all furniture options", phone="919900000003")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
