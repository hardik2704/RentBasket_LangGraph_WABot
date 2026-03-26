# Final QA Report: Resilience & Functional Testing

| Stage                  | ID   | Test Case                              | Priority   | Result   | Notes                                                                              |
|:-----------------------|:-----|:---------------------------------------|:-----------|:---------|:-----------------------------------------------------------------------------------|
| Stage 1 - Smoke        | A1.1 | Webhook Receipt                        | P0         | FAIL     |                                                                                    |
| Stage 1 - Smoke        | A1.2 | Normalization                          | P0         | PASS     |                                                                                    |
| Stage 1 - Smoke        | A2.1 | Identified Active Customer             | P0         | PASS     | Status: active_customer                                                            |
| Stage 1 - Smoke        | A2.2 | Identified Past Customer               | P0         | PASS     | Status: past_customer                                                              |
| Stage 1 - Smoke        | A2.3 | Identified Unknown/Lead                | P0         | PASS     | Status: lead                                                                       |
| Stage 1 - Smoke        | A3.1 | Routing Active Customer to Support     | P0         | PASS     | Agent: support                                                                     |
| Stage 1 - Smoke        | A3.2 | Routing Lead to Sales                  | P0         | PASS     | Agent: sales                                                                       |
| Stage 1 - Smoke        | A3.3 | Routing Lead to Recommendation         | P0         | PASS     | Agent: recommendation                                                              |
| Stage 2 - Core         | C1.1 | Maintenance Submenu Trigger            | P0         | FAIL     | Stage: greeting                                                                    |
| Stage 2 - Core         | C2.1 | Product Capture (Fridge)               | P0         | FAIL     | Stage: greeting                                                                    |
| Stage 2 - Core         | C2.2 | Severity Capture                       | P0         | FAIL     | Stage: greeting                                                                    |
| Stage 2 - Core         | C2.3 | Issue Summary Capture                  | P0         | FAIL     | Stage: greeting                                                                    |
| Stage 2 - Core         | C3.1 | Ticket Creation Triggered              | P0         | FAIL     | Stage: greeting                                                                    |
| Stage 2 - Core         | C3.2 | Ticket Data Integrity                  | P0         | PASS     | Ticket: (2, 'maintenance', 'MAINT_APPLIANCE', 'maintenance - MAINT_APPLIANCE', '') |
| Stage 2 - Core         | D1.1 | Billing Policy Query                   | P0         | PASS     | Stage: awaiting_issue_desc                                                         |
| Stage 2 - Core         | E1.1 | Refund Policy Query                    | P0         | PASS     | Stage: awaiting_issue_desc                                                         |
| Stage 2 - Core         | F1.1 | Pickup Request Intake                  | P0         | PASS     | Stage: awaiting_issue_desc                                                         |
| Stage 2 - Core         | G1.1 | Relocation Query                       | P0         | PASS     | Stage: awaiting_issue_desc                                                         |
| Stage 3 - Escalation   | I1.1 | Explicit 'Talk to Team'                | P1         | PASS     | Stage: greeting                                                                    |
| Stage 3 - Escalation   | I1.2 | Sentiment-based Escalation             | P1         | PASS     | Stage: greeting                                                                    |
| Stage 4 - Data Quality | J1.1 | Session Persistence (Mid-Flow Chat)    | P1         | PASS     | Stage: awaiting_maint_severity                                                     |
| Stage 5 - Resilience   | K1.1 | Invalid Button ID Handling             | P2         | PASS     |                                                                                    |
| Stage 5 - Resilience   | K2.1 | Tool Failure Recovery (Ticket Failure) | P2         | PASS     | Msg:                                                                               |
|                        |      |                                        |            |          | 🙏 **I understand this requires special attention.**                               |
|                        |      |                                        |            |          |                                                                                    |
|                        |      |                                        |            |          | I have immediately flagged this issue directly to our **Senior Escalation Team**.  |
|                        |      |                                        |            |          |                                                                                    |
|                        |      |                                        |            |          | **Escalation Protocol Activated:**                                                 |
|                        |      |                                        |            |          | • Customer: Customer                                                               |
|                        |      |                                        |            |          | • Issue: maintenance                                                               |
|                        |      |                                        |            |          | • Urgency: HIGH                                                                    |
|                        |      |                                        |            |          |                                                                                    |
|                        |      |                                        |            |          | A specialist will review your case and message/call you within **24 hours**.       |
|                        |      |                                        |            |          | For immediate assistance, please call: +91 9958187021.                             |