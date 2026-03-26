-- Table to store user customer profiles for RentBasket
-- This table is used to differentiate between current customers (Support Agent)
-- and new leads (Sales Agent).

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT UNIQUE NOT NULL, -- The primary identifier from WhatsApp
    location_address TEXT,
    pincode TEXT,
    rented_items JSONB DEFAULT '[]',   -- [{ "id": 1, "name": "Bed", "start_date": "2023-11-15" }]
    member_since TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by phone number
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);

-- Table to store operational support tickets for RentBasket
CREATE TABLE IF NOT EXISTS operations_tickets (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    issue_type TEXT NOT NULL,         -- maintenance, billing, relocation, closure
    sub_intent TEXT,                  -- e.g., "broken_fridge", "MAINT_APPLIANCE"
    summary TEXT,                     -- One-liner title for the dashboard
    description TEXT,                 -- Detailed user-provided description
    priority TEXT DEFAULT 'medium',   -- high, medium, low
    status TEXT DEFAULT 'open',       -- open, in_progress, resolved, closed
    is_urgent BOOLEAN DEFAULT FALSE,
    source TEXT DEFAULT 'WhatsApp',   -- Where ticket originated
    escalation_flag BOOLEAN DEFAULT FALSE, -- True if human escalation triggered
    media_refs JSONB DEFAULT '[]',    -- Any photo/video IDs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickets_phone ON operations_tickets(phone_number);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON operations_tickets(status);
