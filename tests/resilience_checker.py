import os
import sys
import json
import time
import pytest
from unittest.mock import MagicMock, patch

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webhook_server import app, conversations, processed_ids
from agents.state import create_initial_state
from utils.db import execute_query, execute_query_one
from utils.phone_utils import normalize_phone

class ResilienceChecker:
    def __init__(self):
        self.client = app.test_client()
        app.config["TESTING"] = True
        self.results = []
        
        # Mock WhatsApp client to prevent real API calls
        self.mock_wa = MagicMock()
        import webhook_server
        webhook_server.whatsapp_client = self.mock_wa

    def log_result(self, stage, test_id, description, priority, status, notes=""):
        self.results.append({
            "Stage": stage,
            "ID": test_id,
            "Category": stage,
            "Test Case": description,
            "Priority": priority,
            "Result": status,
            "Notes": notes
        })
        print(f"[{status}] {test_id}: {description}")

    def send_webhook(self, phone, text, name="Test User", msg_id=None, msg_type="text"):
        if not msg_id:
            msg_id = f"MSG_{int(time.time() * 1000)}"
            
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "123", "phone_number_id": "123"},
                        "contacts": [{"profile": {"name": name}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": msg_id,
                            "timestamp": str(int(time.time())),
                            "text": {"body": text},
                            "type": msg_type
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        return self.client.post("/webhook", 
                               data=json.dumps(payload),
                               content_type="application/json")

    def run_stage_1_smoke(self):
        print("\n--- Running Stage 1: Smoke ---")
        stage = "Stage 1 - Smoke"
        
        # A1. Incoming message handling & Normalization
        phone = "919958448249" 
        res = self.send_webhook(phone, "Hi")
        self.log_result(stage, "A1.1", "Webhook Receipt", "P0", "PASS" if res.status_code == 200 else "FAIL")
        
        normalized = normalize_phone(phone)
        self.log_result(stage, "A1.2", "Normalization", "P0", "PASS" if normalized == "9958448249" else "FAIL")
        
        # A2. Customer identification
        conversations.clear()
        self.send_webhook("9958448249", "Maintenance")
        state = conversations.get("9958448249")
        status = state["collected_info"].get("customer_status") if state else None
        self.log_result(stage, "A2.1", "Identified Active Customer", "P0", "PASS" if status == "active_customer" else "FAIL", f"Status: {status}")
        
        conversations.clear()
        self.send_webhook("9812345678", "I need help")
        state = conversations.get("9812345678")
        status = state["collected_info"].get("customer_status") if state else None
        self.log_result(stage, "A2.2", "Identified Past Customer", "P0", "PASS" if status == "past_customer" else "FAIL", f"Status: {status}")
        
        conversations.clear()
        self.send_webhook("9000000123", "Price of fridge")
        state = conversations.get("9000000123")
        status = state["collected_info"].get("customer_status") if state else None
        self.log_result(stage, "A2.3", "Identified Unknown/Lead", "P0", "PASS" if status == "lead" else "FAIL", f"Status: {status}")

        # A3. Initial Routing
        conversations.clear()
        self.send_webhook("9958448249", "My fridge is not cooling")
        state = conversations.get("9958448249")
        agent = state.get("active_agent") if state else None
        self.log_result(stage, "A3.1", "Routing Active Customer to Support", "P0", "PASS" if agent == "support" else "FAIL", f"Agent: {agent}")

        conversations.clear()
        self.send_webhook("9222222222", "What is the cost of a bed?")
        state = conversations.get("9222222222")
        agent = state.get("active_agent") if state else None
        self.log_result(stage, "A3.2", "Routing Lead to Sales", "P0", "PASS" if agent == "sales" else "FAIL", f"Agent: {agent}")

        conversations.clear()
        self.send_webhook("9333333333", "Help me find home furniture")
        state = conversations.get("9333333333")
        agent = state.get("active_agent") if state else None
        self.log_result(stage, "A3.3", "Routing Lead to Recommendation", "P0", "PASS" if agent == "recommendation" else "FAIL", f"Agent: {agent}")

    def run_stage_2_core_journeys(self):
        print("\n--- Running Stage 2: Core Journeys (Maintenance) ---")
        stage = "Stage 2 - Core"

        # C1-C3. Maintenance Intake
        phone = "9958448249"
        conversations.clear()
        
        # 1. Start support
        self.send_webhook(phone, "Maintenance")
        # 2. Select Appliance (Buttons/Text)
        self.send_webhook(phone, "Appliance not working")
        
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "C1.1", "Maintenance Submenu Trigger", "P0", "PASS" if workflow == "awaiting_maint_product" else "FAIL", f"Stage: {workflow}")
        
        # 3. Choose product (Active Customer Hardik has Fridge and Washing Machine)
        self.send_webhook(phone, "Fridge")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "C2.1", "Product Capture (Fridge)", "P0", "PASS" if workflow == "awaiting_maint_severity" else "FAIL", f"Stage: {workflow}")
        
        # 4. Severity
        self.send_webhook(phone, "Completely unusable")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "C2.2", "Severity Capture", "P0", "PASS" if workflow == "awaiting_issue_desc" else "FAIL", f"Stage: {workflow}")

        # 5. Issue description
        self.send_webhook(phone, "It is leaking gas and making noise.")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "C2.3", "Issue Summary Capture", "P0", "PASS" if workflow == "awaiting_photo_decision" else "FAIL", f"Stage: {workflow}")
        
        # 6. Media decision
        self.send_webhook(phone, "No photo")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "C3.1", "Ticket Creation Triggered", "P0", "PASS" if workflow == "ticket_logged" else "FAIL", f"Stage: {workflow}")
        
        # Verify ticket in DB
        ticket_query = "SELECT id, issue_type, sub_intent, summary, description FROM operations_tickets WHERE phone_number = %s ORDER BY created_at DESC LIMIT 1;"
        ticket = execute_query_one(ticket_query, ("9958448249",))
        self.log_result(stage, "C3.2", "Ticket Data Integrity", "P0", "PASS" if ticket else "FAIL", f"Ticket: {ticket}")

    def run_stage_2_core_billing_refund(self):
        print("\n--- Running Stage 2: Core Journeys (Billing & Refund) ---")
        stage = "Stage 2 - Core"

        phone = "9958448249"
        
        # D1. Billing
        conversations.clear()
        self.send_webhook(phone, "SUP_TYPE_BILLING")
        self.send_webhook(phone, "BILL_LATE")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "D1.1", "Billing Policy Query", "P0", "PASS" if workflow == "awaiting_issue_desc" else "FAIL", f"Stage: {workflow}")

        # E1. Refund
        conversations.clear()
        self.send_webhook(phone, "SUP_TYPE_REFUND")
        self.send_webhook(phone, "REF_STATUS")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "E1.1", "Refund Policy Query", "P0", "PASS" if workflow == "awaiting_issue_desc" else "FAIL", f"Stage: {workflow}")

    def run_stage_2_core_pickup_relocation(self):
        print("\n--- Running Stage 2: Core Journeys (Pickup & Relocation) ---")
        stage = "Stage 2 - Core"

        phone = "9958448249"
        
        # F1. Pickup
        conversations.clear()
        self.send_webhook(phone, "SUP_TYPE_PICKUP")
        self.send_webhook(phone, "PICK_REQUEST")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "F1.1", "Pickup Request Intake", "P0", "PASS" if workflow == "awaiting_issue_desc" else "FAIL", f"Stage: {workflow}")

        # G1. Relocation
        conversations.clear()
        self.send_webhook(phone, "SUP_TYPE_RELOCATION")
        self.send_webhook(phone, "MOVE_CHECK")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        self.log_result(stage, "G1.1", "Relocation Query", "P0", "PASS" if workflow == "awaiting_issue_desc" else "FAIL", f"Stage: {workflow}")

    def run_stage_3_escalation(self):
        print("\n--- Running Stage 3: Escalation ---")
        stage = "Stage 3 - Escalation"

        phone = "9958448249"
        
        # I1. Explicit Escalation
        conversations.clear()
        self.send_webhook(phone, "SUP_TALK_TEAM")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        escalated = (workflow == "escalated") or state.get("needs_human") or state.get("escalation_requested")
        self.log_result(stage, "I1.1", "Explicit 'Talk to Team'", "P1", "PASS" if escalated else "FAIL", f"Stage: {workflow}")

        # I2. Automatic Escalation (Frustration)
        conversations.clear()
        self.send_webhook(phone, "YOUR SERVICE IS PATHETIC!! CONNECT ME TO A HUMAN NOW!!")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        # Note: If sentiment-based escalation is not yet implemented in main loop routing but requested
        escalated = (workflow == "escalated") or state.get("needs_human")
        self.log_result(stage, "I1.2", "Sentiment-based Escalation", "P1", "PASS" if escalated else "FAIL", f"Stage: {workflow}")

    def run_stage_4_data_quality(self):
        print("\n--- Running Stage 4: Data Quality ---")
        stage = "Stage 4 - Data Quality"
        
        phone = "9958448249"
        conversations.clear()
        
        # J1. Session State Persistence
        self.send_webhook(phone, "SUP_TYPE_MAINTENANCE")
        self.send_webhook(phone, "MAINT_APPLIANCE")
        
        # Interject with random question
        self.send_webhook(phone, "Wait, what is your name?") 
        
        # Now get back to flow
        self.send_webhook(phone, "Fridge")
        state = conversations.get(phone)
        workflow = state["collected_info"].get("workflow_stage") if state else None
        
        # Should stay in maintenance flow
        self.log_result(stage, "J1.1", "Session Persistence (Mid-Flow Chat)", "P1", "PASS" if workflow == "awaiting_maint_severity" else "FAIL", f"Stage: {workflow}")

    def run_stage_5_resilience(self):
        print("\n--- Running Stage 5: Resilience ---")
        stage = "Stage 5 - Resilience"
        
        phone = "9958448249"
        conversations.clear()
        
        # K1. Invalid Inputs (Garbage ID)
        self.send_webhook(phone, "SUP_TYPE_MAINTENANCE")
        self.send_webhook(phone, "INVALID_BUTTON_ID_999")
        state = conversations.get(phone)
        # Should either fallback or stay in same stage politely
        self.log_result(stage, "K1.1", "Invalid Button ID Handling", "P2", "PASS" if state else "FAIL")
        
        # K2. Tool Failure Simulation (Mock log_support_ticket_tool exception)
        # Patching the tool's invoke method by replacing the tool in the agent module
        import agents.support_agent
        original_tool = agents.support_agent.log_support_ticket_tool
        
        mock_tool = MagicMock()
        mock_tool.invoke.side_effect = Exception("DB Connection Timeout")
        agents.support_agent.log_support_ticket_tool = mock_tool
        
        try:
            # Set to a state ready to log
            conversations[phone] = create_initial_state()
            state = conversations[phone]
            state["collected_info"]["workflow_stage"] = "ready_to_log"
            state["support_context"]["issue_type"] = "maintenance"
            state["collected_info"]["phone"] = phone
            
            # Send anything to trigger process_ticket_logging
            from agents.support_agent import process_ticket_logging
            msg, new_state = process_ticket_logging(state)
            # It should handle error and escalate
            self.log_result(stage, "K2.1", "Tool Failure Recovery (Ticket Failure)", "P2", "PASS" if "escalated" in new_state["collected_info"]["workflow_stage"] else "FAIL", f"Msg: {msg}")
        except Exception as e:
             self.log_result(stage, "K2.1", "Tool Failure Recovery (Ticket Failure)", "P2", "FAIL", f"Exception: {e}")
        finally:
            agents.support_agent.log_support_ticket_tool = original_tool

    def generate_report(self):
        import pandas as pd
        df = pd.DataFrame(self.results)
        print("\n--- FINAL QA REPORT ---")
        # Ensure all columns are present even if some tests were skipped
        cols = ["Stage", "ID", "Test Case", "Priority", "Result", "Notes"]
        df = df.reindex(columns=cols)
        print(df.to_markdown(index=False))
        
        with open("qa_report.md", "w") as f:
            f.write("# Final QA Report: Resilience & Functional Testing\n\n")
            f.write(df.to_markdown(index=False))

if __name__ == "__main__":
    # Ensure threads are run synchronously for testing
    with patch("threading.Thread") as mocked_thread:
        def start_sync(*args, **kwargs):
            target = kwargs.get("target") or (mocked_thread.call_args[1].get("target") if mocked_thread.call_args else None)
            thread_args = kwargs.get("args") or (mocked_thread.call_args[1].get("args") if mocked_thread.call_args else [])
            if target:
                target(*thread_args)
        
        mocked_thread.return_value.start = start_sync
        
        checker = ResilienceChecker()
        checker.run_stage_1_smoke()
        checker.run_stage_2_core_journeys()
        checker.run_stage_2_core_billing_refund()
        checker.run_stage_2_core_pickup_relocation()
        checker.run_stage_3_escalation()
        checker.run_stage_4_data_quality()
        checker.run_stage_5_resilience()
        checker.generate_report()
