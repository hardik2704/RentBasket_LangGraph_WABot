# 🧪 RentBasket Support Bot: Test Plan

This document outlines the testing strategy for the Customer Support Pilot.

## 1. Mock Data Strategy
We use `scripts/seed_mock_customers.py` to populate the database with diverse operational states.

| Profile | Category | Purpose |
| :--- | :--- | :--- |
| **Hardik Sharma** | Active Customer (Single) | Standard maintenance / billing tests. |
| **Arjun Patel** | Active Customer (Multiple) | Maintenance ambiguity / product selection tests. |
| **Ananya Gupta** | Past Customer | Re-subscription or "Closed Issue" test cases. |
| **Rahul Verma** | Unknown / Lead | Sales handoff and frustration detection tests. |

## 2. Conversation Scenarios
The automated suite `tests/test_support_scenarios.py` covers these critical paths:

### A. Maintenance Happy Path
- **Triggers**: "Appliance not working" button.
- **Verification**: User selects valid item -> inputs text -> clicks "No Media" -> Ticket created.
- **Success Criteria**: `operations_tickets` contains a new row with `issue_type='maintenance'`.

### B. Escalation Path
- **Triggers**: "Talk to Team" button or frustration keywords.
- **Verification**: Bot immediately stops intake and provides handoff contact.
- **Success Criteria**: `analytics_events` logs a `support_escalation` event.

### C. Fallback Path
- **Triggers**: Sending random text when a button selection is required.
- **Verification**: Bot uses the policy-grounded LLM to respond but maintains context.
- **Success Criteria**: Bot does not crash and loop; provides a helpful policy summary.

## 3. How to Run Tests
1. **Initialize DB**: `python3 scripts/setup_db.py`
2. **Seed Data**: `python3 scripts/seed_mock_customers.py`
3. **Execute Scenarios**: `PYTHONPATH=. python3 tests/test_support_scenarios.py`
4. **Manual sanity check**: Send a message to the bot via WhatsApp and run `python3 scripts/pull_analytics.py`.

## 4. Verification Checklist for Pilot
- [ ] Bot recognizes 10-digit phone numbers regardless of +91 prefix.
- [ ] Database logs every turn in the `messages` table.
- [ ] LLM does not fabricate policies (strictly uses `SUPPORT_POLICIES`).
- [ ] Human handoff buttons appear instantly upon failure or request.
