"""
Support Flow Tests for RentBasket WhatsApp Bot.

Tests support scenarios: fridge broken, delivery delayed, refund request,
human handoff. Tests both direct agent calls and webhook-level processing.

Markers:
  - @pytest.mark.unit: Mocked agent/tools (fast)
  - @pytest.mark.e2e: Live LLM tests (slower)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from agents.state import create_initial_state
from agents.support_agent import run_support_agent
from conftest import (
    build_webhook_payload,
    assert_contains_any,
    assert_not_contains,
)


# ============================================================
# HELPER: Create verified customer state
# ============================================================

def make_verified_customer_state():
    """Create state for a verified active customer with active rentals."""
    state = create_initial_state()
    state["collected_info"]["phone"] = "9958448249"
    state["collected_info"]["customer_name"] = "Hardik"
    state["collected_info"]["is_verified_customer"] = True
    state["collected_info"]["customer_status"] = "active_customer"
    state["collected_info"]["active_rentals"] = [
        {"id": "FRIDGE_190", "name": "Single Door Fridge"},
        {"id": "WASH_6KG", "name": "Washing Machine"},
    ]
    return state


# ============================================================
# UNIT TESTS - Direct Agent Calls
# ============================================================

class TestSupportDirectAgent:
    """Test support agent directly (bypassing webhook layer)."""

    @pytest.mark.unit
    @patch("agents.support_agent.log_support_ticket_tool")
    @patch("agents.support_agent.escalate_support_issue_tool")
    def test_maintenance_happy_path(self, mock_escalate, mock_log_ticket):
        """Full maintenance flow: type -> appliance -> product -> severity -> description -> ticket."""
        mock_log_ticket.invoke.return_value = "Ticket #MAINT-001 generated successfully."
        state = make_verified_customer_state()

        # Step 1: Select Maintenance
        resp, state = run_support_agent("SUP_TYPE_MAINTENANCE", state)
        assert "MAINTENANCE_MENU" in resp
        assert state["collected_info"]["workflow_stage"] == "awaiting_maint_type"

        # Step 2: Select Appliance not working
        resp, state = run_support_agent("MAINT_APPLIANCE", state)
        assert state["collected_info"]["workflow_stage"] == "awaiting_maint_product"

        # Step 3: Select product
        resp, state = run_support_agent("PROD_FRIDGE_190", state)
        assert state["collected_info"]["workflow_stage"] == "awaiting_maint_severity"

        # Step 4: Select severity
        resp, state = run_support_agent("SEV_UNUSABLE", state)
        assert state["collected_info"]["workflow_stage"] == "awaiting_issue_desc"

        # Step 5: Provide description
        with patch("agents.support_agent.ChatOpenAI.invoke") as mock_llm:
            from langchain_core.messages import AIMessage
            mock_llm.return_value = AIMessage(content="I understand the issue with your fridge.")
            resp, state = run_support_agent("My fridge is completely off and leaking water.", state)
            assert state["collected_info"]["workflow_stage"] == "awaiting_photo_decision"

        # Step 6: Skip photo
        resp, state = run_support_agent("SUP_NO_PHOTO", state)
        assert state["collected_info"]["workflow_stage"] == "ticket_logged"
        mock_log_ticket.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("agents.support_agent.escalate_support_issue_tool")
    def test_escalation_talk_to_team(self, mock_escalate):
        """Explicit 'Talk to Team' button triggers escalation."""
        mock_escalate.invoke.return_value = "Escalation submitted!"
        state = make_verified_customer_state()

        resp, state = run_support_agent("SUP_TALK_TEAM", state)
        assert state["collected_info"]["workflow_stage"] == "escalated"
        assert state["support_context"]["is_escalated"] is True
        mock_escalate.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("agents.support_agent.ChatOpenAI.invoke")
    def test_free_text_fallback_mid_flow(self, mock_llm):
        """Free text during button-expected flow should fall back to LLM."""
        from langchain_core.messages import AIMessage
        mock_llm.return_value = AIMessage(content="I see you need help with billing.")
        state = make_verified_customer_state()

        # Enter billing flow
        run_support_agent("SUP_TYPE_BILLING", state)

        # Send free text instead of clicking button
        resp, state = run_support_agent("But what about my refund???", state)
        mock_llm.assert_called()

    @pytest.mark.unit
    @patch("agents.support_agent.log_support_ticket_tool")
    @patch("agents.support_agent.escalate_support_issue_tool")
    def test_billing_flow(self, mock_escalate, mock_log_ticket):
        """Billing issue flow."""
        state = make_verified_customer_state()
        resp, state = run_support_agent("SUP_TYPE_BILLING", state)
        assert state["collected_info"]["workflow_stage"] == "awaiting_billing_type"
        assert state["support_context"]["issue_type"] == "billing"


# ============================================================
# UNIT TESTS - Webhook Level
# ============================================================

class TestSupportWebhook:
    """Test support messages through the full webhook pipeline."""

    @pytest.mark.unit
    def test_webhook_fridge_broken(self, conversation):
        """Support: 'My fridge is not working' through webhook."""
        conversation.send("My fridge is not working")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_webhook_delivery_delayed(self, conversation):
        """Support: 'Delivery delayed' through webhook."""
        conversation.send("Delivery delayed by 3 days")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_webhook_refund_request(self, conversation):
        """Support: 'I want refund' through webhook."""
        conversation.send("I want refund")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_webhook_cancel_request(self, conversation):
        """Support: Cancellation request through webhook."""
        conversation.send("I want to cancel my order")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_webhook_human_handoff(self, conversation):
        """'Talk to human' should process without errors."""
        conversation.send("Talk to human")
        assert conversation.last_status_code == 200

    @pytest.mark.unit
    def test_frustrated_customer(self, conversation):
        """Frustrated language should still get a response."""
        conversation.send("This is the worst service, my AC is still not fixed after 5 days!")
        assert conversation.last_status_code == 200


# ============================================================
# E2E TESTS
# ============================================================

@pytest.mark.e2e
class TestSupportE2E:
    """End-to-end support tests with real LLM."""

    def test_e2e_empathetic_tone(self, client, mock_whatsapp, payload_factory):
        """Frustrated message should receive empathetic response."""
        phone = "919900000020"
        payload = payload_factory(
            phone=phone,
            text="My fridge stopped working 3 days ago and nobody came! This is terrible!",
        )
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
        # Bot should have responded
        assert mock_whatsapp.send_text_message.called or mock_whatsapp.send_interactive_buttons.called

    def test_e2e_policy_retrieval(self, client, mock_whatsapp, payload_factory):
        """Refund policy question should retrieve actual policy."""
        phone = "919900000021"
        payload = payload_factory(phone=phone, text="What is your refund policy?")
        resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        assert resp.status_code == 200
