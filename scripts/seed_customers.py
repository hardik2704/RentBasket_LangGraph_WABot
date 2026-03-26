#!/usr/bin/env python3
"""
Seed script for RentBasket Customers table.
Populates the database with realistic dummy customer data for testing.
"""

import os
import sys
import json
from datetime import datetime, timezone

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_query, is_db_available
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CUSTOMERS_DATA = [
    {
        "name": "Hardik Sharma",
        "email": "hardik.s@example.com",
        "phone_number": "9958448249",
        "location_address": "Sector 45, Gurgaon, Haryana",
        "pincode": "122003",
        "member_since": "2023-11-15T10:00:00Z",
        "rented_items": [
            {"id": 101, "name": "Double Bed with Mattress", "rent_per_month": 1200, "start_date": "2023-11-16"},
            {"id": 205, "name": "300L Refrigerator (Double Door)", "rent_per_month": 850, "start_date": "2023-11-16"}
        ]
    },
    {
        "name": "Anjali Verma",
        "email": "anjali.v@gmail.com",
        "phone_number": "919876543210",
        "location_address": "Flat 402, Sunshine Apartments, Sector 62, Noida",
        "pincode": "201301",
        "member_since": "2024-01-10T14:30:00Z",
        "rented_items": [
            {"id": 302, "name": "3-Seater Premium Sofa (Grey)", "rent_per_month": 900, "start_date": "2024-01-12"},
            {"id": 401, "name": "1.5 Ton Split AC", "rent_per_month": 2200, "start_date": "2024-01-15"}
        ]
    },
    {
        "name": "Rajesh Kumar",
        "email": "kumar.rajesh@outlook.com",
        "phone_number": "919999888777",
        "location_address": "H-Block, Saket, New Delhi",
        "pincode": "110017",
        "member_since": "2023-06-20T09:15:00Z",
        "rented_items": [
            {"id": 505, "name": "Fully Automatic Washing Machine", "rent_per_month": 750, "start_date": "2023-06-22"}
        ]
    },
    {
        "name": "Sneha Kapoor",
        "email": "sneha.k@yahoo.com",
        "phone_number": "918882223334",
        "location_address": "Indirapuram, Ghaziabad",
        "pincode": "201014",
        "member_since": "2023-09-05T11:45:00Z",
        "rented_items": []
    }
]

def seed_customers():
    """Create the table and insert dummy data."""
    if not is_db_available():
        print("❌ Database not available. Check your DATABASE_URL in .env")
        return

    print("🚀 Initializing Customers table...")
    
    # 1. Create Table (if not exists)
    schema_query = """
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone_number TEXT UNIQUE NOT NULL,
        location_address TEXT,
        pincode TEXT,
        rented_items JSONB DEFAULT '[]',
        member_since TIMESTAMPTZ DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
    """
    
    try:
        execute_query(schema_query)
        print("✅ Table 'customers' is ready.")
        
        # 2. Insert Data
        print(f"📦 Seeding {len(CUSTOMERS_DATA)} records...")
        
        insert_query = """
        INSERT INTO customers (name, email, phone_number, location_address, pincode, rented_items, member_since)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (phone_number) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            location_address = EXCLUDED.location_address,
            pincode = EXCLUDED.pincode,
            rented_items = EXCLUDED.rented_items,
            member_since = EXCLUDED.member_since,
            updated_at = NOW();
        """
        
        for cust in CUSTOMERS_DATA:
            params = (
                cust["name"],
                cust["email"],
                cust["phone_number"],
                cust["location_address"],
                cust["pincode"],
                json.dumps(cust["rented_items"]),
                cust["member_since"]
            )
            execute_query(insert_query, params)
            print(f"   ✔ Seeded/Updated: {cust['name']} ({cust['phone_number']})")
            
        print("\n🎉 Seeding complete!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")

if __name__ == "__main__":
    seed_customers()
