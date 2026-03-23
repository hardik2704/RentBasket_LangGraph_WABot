import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    with conn.cursor() as cur:
        print("--- Sessions ---")
        cur.execute("SELECT id, phone_number, user_name, started_at FROM sessions ORDER BY id DESC LIMIT 5;")
        for row in cur.fetchall():
            print(row)
            
        print("\n--- Messages ---")
        cur.execute("SELECT id, session_id, phone_number, sender, message, timestamp FROM messages ORDER BY id DESC LIMIT 10;")
        for row in cur.fetchall():
            print(row)
            
        print("\n--- Message Count ---")
        cur.execute("SELECT COUNT(*) FROM messages;")
        print(f"Total messages: {cur.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    check_db()
