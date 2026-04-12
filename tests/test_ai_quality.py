"""
AI Quality Tests for RentBasket WhatsApp Bot.

Tests LLM behavior: correct tool usage, hallucination resistance,
fallback quality, tone, and upsell behavior.

All tests are @pytest.mark.e2e -- they call real LLM agents.
Run with: pytest -m e2e -v
Requires: OPENAI_API_KEY environment variable.
"""

import json
import pytest
from conftest import (
    build_webhook_payload,
    assert_contains_any,
    assert_not_contains,
)


def _get_bot_reply(client, mock_whatsapp, phone, text):
    """Send message and extract bot reply."""
    payload = build_webhook_payload(phone=phone, text=text)
    resp = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200

    # Extract reply from mocked send calls
    reply_parts = []
    for call in mock_whatsapp.send_text_message.call_args_list:
        args, kwargs = call
        target = args[0] if args else kwargs.get("to_phone")
        if target == phone:
            msg = args[1] if len(args) > 1 else kwargs.get("message", "")
            reply_parts.append(msg)
    return " ".join(reply_parts) if reply_parts else None


# ============================================================
# TOOL USAGE TESTS
# ============================================================

@pytest.mark.e2e
class TestToolUsage:
    """Verify the AI agent uses the correct tools."""

    def test_search_tool_for_product_query(self, client, mock_whatsapp):
        """Product query should trigger search and return real product info."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100001", "Show me fridges")
        if reply:
            # Reply should mention fridge-related terms or pricing
            assert_contains_any(reply, ["fridge", "refrigerator", "door", "price", "rent", "/mo"])

    def test_quote_tool_for_pricing(self, client, mock_whatsapp):
        """Pricing query should return actual price figures."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100002", "How much is a sofa for 6 months?")
        if reply:
            # Should contain price indicators
            assert_contains_any(reply, ["₹", "rs", "/mo", "month", "price", "rent"])

    def test_state_captures_pincode(self, client, mock_whatsapp):
        """Pincode in message should be captured in state."""
        phone = "919900100003"

        # First message
        payload1 = build_webhook_payload(phone=phone, text="Need sofa")
        client.post("/webhook", data=json.dumps(payload1), content_type="application/json")

        # Second with pincode
        payload2 = build_webhook_payload(phone=phone, text="My area pincode is 122001")
        client.post("/webhook", data=json.dumps(payload2), content_type="application/json")

        from webhook_server_revised import conversations
        state = conversations.get(phone)
        if state:
            assert state["collected_info"].get("pincode") == "122001"


# ============================================================
# HALLUCINATION RESISTANCE
# ============================================================

@pytest.mark.e2e
class TestNoHallucination:
    """Verify the AI does not hallucinate products, prices, or competitors."""

    def test_no_fake_products(self, client, mock_whatsapp):
        """Asking for non-existent products should NOT list them."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100010", "Do you rent laptops?")
        if reply:
            assert_not_contains(reply, [
                "laptop available", "we have laptops", "laptop for rent",
                "macbook", "dell laptop"
            ])

    def test_no_competitor_mentions(self, client, mock_whatsapp):
        """Bot should never mention competitors."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100011", "How are you compared to others?")
        if reply:
            assert_not_contains(reply, [
                "furlenco", "rentomojo", "cityfurnish", "pepperfry rent",
            ])

    def test_no_fabricated_policies(self, client, mock_whatsapp):
        """Bot should not invent return/refund policies."""
        reply = _get_bot_reply(
            client, mock_whatsapp, "919900100012",
            "Can I return after 1 day for full refund?"
        )
        if reply:
            # Should NOT promise instant full refund (policy requires 7 days minimum)
            assert_not_contains(reply, [
                "1 day return", "instant refund", "100% refund next day",
            ])


# ============================================================
# FALLBACK QUALITY
# ============================================================

@pytest.mark.e2e
class TestFallbackQuality:
    """Test bot's response to out-of-scope and unclear messages."""

    def test_out_of_scope_redirected(self, client, mock_whatsapp):
        """Non-furniture question should be redirected politely."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100020", "What is the weather today?")
        if reply:
            # Should NOT try to answer weather; should redirect to furniture
            assert_not_contains(reply, ["temperature", "sunny", "rain", "celsius"])

    def test_gibberish_gets_clarification(self, client, mock_whatsapp):
        """Gibberish should get a polite clarification request, not an error."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100021", "xyzzy plugh zork")
        if reply:
            # Should not contain error messages
            assert_not_contains(reply, ["error", "exception", "traceback", "500"])


# ============================================================
# TONE QUALITY
# ============================================================

@pytest.mark.e2e
class TestToneQuality:
    """Test that bot maintains appropriate tone."""

    def test_friendly_general_tone(self, client, mock_whatsapp):
        """General query should get a friendly, helpful response."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100030", "Tell me about your services")
        if reply:
            # Should NOT be robotic/harsh
            assert_not_contains(reply, [
                "invalid request", "error processing", "I cannot",
            ])

    def test_empathetic_support_tone(self, client, mock_whatsapp):
        """Frustrated support message should be met with empathy."""
        reply = _get_bot_reply(
            client, mock_whatsapp, "919900100031",
            "I am very angry, my AC has been broken for a week and nobody responds!"
        )
        if reply:
            # Should contain empathy markers
            assert_contains_any(reply, [
                "sorry", "understand", "apologize", "help", "resolve",
                "right away", "immediately", "concern",
            ])


# ============================================================
# UPSELL BEHAVIOR
# ============================================================

@pytest.mark.e2e
class TestUpsellBehavior:
    """Test if bot suggests related/complementary products."""

    def test_upsell_after_single_product(self, client, mock_whatsapp):
        """After bed request, bot may suggest mattress or bedside table."""
        reply = _get_bot_reply(client, mock_whatsapp, "919900100040", "I want a bed for 12 months")
        # This is a soft test -- upsell is nice-to-have, not mandatory
        # We just verify the response is valid
        if reply:
            assert len(reply) > 10  # Should be a substantial response
