import json
import pytest
from unittest.mock import patch

def test_webhook_read_receipt(client, mock_whatsapp):
    """Test that webhook sends read receipt and returns 200."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123", "phone_number_id": "123"},
                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": "919958448249"}],
                    "messages": [{
                        "from": "919958448249",
                        "id": "MSG_123",
                        "timestamp": "123456789",
                        "text": {"body": "Hi"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    response = client.post("/webhook", 
                           data=json.dumps(payload),
                           content_type="application/json")
    
    assert response.status_code == 200
    mock_whatsapp.send_read_and_typing_indicator.assert_called_with("MSG_123")

def test_webhook_deduplication(client, mock_whatsapp, mock_agent):
    """
    Test that duplicate message IDs are ignored.
    NOTE: This test is EXPECTED TO FAIL currently because deduplication was reverted.
    """
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123", "phone_number_id": "123"},
                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": "919958448249"}],
                    "messages": [{
                        "from": "919958448249",
                        "id": "DUPE_ID",
                        "timestamp": "123456789",
                        "text": {"body": "Hello again"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    # Send first time
    response1 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
    assert response1.status_code == 200
    
    # Send second time (Meta retry)
    response2 = client.post("/webhook", data=json.dumps(payload), content_type="application/json")
    assert response2.status_code == 200
    
    # The actual behavior should be that the agent is NOT called twice if deduplication is on
    # If this fails, it proves we need the deduplication logic back.
    assert mock_agent.call_count == 1
