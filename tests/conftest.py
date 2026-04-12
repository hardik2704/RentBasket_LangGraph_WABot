"""
RentBasket WhatsApp Bot - Test Configuration & Fixtures
Enterprise-grade testing infrastructure with multi-turn conversation support,
semantic assertion helpers, and automatic report collection.
"""

import sys
import os
import json
import time
import uuid

# Fix import path for pytest + pytest-xdist
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
from webhook_server_revised import (
    app,
    conversations,
    processed_ids_dict,
    session_context,
    per_phone_locks,
)
from agents.state import create_initial_state
from unittest.mock import MagicMock, patch
import random


# ============================================================
# PAYLOAD BUILDER
# ============================================================

def build_webhook_payload(
    phone="919958448249",
    text="Hi",
    sender_name="Test User",
    msg_id=None,
    msg_type="text",
    interactive=None,
):
    """
    Build a realistic WhatsApp Business API webhook payload.
    Generates unique message IDs by default to avoid dedup interference.
    """
    if msg_id is None:
        msg_id = f"wamid.test_{uuid.uuid4().hex[:16]}"

    message = {
        "from": phone,
        "id": msg_id,
        "timestamp": str(int(time.time())),
        "type": msg_type,
    }

    if msg_type == "text":
        message["text"] = {"body": text}
    elif msg_type == "interactive" and interactive:
        message["interactive"] = interactive

    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "TEST_PHONE_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": sender_name},
                                    "wa_id": phone,
                                }
                            ],
                            "messages": [message],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


# ============================================================
# CONVERSATION SESSION (Multi-Turn Testing Primitive)
# ============================================================

class ConversationSession:
    """
    Simulates a WhatsApp customer session for multi-turn testing.
    Each instance uses a unique phone number for parallel safety.
    """

    def __init__(self, client, mock_whatsapp, mock_agent=None, phone=None, sender_name="Test User"):
        self.client = client
        self.mock_whatsapp = mock_whatsapp
        self.mock_agent = mock_agent
        self.phone = phone or f"9199{random.randint(10000000, 99999999)}"
        self.sender_name = sender_name
        self.responses = []
        self.last_reply = None
        self.last_status_code = None
        self._msg_count = 0

    def send(self, text, msg_type="text", interactive=None):
        """Send a message and capture the bot's reply."""
        self._msg_count += 1
        payload = build_webhook_payload(
            phone=self.phone,
            text=text,
            sender_name=self.sender_name,
            msg_type=msg_type,
            interactive=interactive,
        )
        response = self.client.post(
            "/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.last_status_code = response.status_code

        # Capture the bot's reply from mock_whatsapp calls
        reply = self._extract_last_reply()
        self.last_reply = reply
        self.responses.append(reply)
        return reply

    def _extract_last_reply(self):
        """Extract the most recent bot reply from mocked WhatsApp calls."""
        calls = self.mock_whatsapp.send_text_message.call_args_list
        if calls:
            # Find calls for our phone number
            for call in reversed(calls):
                args, kwargs = call
                target_phone = args[0] if args else kwargs.get("to_phone")
                if target_phone == self.phone:
                    return args[1] if len(args) > 1 else kwargs.get("message", "")
        return None

    @property
    def state(self):
        """Get current conversation state."""
        return conversations.get(self.phone)

    @property
    def collected_info(self):
        """Shortcut to collected_info dict."""
        state = self.state
        return state.get("collected_info", {}) if state else {}


# ============================================================
# SEMANTIC ASSERTION HELPERS
# ============================================================

def assert_contains_any(text, keywords, msg=None):
    """Assert that text contains at least one of the keywords (case-insensitive)."""
    if text is None:
        raise AssertionError(msg or f"Text is None, expected one of: {keywords}")
    text_lower = text.lower()
    found = any(kw.lower() in text_lower for kw in keywords)
    if not found:
        raise AssertionError(
            msg or f"Text does not contain any of {keywords}.\nActual: {text[:200]}"
        )


def assert_not_contains(text, forbidden, msg=None):
    """Assert text contains none of the forbidden terms (case-insensitive)."""
    if text is None:
        return  # None doesn't contain anything
    text_lower = text.lower()
    for term in forbidden:
        if term.lower() in text_lower:
            raise AssertionError(
                msg or f"Text contains forbidden term '{term}'.\nActual: {text[:200]}"
            )


def assert_state_field(state, dotpath, expected):
    """Assert a nested state field via dot-path. E.g., 'collected_info.pincode'."""
    parts = dotpath.split(".")
    val = state
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = None
            break
    assert val == expected, f"State field '{dotpath}' = {val!r}, expected {expected!r}"


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_all_state():
    """Clear ALL shared state between tests to prevent cross-contamination."""
    conversations.clear()
    processed_ids_dict.clear()
    session_context.clear()
    per_phone_locks.clear()
    yield
    conversations.clear()
    processed_ids_dict.clear()
    session_context.clear()
    per_phone_locks.clear()


@pytest.fixture
def mock_whatsapp():
    """Mock WhatsApp client to prevent real API calls."""
    with patch("webhook_server_revised.whatsapp_client") as mocked:
        mocked.send_text_message = MagicMock(return_value={"messages": [{"id": "mock_msg_id"}]})
        mocked.send_read_and_typing_indicator = MagicMock(return_value={"success": True})
        mocked.send_typing_indicator = MagicMock(return_value={"success": True})
        mocked.send_interactive_buttons = MagicMock(return_value={"messages": [{"id": "mock_msg_id"}]})
        mocked.send_list_message = MagicMock(return_value={"messages": [{"id": "mock_msg_id"}]})
        mocked.send_template_message = MagicMock(return_value={"messages": [{"id": "mock_msg_id"}]})
        yield mocked


@pytest.fixture
def mock_agent():
    """Mock the orchestrator/agent to control responses.

    By default, returns the input state back (preserving extracted data like
    pincode, duration). Override side_effect or return_value per-test if needed.
    """
    def _passthrough_agent(text, state):
        """Default mock: return the state as-is with a generic response."""
        return ("Test response from bot", state)

    with patch("webhook_server_revised.route_and_run") as mocked:
        mocked.side_effect = _passthrough_agent
        yield mocked


@pytest.fixture(autouse=True)
def mock_threads():
    """Make threading synchronous for testing."""
    with patch("threading.Thread") as mocked:

        def start_sync():
            call_kwargs = mocked.call_args[1]
            target = call_kwargs.get("target")
            args = call_kwargs.get("args", ())
            if target:
                target(*args)

        mocked.return_value.start = start_sync
        yield mocked


@pytest.fixture(autouse=True)
def mock_all_external():
    """Mock all external service calls (Firebase, DB, logging) to prevent side effects.

    IMPORTANT: Two layers of patching are required:
    1. Module-level imports in webhook_server_revised (e.g., get_lead, upsert_lead)
    2. Source module (utils.firebase_client, tools.customer_tools) for local imports
       and calls that bypass the top-level mock (e.g., orchestrator calling
       verify_customer_status -> get_customer_profile -> Firestore directly).
    """
    with patch("webhook_server_revised.get_lead", return_value=None), \
         patch("webhook_server_revised.upsert_lead"), \
         patch("webhook_server_revised.get_or_create_session", return_value="test-session-id"), \
         patch("webhook_server_revised.log_conversation_turn"), \
         patch("webhook_server_revised.start_new_session"), \
         patch("webhook_server_revised.update_session"), \
         patch("webhook_server_revised.log_event"), \
         patch("webhook_server_revised.file_log_turn"), \
         patch("webhook_server_revised.file_start_session"), \
         patch("webhook_server_revised.update_user_facts"), \
         patch("webhook_server_revised.restore_lead_to_state", side_effect=lambda p, s: s), \
         patch("webhook_server_revised._try_direct_product_request", return_value=False), \
         patch("webhook_server_revised.time.sleep"), \
         patch("utils.firebase_client.get_lead", return_value=None), \
         patch("utils.firebase_client.upsert_lead"), \
         patch("utils.firebase_client.is_hot_lead", return_value=False), \
         patch("tools.customer_tools.get_customer_profile", return_value=None), \
         patch("agents.orchestrator.verify_customer_status", return_value={
             "status": "unknown",
             "is_verified": False,
             "customer_profile": None,
             "active_rentals": [],
         }), \
         patch("agents.orchestrator.get_lead", return_value=None), \
         patch("agents.orchestrator.upsert_lead"):
        yield


@pytest.fixture
def payload_factory():
    """Factory fixture for building webhook payloads."""
    return build_webhook_payload


@pytest.fixture
def conversation(client, mock_whatsapp, mock_agent):
    """Single conversation session with mocked agent."""
    return ConversationSession(client, mock_whatsapp, mock_agent)


@pytest.fixture
def make_conversation(client, mock_whatsapp, mock_agent):
    """Factory for creating multiple independent conversation sessions."""
    def _make(phone=None, sender_name="Test User"):
        return ConversationSession(client, mock_whatsapp, mock_agent, phone, sender_name)
    return _make


# ============================================================
# REPORT COLLECTOR PLUGIN
# ============================================================

class ReportCollector:
    """Collects test results for report generation."""

    def __init__(self):
        self.results = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            self.results.append({
                "nodeid": report.nodeid,
                "outcome": report.outcome,
                "duration": round(report.duration, 4),
                "markers": [m.name for m in report.own_markers] if hasattr(report, "own_markers") else [],
                "longrepr": str(report.longrepr) if report.failed else None,
            })

    def pytest_sessionfinish(self, session, exitstatus):
        report_path = os.path.join(os.path.dirname(__file__), ".test_results.json")
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r["outcome"] == "passed"),
                "failed": sum(1 for r in self.results if r["outcome"] == "failed"),
                "results": self.results,
            }, f, indent=2)


def pytest_configure(config):
    """Register the report collector plugin."""
    config.pluginmanager.register(ReportCollector(), "report_collector")
