#!/usr/bin/env python3
"""
One-time database setup script for RentBasket WhatsApp Bot.
Creates the sessions, messages, and analytics_events tables.

Usage:
    DATABASE_URL=postgresql://... python scripts/setup_db.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SCHEMA_SQL = """
-- =============================================
-- TABLE 1: sessions
-- =============================================
CREATE TABLE IF NOT EXISTS sessions (
    id              SERIAL PRIMARY KEY,
    phone_number    TEXT NOT NULL,
    user_name       TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ DEFAULT NOW(),
    conversation_stage TEXT DEFAULT 'greeting',
    active_agent    TEXT DEFAULT 'sales',
    pincode         TEXT,
    city            TEXT,
    duration_months INT,
    items           JSONB DEFAULT '[]',
    is_bulk_order   BOOLEAN DEFAULT FALSE,
    needs_human     BOOLEAN DEFAULT FALSE,
    total_messages  INT DEFAULT 0,
    handoff_reason  TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_phone ON sessions(phone_number);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(last_active_at DESC);

-- =============================================
-- TABLE 2: messages
-- =============================================
CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    session_id      INT REFERENCES sessions(id) ON DELETE CASCADE,
    phone_number    TEXT NOT NULL,
    sender          TEXT NOT NULL,
    sender_name     TEXT,
    message         TEXT NOT NULL,
    wa_message_id   TEXT,
    agent_used      TEXT,
    tools_called    TEXT[],
    intent          TEXT,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone_number);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_time ON messages(timestamp DESC);

-- =============================================
-- TABLE 3: analytics_events
-- =============================================
CREATE TABLE IF NOT EXISTS analytics_events (
    id              SERIAL PRIMARY KEY,
    phone_number    TEXT NOT NULL,
    session_id      INT REFERENCES sessions(id),
    event_type      TEXT NOT NULL,
    event_data      JSONB DEFAULT '{}',
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_time ON analytics_events(timestamp DESC);
"""


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable is not set.")
        print("   Set it in your .env file or export it:")
        print("   export DATABASE_URL=postgresql://user:pass@host:port/dbname")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2-binary is required. Run: pip install psycopg2-binary")
        sys.exit(1)

    print(f"🚀 Connecting to database...")
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        print("✅ Connected!")

        print("📦 Creating tables...")
        cur.execute(SCHEMA_SQL)
        conn.commit()

        # Verify tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('sessions', 'messages', 'analytics_events')
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"✅ Tables created: {', '.join(tables)}")

        cur.close()
        conn.close()
        print("\n🎉 Database setup complete!")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
