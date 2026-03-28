"""
Firebase Admin SDK client for RentBasket.
Initializes Firestore using a JSON string from 'FIREBASE_CONFIG' environment variable.
Designed for coherence and evolvability in a Customer Support context.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

_db = None

def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    global _db
    if not firebase_admin._apps:
        config_json = os.getenv("FIREBASE_CONFIG")
        if not config_json:
            print("⚠️ FIREBASE_CONFIG not found in environment!")
            return None
        
        try:
            cred_dict = json.loads(config_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            print("✨ Firebase initialized successfully.")
        except Exception as e:
            print(f"❌ Failed to initialize Firebase: {e}")
            return None
    elif _db is None:
        _db = firestore.client()
    return _db

def get_db():
    return initialize_firebase()

# ==========================================
# FIRESTORE HELPERS
# ==========================================

def upsert_customer(phone: str, customer_data: dict):
    """Save or update customer profile."""
    db = get_db()
    if not db: return
    db.collection("customers").document(phone).set(customer_data, merge=True)

def log_session_msg(session_id: str, message_data: dict):
    """Logs a message into a session's sub-collection."""
    db = get_db()
    if not db: return

    # Update main session metadata
    session_ref = db.collection("sessions").document(session_id)
    ts = datetime.now(timezone.utc)
    sender_label = message_data.get("sender_name", "Unknown")
    msg_text = message_data.get("message", "")
    transcript_line = f"[{ts.strftime('%d/%m/%y, %I:%M %p').lower()}] {sender_label}: {msg_text}"

    session_ref.set({
        "last_active_at": ts,
        "phone_number": message_data.get("phone"),
        "user_name": message_data.get("user_name"),
        "live_transcript": firestore.ArrayUnion([transcript_line])
    }, merge=True)
    
    session_ref.collection("messages").add({
        **message_data,
        "timestamp": datetime.now(timezone.utc)
    })

def log_event(phone: str, event_type: str, event_data: dict = None, session_id: str = None):
    """Logs a business event for analytics."""
    db = get_db()
    if not db: return
    db.collection("analytics").add({
        "phone": phone,
        "session_id": session_id,
        "event_type": event_type,
        "event_data": event_data or {},
        "timestamp": datetime.now(timezone.utc)
    })

def log_ticket(ticket_id: str, ticket_data: dict):
    """Logs a support ticket for the bot."""
    db = get_db()
    if not db: return
    db.collection("tickets").document(ticket_id).set({
        **ticket_data,
        "updated_at": datetime.now(timezone.utc)
    }, merge=True)

def upsert_lead(phone: str, lead_data: dict):
    """
    Save or update lead profile in the 'leads' collection.
    Schema:
    - name: string (Primary name)
    - push_name: string (WhatsApp push name)
    - extracted_name: string (Name mentioned in chat)
    - phone: string
    - delivery_location: {address, city, pincode}
    - product_preferences: [{category, product_id}]
    - final_cart: [{product_id, quantity, duration, final_price}]
    - lead_stage: new | qualified | cart_created | reserved | converted
    - updated_at: timestamp
    """
    db = get_db()
    if not db: return
    
    # Ensure updated_at is always refreshed
    data_to_save = {
        **lead_data,
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Set created_at if it's a new document
    doc_ref = db.collection("leads").document(phone)
    doc = doc_ref.get()
    if not doc.exists:
        data_to_save["created_at"] = datetime.now(timezone.utc)
        data_to_save["lead_stage"] = lead_data.get("lead_stage", "new")
    
    doc_ref.set(data_to_save, merge=True)

def get_lead(phone: str):
    """Retrieve lead data from Firestore."""
    db = get_db()
    if not db: return None
    doc = db.collection("leads").document(phone).get()
    return doc.to_dict() if doc.exists else None


def is_hot_lead(phone: str) -> bool:
    """
    A lead is 'hot' (🔥) when:
      - lead_stage is 'cart_created', 'qualified', or 'browsing'
      - last_message_timestamp was within the past 2 hours

    Used to dynamically swap the primary cart button to
    '🔥 Reserve Now' and show a free-delivery footer.
    """
    db = get_db()
    if not db:
        return False
    try:
        doc = db.collection("leads").document(phone).get()
        if not doc.exists:
            return False
        data = doc.to_dict()
        stage = data.get("lead_stage", "new")
        if stage not in ("cart_created", "qualified", "browsing"):
            return False
        last_ts = data.get("last_message_timestamp")
        if not last_ts:
            return False
        # Normalise to UTC-aware datetime
        if hasattr(last_ts, "tzinfo") and last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_ts).total_seconds() <= 7200  # 2 hours
    except Exception:
        return False
