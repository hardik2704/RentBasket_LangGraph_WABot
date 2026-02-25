# WhatsApp Bot "Ku" - RentBasket
# Configuration and Constants

import os
from dotenv import load_dotenv

load_dotenv()

# ========================================
# API KEYS
# ========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# WhatsApp Business API (from .env)
WHATSAPP_PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "12345")
WHATSAPP_VERSION = os.getenv("VERSION", "v23.0")

# ========================================
# MODEL CONFIGURATION
# ========================================
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3  # Slightly creative but consistent
EMBEDDING_MODEL = "text-embedding-3-small"

# ========================================
# RAG CONFIGURATION
# ========================================
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
RETRIEVER_K = 3  # Number of chunks to retrieve

# ========================================
# COMPANY CONTACT INFO & OFFICES
# ========================================

# Gurgaon Office
GURGAON_OFFICE = {
    "address": "C9/2, Lower Ground Floor, Ardee City, Sector 52, Gurugram, Haryana 122003",
    "hours": "Mon - Sun: 9am - 9pm",
    "phone": "+91 9958858473",
    "sales_phone": "+91 9958187021",
}

# Noida Office
NOIDA_OFFICE = {
    "address": "Plot No B.L.K 15, Basement, Sector 116, Noida, UP 201301",
    "hours": "Mon - Sun: 9am - 9pm",
    "phone": "+91 9958440038",
    "sales_phone": "+91 9958440038",
}

# Quick access
SALES_PHONE_GURGAON = GURGAON_OFFICE["sales_phone"]
SALES_PHONE_NOIDA = NOIDA_OFFICE["sales_phone"]
SUPPORT_EMAIL = "support@rentbasket.com"
WEBSITE = "https://rentbasket.com"

# ========================================
# LOGGING CONFIGURATION
# ========================================
import os as _os
LOGS_DIRECTORY = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logs")

# ========================================
# BOT PERSONALITY
# ========================================
BOT_NAME = "Ku"
BOT_GREETING = f"Hi! I'm *{BOT_NAME}*, RentBasket's WhatsApp assistant. 😊"

# ========================================
# SERVICE AREAS
# ========================================
SERVICEABLE_PINCODES = {
    # Gurgaon sectors (122xxx)
    "122001", "122002", "122003", "122004", "122005", "122006", "122007", "122008",
    "122009", "122010", "122011", "122015", "122016", "122017", "122018", "122022",
    "122101", "122102", "122103", "122104", "122105",
    # Noida sectors (201xxx)
    "201301", "201303", "201304", "201305", "201306", "201307", "201308", "201309",
    "201310", "201312", "201313", "201314", "201318",
    # Greater Noida
    "201306", "201310",
}

# Border areas - need to check with sales
BORDER_PINCODES = {
    "122413", "122414",  # Manesar area
}

# ========================================
# DURATION OPTIONS
# ========================================
VALID_DURATIONS = [3, 6, 9, 12, 18, 24]
DURATION_TO_INDEX = {3: 0, 6: 1, 9: 2, 12: 3, 18: 3, 24: 3}
