"""
Scenario tests for RentBasket Customer Support Agent.
Uses unittest.mock to prevent database pollution while tracking state transitions.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.support_agent import run_support_agent
from agents.state import create_initial_state

class TestSupportScenarios(unittest.TestCase):

    def setUp(self):
        """Reset state before each scenario."""
        self.state = create_initial_state()
        self.state["collected_info"]["phone"] = "9958448249"
        self.state["collected_info"]["customer_name"] = "Hardik"
        self.state["collected_info"]["is_verified_customer"] = True
        self.state["collected_info"]["active_rentals"] = [
            {"id": "FRIDGE_190", "name": "Single Door Fridge"},
            {"id": "WASH_6KG", "name": "Washing Machine"}
        ]

    # Mocking external DB writes to prevent DB pollution
    @patch('agents.support_agent.log_support_ticket_tool')
    @patch('agents.support_agent.escalate_support_issue_tool')
    def test_maintenance_happy_path(self, mock_escalate, mock_log_ticket):
        """Test: User clicks Maintenance -> Appliance -> Selects Item -> Severity -> Text -> Logs Ticket"""
        
        mock_log_ticket.invoke.return_value = "✅ Ticket #123 generated successfully."
        
        # 1. User clicks "Maintenance Issue" on Main Menu
        resp, self.state = run_support_agent("SUP_TYPE_MAINTENANCE", self.state)
        self.assertIn("MAINTENANCE_MENU", resp)
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "awaiting_maint_type")
        
        # 2. User clicks "Appliance not working"
        resp, self.state = run_support_agent("MAINT_APPLIANCE", self.state)
        self.assertIn("Which item needs maintenance?", resp)
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "awaiting_maint_product")
        
        # 3. User types "Fridge" (Dynamic active rentals catch this)
        resp, self.state = run_support_agent("PROD_FRIDGE_190", self.state)
        self.assertIn("MAINTENANCE_SEVERITY_BUTTONS", resp)
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "awaiting_maint_severity")
        
        # 4. User clicks "Unusable"
        resp, self.state = run_support_agent("SEV_UNUSABLE", self.state)
        self.assertIn("Could you briefly type", resp)
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "awaiting_issue_desc")
        
        # 5. User provides description
        with patch('agents.support_agent.ChatOpenAI.invoke') as mock_llm:
            from langchain_core.messages import AIMessage
            mock_llm.return_value = AIMessage(content="I see the issue. Our policy covers this.")
            
            resp, self.state = run_support_agent("My fridge is totally off and leaking.", self.state)
            self.assertIn("MEDIA_REQUEST_BUTTONS", resp)
            self.assertEqual(self.state["collected_info"]["workflow_stage"], "awaiting_photo_decision")
        
        # 6. User clicks "No Photo"
        resp, self.state = run_support_agent("SUP_NO_PHOTO", self.state)
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "ticket_logged")
        mock_log_ticket.invoke.assert_called_once()


    @patch('agents.support_agent.escalate_support_issue_tool')
    def test_escalation_path(self, mock_escalate):
        """Test: User explicitly clicks 'Talk to Team' triggers escalation tool."""
        
        mock_escalate.invoke.return_value = "🚨 Human Escalted!"
        
        # User clicks "Talk to Team" at the start
        resp, self.state = run_support_agent("SUP_TALK_TEAM", self.state)
        
        self.assertEqual(self.state["collected_info"]["workflow_stage"], "escalated")
        self.assertTrue(self.state["support_context"]["is_escataled"])
        mock_escalate.invoke.assert_called_once()

    @patch('agents.support_agent.ChatOpenAI.invoke')
    def test_fallback_free_text(self, mock_llm):
        """Test: User types random free text instead of clicking a button mid-flow."""
        
        from langchain_core.messages import AIMessage
        mock_llm.return_value = AIMessage(content="I didn't quite understand that.")
        
        # 1. Send it into Billing flow
        run_support_agent("SUP_TYPE_BILLING", self.state)
        
        # 2. User sends random unstructured text when expecting a Button click
        resp, self.state = run_support_agent("But what about my refund???", self.state)
        
        # It should hit the fallback LLM block
        mock_llm.assert_called()


if __name__ == '__main__':
    print("🧪 Running RentBasket Support Scenario Mocks...\n")
    unittest.main(verbosity=2)
