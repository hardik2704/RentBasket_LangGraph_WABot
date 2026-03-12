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

```
RentBasket_LangGraph_WABot/
├── main.py              # Demo mode entry point
├── webhook_server.py    # WhatsApp webhook server
├── config.py            # Configuration settings
├── .env                 # Environment variables
├── agents/              # LangGraph agent logic
│   ├── orchestrator.py  # Intent router + agent dispatcher
│   ├── sales_agent.py   # Main sales agent
│   ├── recommendation_agent.py  # Product discovery agent
│   └── state.py         # Conversation state
├── rag/                 # RAG knowledge retrieval
│   └── vectorstore.py   # ChromaDB vector store
├── tools/               # Agent tools
│   ├── product_tools.py # Product search, pricing
│   ├── catalogue_tools.py # Catalogue browsing, filtering
│   ├── location_tools.py  # Serviceability checks
│   └── human_handoff.py   # Sales team escalation
├── whatsapp/            # WhatsApp API client
│   └── client.py        # Send messages, buttons
├── utils/               # Utilities
│   ├── logger.py        # File-based conversation logger
│   ├── db.py            # PostgreSQL connection manager
│   └── db_logger.py     # DB-backed logger + analytics
├── scripts/             # Utility scripts
│   ├── setup_db.py      # One-time DB schema setup
│   └── sync_logs.py     # Sync logs from Render
├── data/                # Knowledge base & product data
└── logs/                # Conversation logs (file backup)
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
| `python scripts/sync_logs.py` | Sync production logs locally |
| `python scripts/sync_logs.py --watch` | Keep logs synced in real-time |

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
| `DATABASE_URL` | No** | PostgreSQL connection string (Supabase) |

*Required for WhatsApp integration
**If not set, falls back to file-based logging

---

## 📊 Logs

Conversation logs are stored in **PostgreSQL (Supabase)** for persistence and analytics, with automatic file-based fallback.

### 🗄️ Database Setup (Recommended)

1. Create a free project at [supabase.com](https://supabase.com)
2. Copy `DATABASE_URL` from **Settings → Database → Connection string (URI)**
3. Add to `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
   ```
4. Run the setup script:
   ```bash
   python scripts/setup_db.py
   ```
5. Add `DATABASE_URL` to Render environment variables and redeploy.

**What gets stored:**
| Table | Contents |
|---|---|
| `sessions` | Session lifecycle, pincode, items, duration, agent, stage |
| `messages` | Every user↔bot message with intent, agent, tools used |
| `analytics_events` | Pricing negotiations, handoffs, button presses |

### 🔄 Syncing File Logs from Render
File-based logs (`.txt`) continue to work as a backup. Sync them locally:

1. **Manual Sync**: `python scripts/sync_logs.py`
2. **Watch Mode**: `python scripts/sync_logs.py --watch`

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
| DB connection error | Check `DATABASE_URL` is correct; bot falls back to file logs |
| `psycopg2` import error | Run `pip install psycopg2-binary` |

---

## 📝 License

Private - RentBasket © 2024
