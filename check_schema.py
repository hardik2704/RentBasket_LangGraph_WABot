import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_schema():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    with conn.cursor() as cur:
        print("--- Columns in 'messages' ---")
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'messages';")
        for row in cur.fetchall():
            print(row)
            
        print("\n--- Columns in 'sessions' ---")
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'sessions';")
        for row in cur.fetchall():
            print(row)

    conn.close()

if __name__ == "__main__":
    check_schema()
