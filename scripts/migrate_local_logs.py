"""
Historical Log Migrator for RentBasket WhatsApp Bot (Robust Edit).
Avoids Firestore 'Deadline Exceeded' by using per-session commits and chunked batches.
"""

import os
import re
import sys
import time
from datetime import datetime
from google.cloud import firestore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db

LOGS_DIR = "logs"
SESSION_SEP = "--------------------------------------------------"
BATCH_SIZE = 400 # Firestore limit is 500

def parse_log_file(filepath):
    """Parses a single log file into a list of sessions."""
    filename = os.path.basename(filepath)
    phone = filename.replace(".txt", "")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split into raw sessions
    raw_sessions = content.split(SESSION_SEP)
    sessions = []
    
    # Regex to capture: Date, Time - Sender (ignored for meta): Message
    msg_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2}, \d{2}:\d{2} [ap]m) - (.*?): (.*)$', re.MULTILINE)
    
    for raw in raw_sessions:
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        if not lines: continue
        
        # Clean up lines (ignore HTML remnants)
        cleaned_lines = [l for l in lines if msg_pattern.match(l) or "--- Session started ---" in l or "New session started" in l]
        if not cleaned_lines: continue

        # Try to extract the first timestamp for the session creation time
        ts_match = msg_pattern.search(raw)
        if ts_match:
            try:
                dt = datetime.strptime(ts_match.group(1).lower(), "%d/%m/%y, %I:%M %p")
            except:
                dt = datetime.now()
        else:
            dt = datetime.now()
            
        session_data = {
            "phone": phone,
            "created_at": dt,
            "transcript": cleaned_lines,
            "messages": []
        }
        
        for line in cleaned_lines:
            m = msg_pattern.match(line)
            if m:
                ts_str, sender_raw, message = m.groups()
                sender_type = "bot" if sender_raw.lower().strip() == "ku" else "user"
                sender_name = "Ku" if sender_type == "bot" else sender_raw.split(" (")[0]
                
                try:
                    ts_dt = datetime.strptime(ts_str.lower(), "%d/%m/%y, %I:%M %p")
                except:
                    ts_dt = dt

                session_data["messages"].append({
                    "phone": phone,
                    "sender": sender_type,
                    "sender_name": sender_name,
                    "message": message,
                    "timestamp": ts_dt
                })
        
        if session_data["messages"]:
            sessions.append(session_data)
        
    return sessions

def migrate():
    db = get_db()
    if not db:
        print("❌ Firebase not available.")
        return
        
    print(f"🚀 Starting Migration from {LOGS_DIR} (Robustly)...")
    
    files = sorted([f for f in os.listdir(LOGS_DIR) if f.startswith("91") and f.endswith(".txt")])
    total_sessions_migrated = 0

    for filename in files:
        filepath = os.path.join(LOGS_DIR, filename)
        print(f"📖 Parsing {filename}...")
        try:
            sessions = parse_log_file(filepath)
        except Exception as e:
            print(f"   ❌ Failed to parse {filename}: {e}")
            continue
            
        for s in sessions:
            try:
                # 1. Create Session Doc
                session_ref = db.collection("sessions").document()
                session_ref.set({
                    "phone_number": s["phone"],
                    "created_at": s["created_at"],
                    "last_active_at": s["created_at"],
                    "live_transcript": s["transcript"],
                    "is_active": False,
                    "is_historical": True,
                    "total_messages": len(s["messages"])
                })
                
                # 2. Upload Messages in Chunks
                messages = s["messages"]
                for i in range(0, len(messages), BATCH_SIZE):
                    chunk = messages[i:i + BATCH_SIZE]
                    batch = db.batch()
                    for msg in chunk:
                        m_ref = session_ref.collection("messages").document()
                        batch.set(m_ref, msg)
                    batch.commit()
                    time.sleep(0.1) # Soft rate limiting
                
                total_sessions_migrated += 1
                if total_sessions_migrated % 10 == 0:
                    print(f"   ✅ {total_sessions_migrated} sessions uploaded...")
            
            except Exception as e:
                print(f"   ❌ Error uploading session for {s['phone']}: {e}")
                time.sleep(1)
            
    print(f"\n✨ Migration complete! Total sessions uploaded: {total_sessions_migrated}")

if __name__ == "__main__":
    migrate()
