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
python webhook_server.py --port 5000
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

✅ You should see: `🤖 Ku - WhatsApp Webhook Server` running on port 5000

---

### Step 3️⃣: Start ngrok Tunnel

**Open Terminal 2:**
```
ngrok http 5000
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
│   ├── sales_agent.py   # Main sales agent
│   └── state.py         # Conversation state
├── rag/                 # RAG knowledge retrieval
│   └── vectorstore.py   # ChromaDB vector store
├── tools/               # Agent tools
│   └── product_tools.py # Product search, pricing
├── whatsapp/            # WhatsApp API client
│   └── client.py        # Send messages, buttons
├── data/                # Knowledge base data
├── logs/                # Conversation logs
└── utils/               # Utilities
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

*Required for WhatsApp integration

---

## 📊 Logs

Conversation logs are saved per phone number in the `logs/` folder:
- `logs/demo_user.txt` - Demo mode logs
- `logs/919xxxxxxxxx.txt` - WhatsApp user logs

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `OPENAI_API_KEY not set` | Check `.env` file exists and has valid key |
| Webhook verification fails | Ensure `VERIFY_TOKEN` matches Meta dashboard |
| ngrok URL expired | Restart ngrok; update webhook URL in Meta |
| No response on WhatsApp | Check webhook server logs; verify ngrok is running |

---

## 📝 License

Private - RentBasket © 2024
