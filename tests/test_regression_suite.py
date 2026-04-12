"""
Regression Test Suite for RentBasket WhatsApp Bot.

Each test guards against a previously identified bug.
When a new bug is fixed, add a regression test here following the template.

Template:
    @pytest.mark.regression
    def test_regression_BUGID_short_description(self):
        '''
        Bug: [Description of the original bug]
        Fixed in: [file(s) modified]
        Guard: [What this test prevents from happening again]
        '''
        # ... test code ...
"""

import json
import pytest
from conftest import build_webhook_payload


# ============================================================
# REGRESSION TESTS
# ============================================================

@pytest.mark.regression
class TestRegressionSuite:

    def test_regression_deduplication_works(self, client, mock_whatsapp, mock_agent):
        """
        Bug: Deduplication was reverted, causing Meta retries to process twice.
        Fixed in: webhook_server_revised.py (processed_ids_dict logic restored)
        Guard: Same message_id must NOT call agent twice.
        """
        msg_id = "wamid.REGRESS_DEDUP_001"
        payload = build_webhook_payload(text="Need sofa for my room", msg_id=msg_id)

        # Send twice (simulating Meta retry)
        resp1 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
        resp2 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Second request should be deduped (returns "duplicate" status)
        resp2_json = resp2.get_json()
        assert resp2_json.get("status") == "duplicate", \
            f"Second request not deduped. Response: {resp2_json}"

    def test_regression_url_no_pricing_negotiation(self):
        """
        Bug: URLs containing pricing keywords triggered negotiation handler.
        Fixed in: webhook_server_revised.py is_pricing_negotiation()
        Guard: Messages with URLs must never trigger pricing negotiation.
        """
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("https://rentbasket.com/offer") is False
        assert is_pricing_negotiation("Check http://site.com/best-price") is False

    def test_regression_duration_no_pricing_negotiation(self):
        """
        Bug: Duration questions like 'how much for 6 months' triggered negotiation.
        Fixed in: webhook_server_revised.py is_pricing_negotiation()
        Guard: Duration/tenure questions must NOT trigger pricing negotiation.
        """
        from webhook_server_revised import is_pricing_negotiation
        assert is_pricing_negotiation("How much for 6 months?") is False
        assert is_pricing_negotiation("Will there be discount for 12 months?") is False
        assert is_pricing_negotiation("What if I rent for longer duration?") is False

    def test_regression_is_escalated_field_spelling(self):
        """
        Bug: Field was misspelled as 'is_escataled' throughout codebase.
        Fixed in: agents/state.py, agents/support_agent.py
        Guard: The field must be correctly spelled as 'is_escalated'.
        """
        from agents.state import create_initial_state
        state = create_initial_state()
        # Field should exist with correct spelling
        assert "is_escalated" in state["support_context"], \
            "is_escalated field missing from support_context (typo regression)"
        assert state["support_context"]["is_escalated"] is False

        # Old typo should NOT exist
        assert "is_escataled" not in state["support_context"], \
            "Old typo 'is_escataled' still present in state"

    def test_regression_empty_payload_no_crash(self, client, mock_whatsapp):
        """
        Bug: Empty webhook payloads caused 500 errors.
        Fixed in: webhook_server_revised.py handle_webhook()
        Guard: Empty payloads must return 200 without crashing.
        """
        resp = client.post("/webhook", data=json.dumps({}), content_type="application/json")
        assert resp.status_code == 200

    def test_regression_greeting_creates_state(self, client, mock_whatsapp, mock_agent, payload_factory):
        """
        Bug: First message from new user did not always create conversation state.
        Fixed in: webhook_server_revised.py process_webhook_async()
        Guard: First message must always create conversation state.
        """
        phone = "919988776655"
        payload = payload_factory(phone=phone, text="Hi")
        client.post("/webhook", data=json.dumps(payload), content_type="application/json")

        from webhook_server_revised import conversations
        assert phone in conversations, "Conversation state not created for new user"
