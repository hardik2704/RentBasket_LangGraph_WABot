import pytest
from webhook_server import app, conversations
from agents.state import create_initial_state
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def clear_conversations():
    """Clear conversation state between tests."""
    conversations.clear()

@pytest.fixture
def mock_whatsapp():
    """Mock WhatsApp client to prevent real API calls."""
    with patch("webhook_server.whatsapp_client") as mocked:
        # Mock common methods
        mocked.send_text_message = MagicMock()
        mocked.send_read_and_typing_indicator = MagicMock()
        mocked.send_typing_indicator = MagicMock()
        yield mocked

@pytest.fixture
def mock_agent():
    """Mock the orchestrator/agent to control responses."""
    with patch("webhook_server.route_and_run") as mocked:
        mocked.return_value = ("Test response", create_initial_state())
        yield mocked

@pytest.fixture(autouse=True)
def mock_threads():
    """Make threading synchronous for testing."""
    with patch("threading.Thread") as mocked:
        def start_sync():
            # Get the target and args from the call
            target = mocked.call_args[1]["target"]
            args = mocked.call_args[1]["args"]
            target(*args)
        
        mocked.return_value.start = start_sync
        yield mocked
