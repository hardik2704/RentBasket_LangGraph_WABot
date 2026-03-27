# 🤖 RentBasket WhatsApp Bot "Ku"

AI-powered WhatsApp sales assistant for RentBasket built with **LangGraph**, **LangChain**, and **OpenAI**.

---

## 🚀 Quick Start

### 1. Clone & Setup Environment

```bash
cd RentBasket_LangGraph_WABot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your credentials:

```env
# Required - OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Required for WhatsApp - From Meta Business Dashboard
ACCESS_TOKEN=your_whatsapp_access_token
PHONE_NUMBER_ID=your_phone_number_id
APP_ID=your_app_id
APP_SECRET=your_app_secret
VERSION=v23.0
VERIFY_TOKEN=12345  # Your custom verify token for webhook

# Firebase Configuration (Paste the entire Service Account JSON string)
FIREBASE_CONFIG='{"type": "service_account", "project_id": "...", ...}'
```

### 3. Run the Bot

```bash
# Demo Mode (Terminal Chat)
python main.py

# Test Scenarios
python main.py --test

# WhatsApp Webhook Server
python webhook_server.py --port 8000
```

---

## 📱 WhatsApp Business API Integration

### Step 1️⃣: Get Your Meta Credentials

> **Where:** [developers.facebook.com](https://developers.facebook.com/) → Your App → WhatsApp → API Setup

| Find This | Copy to `.env` as |
|-----------|-------------------|
| Phone Number ID | `PHONE_NUMBER_ID` |
| Temporary Access Token | `ACCESS_TOKEN` |

---

### Step 2️⃣: Start Your Webhook Server

**Open Terminal 1:**
```
python3 webhook_server.py
```

✅ You should see: `🤖 Ku - WhatsApp Webhook Server` running on port 8000

---

### Step 3️⃣: Start ngrok Tunnel

**Open Terminal 2:**
```
ngrok http 8000
```

✅ Copy the **https** URL → Example: `https://abc123.ngrok-free.app`

---

### Step 4️⃣: Connect Webhook to Meta

> **Where:** Meta Developer Dashboard → WhatsApp → Configuration

| Field | What to Enter |
|-------|---------------|
| **Callback URL** | `https://YOUR-NGROK-URL/webhook` |
| **Verify Token** | `12345` |

**Then click:** ✅ Verify and Save

**Subscribe to these webhook fields:**
- ☑️ `messages`  
- ☑️ `messaging_postbacks`

---

### Step 5️⃣: Send a Test Message

📲 Open WhatsApp → Message your connected number → Bot replies! 🎉

**What happens:**
1. ✓✓ Blue ticks (read receipt)
2. ⌨️ Typing indicator appears  
3. 💬 Bot sends AI response

---

## 📁 Project Structure

```text
RentBasket_LangGraph_WABot/
├── 🤖 main.py               # Main entry point for local interactive demo & testing
├── 📡 webhook_server.py     # Production Flask server for WhatsApp Business API integration
├── ⚙️ config.py             # Global configurations, credentials, and business rules
├── 🧠 agents/               # Core AI logic using LangGraph
│   ├── orchestrator.py      # Intent classification & dynamic agent routing
│   ├── sales_agent.py       # Handles pricing, quotes, and sales-focused queries
│   ├── recommendation_agent.py # Product discovery and browsing assistant
│   └── state.py             # Conversation memory and shared state schema
├── 🛠️ tools/                # Specialized functions used by agents
│   ├── product_tools.py     # Real-time pricing and availability retrieval
│   ├── catalogue_tools.py   # Product category and specification lookups
│   ├── location_tools.py    # Serviceability validation (Pincode checks)
│   └── human_handoff.py     # Logic for escalating to human sales agents
├── 🚚 logistics/            # Location-based engines
│   ├── distance_engine.py   # Calculates distances for delivery zones
│   └── pricing.py           # Handles location-dependent rental pricing
├── 💬 whatsapp/             # WhatsApp Cloud API wrappers
│   ├── client.py            # Handles sending text, buttons, and list messages
│   └── indicators.py        # Typing & read receipt simulations
├── 📝 utils/                # Shared helpers
│   ├── firebase_client.py   # [NEW] Firestore initialization & SDK wrapper
│   ├── db_logger.py         # [UPDATED] Advanced logging to Google Firestore
│   └── logger.py            # Local file-based logging for debugging
├── 📜 scripts/              # Dev & ops automation
│   ├── pull_analytics.py    # [UPDATED] Pulls pilot metrics from Firestore
│   ├── seed_customers.py    # [UPDATED] Populates Firestore with test data
│   └── sync_logs.py         # Sync production file-based logs locally
├── 📦 data/                 # Static assets and knowledge base
│   ├── products.py          # Product catalog definitions
│   └── knowledge_base.py    # RAG source data for policies
└── 📂 logs/                 # Local archive of WhatsApp conversation transcripts
```

---

## 🔧 Key Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Interactive demo mode |
| `python main.py --test` | Run test scenarios |
| `python webhook_server.py` | Start WhatsApp webhook server |
| `python webhook_server.py --port 8000` | Custom port |
| `ngrok http 5000` | Expose server to internet |
| `python3 scripts/sync_logs.py` | Sync production logs locally |
| `python3 scripts/sync_logs.py --watch` | Keep logs synced in real-time |

---

## 💡 Bot Capabilities

- **Product Search**: "I need a dining table for 6 months"
- **Bundle Pricing**: "Need bed, sofa, fridge for 3 months"
- **Serviceability Check**: Validates delivery by pincode
- **RAG-based Q&A**: Answers policy questions from knowledge base
- **Pricing Negotiation**: Detects negotiation intent → shows interactive buttons
- **Human Handoff**: Escalates to sales team when needed

---

## 🔑 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT |
| `ACCESS_TOKEN` | Yes* | WhatsApp Cloud API access token |
| `PHONE_NUMBER_ID` | Yes* | Your WhatsApp Business phone number ID |
| `APP_ID` | No | Meta App ID |
| `APP_SECRET` | No | Meta App Secret |
| `VERSION` | No | Graph API version (default: v23.0) |
| `VERIFY_TOKEN` | No | Webhook verification token (default: 12345) |
| `FIREBASE_CONFIG` | Yes** | Full Service Account JSON string for Firestore |

*Required for WhatsApp integration
**If not set, falls back to local file-based logging

---

## 📊 Logs & Persistence

Conversation logs are stored in **Google Firebase (Firestore)** for high-availability persistence and support analytics, with automatic file-based fallback.

### 🔥 Firebase/Firestore Setup (Recommended)

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/) and create a new project.
   - Enable **Cloud Firestore** in test mode or production mode.
2. **Generate Service Account**:
   - Go to **Project Settings → Service Accounts**.
   - Click **Generate New Private Key**.
3. **Environment Configuration**:
   - Add the **Entire JSON content** of the downloaded file to your `.env` or Render environment:
     ```env
     FIREBASE_CONFIG='{"type": "service_account", "project_id": "...", ...}'
     ```
4. **Seed Test Data**:
   - Run the seeding script to populate your new database:
     ```bash
     python3 scripts/seed_customers.py
     ```

### 🗂️ Firestore Schema Structure
| Collection | Description | Evolvability |
| :--- | :--- | :--- |
| `sessions` | Session lifecycle & parent metadata | Snapshot of latest user state |
| `sessions/{id}/messages` | Full audit trail (Sub-collection) | Real-time chat history stream |
| `analytics` | Business events (negotiations, handoffs) | Event-driven pilot metrics |
| `customers` | Core profiles indexed by Phone | Integrated CRM-style lookups |
| `tickets` | [NEW] Support tickets for human ops | Operational dashboard fuel |

### 🔄 Syncing File Logs from Render
File-based logs (`.txt`) continue to work as a backup. Sync them locally:

1. **Manual Sync**: `python3 scripts/sync_logs.py`
2. **Watch Mode**: `python3 scripts/sync_logs.py --watch`

3. **Locations**:
   - `logs/demo_user.txt` - Local demo mode logs
   - `logs/919xxxxxxxxx.txt` - Synced WhatsApp user logs

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `OPENAI_API_KEY not set` | Check `.env` file exists and has valid key |
| Webhook verification fails | Ensure `VERIFY_TOKEN` matches Meta dashboard |
| ngrok URL expired | Restart ngrok; update webhook URL in Meta |
| No response on WhatsApp | Check webhook server logs; verify ngrok is running |
| Firebase Init Error | Ensure `FIREBASE_CONFIG` is a valid JSON string |

---

## 📝 License

Private - RentBasket © 2026
