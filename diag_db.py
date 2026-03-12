import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

print(f"DATABASE_URL ends with: ...{os.getenv('DATABASE_URL')[-20:] if os.getenv('DATABASE_URL') else 'None'}")

try:
    import psycopg2
    print(f"psycopg2 version: {psycopg2.__version__}")
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("✅ Successfully connected to the database!")
    
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables found: {tables}")
        
    conn.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")
