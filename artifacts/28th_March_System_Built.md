Here's the complete report based on the full codebase analysis:

---

# RentBasket "Ku" — WhatsApp Bot Capability Report

---

## Overview

**Ku** is a production-grade AI WhatsApp assistant for **RentBasket** (furniture/appliance rental). It handles the full customer lifecycle — from lead capture to active customer support — via WhatsApp Cloud API.

- **Stack**: LangGraph + LangChain + GPT-4o-mini + Firebase Firestore + Meta WhatsApp Cloud API
- **Architecture**: Stateless webhook server (Flask) + in-memory conversation state + per-phone FIFO locks + Firestore persistence

---

## System Architecture

```
WhatsApp User
     │
     ▼
POST /webhook (Flask, port 8000)
     │
     ├─ Dedup check → Mark read → Typing indicator
     ├─ Greeting/Fallback? → Deterministic reply (no LLM)
     └─ Background thread → Orchestrator → Agent → Response
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              Sales Agent  Recommend.  Support Agent
                    │           │           │
               Tools (LangChain ReAct loop)
                    │
              Firestore ← Session/Lead/Ticket logs
```

---

## Agent System

### Orchestrator
Routes every message by classifying intent → `SALES | RECOMMENDATION | SUPPORT | ESCALATION | GENERAL`

| Customer Status | Intent | Routes To |
|---|---|---|
| Unknown / Lead | SALES or GENERAL | Sales Agent |
| Unknown / Lead | RECOMMENDATION | Sales Agent (keeps in funnel) |
| Active Customer | RECOMMENDATION | Recommendation Agent |
| Active Customer | SUPPORT | Support Agent |
| Any | ESCALATION | Sales Agent + `needs_human=True` |

---

### Sales Agent
Converts leads to customers in **3–4 messages**.

| Step | Action |
|---|---|
| Msg 1 | Greet + ask what they want to rent |
| Msg 2 | Ask city & pincode |
| Msg 3 | Show 2–3 curated options, build tentative cart |
| Msg 4 | Show quote + CTA (Reserve Now / Talk to Expert) |

- **Default**: 12-month duration, 30% flat discount, `₹~~Original~~ ₹Final/mo +GST` format
- **Lead syncing**: Upserts lead data to Firestore at each step (`lead_stage`: new → qualified → cart_created → reserved)
- **Tools**: product search, pricing, quote builder, pincode check, RAG knowledge base, human handoff

---

### Recommendation Agent
Product discovery for **existing customers**.

- Browse all categories with starting prices
- Filter by budget range
- Side-by-side product comparison
- Curated room packages (bedroom, living room, kitchen, etc.)
- Multi-item quote generation with pincode validation

---

### Support Agent
Handles post-sales operations via **hybrid deterministic + LLM** flow.

**Support Menu Tree**:
```
Main Menu
├── Maintenance → [Appliance/Furniture/Installation/Replacement] → Severity → Ticket
├── Billing     → [Payment made/Late fee/Invoice/Due date]
├── Refund      → [Status/Deductions/Delayed]
├── Pickup      → [Request/Delay/Contract terms]
├── Relocation  → [Move items/Address change]
└── Escalate    → Human handoff buttons
```

- **Button clicks** → deterministic state machine (no LLM cost)
- **Free text** → LLM + policy RAG (no hallucination on policies)
- **Tickets** logged to Firestore with `ticket_id`, priority, escalation flag

---

## Tools Available to Agents

| Category | Tools |
|---|---|
| **Products** | `search_products`, `get_price`, `create_quote`, `get_trending` |
| **Catalogue** | `get_full_catalogue_overview`, `browse_category`, `compare_products`, `get_room_package`, `filter_by_budget` |
| **Customer** | `get_customer_profile`, `verify_customer_status` |
| **Leads** | `sync_lead_data` (upsert to Firestore) |
| **Location** | `check_serviceability` (Gurgaon/Noida pincodes), `get_service_areas` |
| **Support** | `log_support_ticket`, `retrieve_support_policy` (RAG), `check_ticket_status` |
| **Escalation** | `escalate_support_issue`, `request_human_handoff` |
| **Knowledge** | `search_company_knowledge` (ChromaDB RAG on FAQs/T&Cs) |
| **Office** | `get_office_location` (Gurgaon / Noida) |

---

## Data Layer (Firestore Collections)

| Collection | Purpose | Key Fields |
|---|---|---|
| `sessions` | Live conversation audit trail | messages sub-collection, transcript, agent used |
| `customers` | Verified customer profiles | phone, rented_items, active status |
| `leads` | Sales pipeline | stage, cart, delivery location, preferences |
| `tickets` | Support issues | type, priority, escalation_flag, status |
| `analytics` | Business events | pricing_negotiation, escalation, ticket_created |

Fallback: file logs at `logs/{phone}.txt` if Firestore unavailable.

---

## WhatsApp Capabilities

| Feature | Implementation |
|---|---|
| Text messages | `send_text_message()` |
| Button messages | `send_interactive_buttons()` — max 3 buttons |
| List/dropdown menus | `send_list_message()` — dynamic sections + rows |
| Read receipts | Blue checkmarks on receive |
| Typing indicator | Shows "typing..." before response |
| Deduplication | `processed_ids` cache (Meta retries) |
| FIFO per-phone | Per-phone threading locks |
| Webhook verification | `GET /webhook` with `hub.challenge` |
| Log download | `/logs` endpoint (auth via VERIFY_TOKEN) |

---

## Special Behaviors (Webhook-Level, Pre-LLM)

| Trigger | Action |
|---|---|
| "hi", "hello", "start" | Instant button reply (BROWSE / SALES / SUPPORT) — no LLM |
| Pricing keywords ("discount", "cheaper", "negotiate") | Interactive tenure/discount options |
| Button: `BROWSE_FURNITURE` | Routes to Recommendation Agent |
| Button: `TALK_TO_SALES` | Routes to Sales Agent |
| Button: `NEED_SUPPORT` | Routes to Support Agent |
| Button: `CALL_ME` / `CHAT_HERE` | Human handoff CTA |
| "help" text | Fallback menu |

---

## Service Coverage

- **Cities**: Gurgaon (122xxx pincodes) + Noida (201xxx pincodes)
- **Border areas**: Manesar (122413, 122414) — manual check required
- **Sales contacts**: Gurgaon `+91 9958187021` / Noida `+91 9958440038`
- **Support email**: `support@rentbasket.com`

---

## Infrastructure

- **LLM**: GPT-4o-mini (temp: 0.3) for responses + `text-embedding-3-small` for RAG
- **Vector DB**: ChromaDB (local) for knowledge base / FAQ retrieval
- **Server**: Flask on port 8000, Render-deployable (stateless)
- **Conversation state**: In-memory dict per phone + Firestore for persistence
- **Pricing logic**: Haversine-based distance engine for location-based delivery pricing

---

## What's In Place vs. What's Missing / Potential Gaps

**Solid**:
- Full sales funnel (lead → cart → close)
- Support ticketing with structured menus
- Human escalation with CTA buttons
- RAG for policy Q&A
- Real-time Firestore logging

**Notable Gaps / Build-Upon Opportunities**:
- `admin-portal/` (React/TS) exists but appears incomplete
- No template message (HSM) sending for proactive outreach
- No payment link / Razorpay integration
- No image/media handling (media presence is detected but not processed)
- PostgreSQL (`utils/db.py`) exists as fallback but not actively used
- No automated follow-up / drip messaging for leads

---

This gives you the full picture to build upon it!