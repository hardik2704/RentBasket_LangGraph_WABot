# RentBasket WhatsApp Bot — Ku

**Version: V1.1** | Production-Ready AI Rental Assistant

Ku is RentBasket's AI-powered WhatsApp sales & support bot, built on **LangGraph + GPT-4o + WhatsApp Cloud API**. Customers can browse furniture and appliance rentals, get instant pricing, share item lists via text or voice note, and complete checkout — entirely within WhatsApp.

---

## What Ku Can Do

### For Customers (Sales Flow)
| Feature | How It Works |
|---|---|
| **Instant Greeting** | Smart welcome with 3 action buttons |
| **Share Item List** | Type or voice-note your items — Ku builds a cart instantly |
| **Browse by Room** | Navigate Study → Living → Bedroom → Kitchen with subcategories |
| **Voice Note Support** | Whisper transcribes, GPT-4o extracts products (Hindi/English/Hinglish) |
| **Smart Pricing** | 30% off MRP shown instantly; 10% extra for 12+ month upfront |
| **Checkout Link** | Personalized cart URL generated with JWT + referral code |
| **Serviceability Check** | Pincode validated against Gurgaon & Noida service areas |
| **Catalogue Image** | Product catalogue image sent at Browse Products entry |

### For Customers (Support Flow)
| Feature | How It Works |
|---|---|
| **Maintenance Requests** | Severity-based routing with ticket creation |
| **Billing Queries** | Interactive sub-menu for billing types |
| **Refund Tracking** | Closure date + refund status lookup |
| **Relocation Requests** | Address capture + new pincode check |
| **Human Handoff** | Escalates to sales team with phone numbers |

### Conversation Intelligence
| Feature | How It Works |
|---|---|
| **Bye Detection** | 30+ bye phrases (English + Hindi) → farewell + sales contact |
| **Ghost Timer** | 30 min silence → sends farewell message automatically |
| **19-Hour Follow-up** | Re-engagement nudge 19 hrs after last message |
| **Pricing Negotiation** | Detects "too costly" / "discount" → escalation flow |
| **Lead Persistence** | Firestore saves name, duration, location, cart stage across sessions |
| **Re-greeting Restore** | On "Hi" again → restores name/location but re-asks duration fresh |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI Orchestration** | LangGraph + LangChain |
| **Language Model** | GPT-4o (extraction) + GPT-4o-mini (agents) |
| **Voice Transcription** | OpenAI Whisper |
| **WhatsApp API** | Meta WhatsApp Cloud API v23.0 |
| **Web Server** | Flask + Gunicorn |
| **Database** | Firebase Firestore |
| **Deployment** | Render |
| **Knowledge Base** | ChromaDB (RAG for policies) |

---

## Product Catalogue

- **60+ products** across furniture and appliances
- **25+ categories**: Beds, Sofas, Fridges, Washing Machines, ACs, TVs, Study Furniture, and more
- **Dynamic pricing** by duration: 3 / 6 / 9 / 12+ months
- **Smart defaults**: "washing machine" → Fully Automatic; "TV" → Smart LED 43"; "sofa" → 5 Seater with CT

### Service Cities
| City | Sales Phone |
|---|---|
| Gurgaon (Gurugram) | +91 9958187021 |
| Noida | +91 9958440038 |

---

## Agent Architecture

```
User Message
     │
     ▼
Orchestrator (Intent Classifier)
     │
     ├──► Sales Agent        ← New leads, pricing, cart creation
     ├──► Recommendation Agent  ← Browse, compare, package suggestions
     ├──► Support Agent      ← Maintenance, billing, refund, relocation
     └──► Support Intake     ← Identity verification for unknown users
```

Each agent has its own LangGraph state machine, tool set, and system prompt.

---

## Browse Products Flow

```
[Browse Products Button]
     │
     ▼
RentBasket Catalogue Image  ← NEW in V1.1
     │
     ▼
Select Duration (3 / 6 / 12 months)
     │
     ▼
Select Room
  ├─ Study Room    (Desk, Chair, Shelf)
  ├─ Living Room   (Sofas, TVs, Tables, AC)
  ├─ Bedroom       (Beds, Mattresses, Storage)
  └─ Kitchen       (Fridge, Washing Machine, Cooking)
     │
     ▼
Select Subcategory → Select Variant
     │
     ▼
Cart Quote (MRP → 30% off → Savings shown)
     │
     ▼
[View Cart] [Browse More] [Reviews]
     │
     ▼
Full Cart Details + Checkout Button
     │
     ▼
Enter Pincode → Serviceability Check → Cart Link
```

---

## Share Item List Flow (V1.1)

```
[Share Item List Button]  ← First button in greeting
     │
     ▼
"Please share the items you're looking for..."
     │
     ▼  (text or voice note)
GPT-4o Extraction
  - Understands English / Hindi / Hinglish
  - Maps vague terms to exact product IDs
  - Handles quantities ("do bed" = 2 beds)
  - Falls back to regex parser if needed
     │
     ▼
"Got it! I found: 2x Double Bed, 1x Washing Machine..."
     │
     ▼
Select Duration (3 / 6 / 12 months)
     │
     ▼
Draft Cart with 3 buttons: [View Cart] [Browse More] [Reviews]
```

---

## Conversation Lifecycle

```
User Sends "Hi"
     │ Greeting + 3 buttons
     │ Timers reset
     ▼
User Browses / Shares Items / Talks to Agent
     │ Every message resets 30-min ghost timer + 19-hr follow-up timer
     ▼
User Says "Bye" / Goes Quiet
     │
     ├─ Explicit Bye → Farewell message + sales phone + website
     │                 19-hr follow-up scheduled
     │
     └─ Silent 30 min → Ghost message + sales phone + website
                        (19-hr follow-up still running)
     ▼
19 Hours Later → "Hi! Just checking in. Were you still looking?..."
```

---

## Quick Start (Local)

### 1. Clone & Install
```bash
git clone https://github.com/hardik2704/RentBasket_LangGraph_WABot.git
cd RentBasket_LangGraph_WABot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in:
```env
# WhatsApp Cloud API
PHONE_NUMBER_ID=your_phone_number_id
ACCESS_TOKEN=your_meta_access_token
VERIFY_TOKEN=your_webhook_verify_token
VERSION=v23.0

# OpenAI
OPENAI_API_KEY=your_openai_key

# Firebase
FIREBASE_CONFIG={"type":"service_account",...}   # Full JSON as string

# Server
RENDER_URL=https://your-app.onrender.com
PORT=8000
```

### 3. Run Server
```bash
source venv/bin/activate
python3 webhook_server_revised.py
```

### 4. Expose with ngrok (for local testing)
```bash
ngrok http 8000
# Set the ngrok HTTPS URL as your webhook in Meta Developer Console
```

---

## Deployment (Render)

1. Push to GitHub (`main` branch)
2. Render auto-deploys on push
3. Set all env vars in Render → Environment
4. Webhook URL: `https://your-app.onrender.com/webhook`
5. Set in Meta Developer Console: Webhook URL + Verify Token

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `PHONE_NUMBER_ID` | Yes | WhatsApp Business phone number ID |
| `ACCESS_TOKEN` | Yes | Meta long-lived access token |
| `VERIFY_TOKEN` | Yes | Webhook verification token |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `FIREBASE_CONFIG` | Yes | Firebase Admin SDK JSON (as string) |
| `RENDER_URL` | Yes | Your Render deployment URL |
| `PORT` | No | Server port (default: 8000) |
| `DATABASE_URL` | No | PostgreSQL URL (optional analytics DB) |

---

## Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Health check |
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | Receive WhatsApp messages |
| `/catalogue` | GET | Serves `RentBasket_Catalogue.png` |
| `/logs` | GET | List conversation log files |

---

## Firestore Data Model

```
leads/{phone}
  ├─ name, push_name
  ├─ duration_months
  ├─ delivery_location: {pincode, city}
  ├─ lead_stage: new | browsing | quote_ready | cart_created | converted
  └─ browse_cart_link

sessions/{session_id}
  ├─ phone, push_name, created_at
  ├─ live_transcript[]
  └─ messages/ (subcollection)

analytics/{phone}/events[]
  └─ action, data, timestamp
```

---

## Feature Changelog

### V1.1 (Current)
- Share Item List button added as primary greeting action
- GPT-4o powered voice/text item extraction (Hindi/Hinglish/English)
- Bye/exit detection with farewell message + sales contact
- 30-minute ghost timer for inactive users
- 19-hour follow-up re-engagement message
- RentBasket Catalogue image sent at Browse Products entry
- Smart category defaults (TV → 43", Study Chair → Premium, etc.)
- Room reorder: Study Room first, 1BHK removed from room list

### V1.0
- LangGraph multi-agent architecture (Sales, Recommendation, Support)
- Interactive Browse Products flow (Room → Subcategory → Variants)
- Voice note transcription with Whisper
- Firebase Firestore lead + session persistence
- Pincode serviceability check
- Pricing negotiation detection
- Human handoff escalation
- RAG knowledge base for policy Q&A

---

## Project Structure

```
RentBasket_LangGraph_WABot/
├── webhook_server_revised.py   # Main Flask server (~4500 lines)
├── config.py                   # Business config, phones, API endpoints
├── main.py                     # Local interactive demo
├── requirements.txt
│
├── agents/
│   ├── orchestrator.py         # Intent routing + customer verification
│   ├── sales_agent.py          # Lead qualification + cart creation
│   ├── recommendation_agent.py # Browse + compare + packages
│   ├── support_agent.py        # Maintenance/billing/refund/relocation
│   └── state.py                # LangGraph conversation state schema
│
├── tools/
│   ├── product_tools.py        # Search, quote, cart link generation
│   ├── location_tools.py       # Pincode extraction + serviceability API
│   ├── catalogue_tools.py      # Full catalogue, compare, budget filter
│   ├── customer_tools.py       # Customer verification
│   ├── support_tools.py        # Ticket logging + policy lookup
│   ├── lead_tools.py           # Lead sync to Firestore
│   └── human_handoff.py        # Escalation tool
│
├── whatsapp/
│   └── client.py               # WhatsApp Cloud API client
│
├── utils/
│   ├── firebase_client.py      # Firestore operations
│   ├── db_logger.py            # Session + turn logging
│   ├── phone_utils.py          # Phone normalization
│   ├── session_cache.py        # In-memory user fact cache
│   └── support_menus.py        # Pre-built interactive menus
│
├── data/
│   ├── products.py             # 60+ products, pricing, search functions
│   └── RentBasket_Catalogue.png # Product catalogue image
│
└── rag/
    └── vectorstore.py          # ChromaDB policy knowledge base
```

---

## Built With

- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent state machine orchestration
- [LangChain](https://langchain.com) — LLM integration & tool calling
- [OpenAI GPT-4o](https://openai.com) — Agent reasoning + product extraction
- [OpenAI Whisper](https://openai.com/research/whisper) — Voice note transcription
- [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp) — Messaging
- [Firebase Firestore](https://firebase.google.com) — Lead & session persistence
- [Flask](https://flask.palletsprojects.com) — Webhook server
- [Render](https://render.com) — Deployment

---

*RentBasket — Comfort On Rent, Happiness Delivered.*
