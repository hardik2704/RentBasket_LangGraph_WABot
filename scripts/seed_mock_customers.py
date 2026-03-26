"""
Seeding script for RentBasket mock customers to test 4-tier status categories.
- Active Customer: Has active rentals, is_active=True
- Past Customer: No active rentals, is_active=False
- Lead: (Handled by unknown logic or separate table if added later)
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_query, is_db_available

def seed_mock_data():
    if not is_db_available():
        print("❌ Database not available. Check your environment variables.")
        return

    print("🌱 Seeding mock customer data for status testing...")

    # Clear existing data to avoid conflicts for this specific test suite
    # (Optional: Depends on if you want to keep existing data)
    # execute_query("TRUNCATE TABLE customers RESTART IDENTITY CASCADE;")

    customers = [
        # 1. Active Customer (Hardik)
        {
            "name": "Hardik Sharma",
            "email": "hardik@example.com",
            "phone_number": "9958448249",
            "location_address": "806 Pony Express, Gurgaon",
            "pincode": "122001",
            "rented_items": json.dumps([
                {"id": "FRIDGE_SNG_190", "name": "Single Door fridge (190L)", "start_date": "2024-01-15"},
                {"id": "WASH_MTIC_6", "name": "Automatic Washing Machine (6kg)", "start_date": "2024-02-01"}
            ]),
            "is_active": True
        },
        # 2. Past Customer (Disconnected)
        {
            "name": "Ananya Gupta",
            "email": "ananya@example.com",
            "phone_number": "9812345678",
            "location_address": "Flat 202, Sunshine Apts, Noida",
            "pincode": "201301",
            "rented_items": json.dumps([]), # No active rentals
            "is_active": False
        },
        # 3. Active Customer (Recent)
        {
            "name": "Vikram Singh",
            "email": "vikram@example.com",
            "phone_number": "8877665544",
            "location_address": "D-45, Sector 15, Faridabad",
            "pincode": "121001",
            "rented_items": json.dumps([
                {"id": "SOFA_3STR_GRY", "name": "3-Seater Fabric Sofa (Grey)", "start_date": "2024-03-10"}
            ]),
            "is_active": True
        },
        # 4. Active Customer (Multiple Appliances / Ambiguous Maintenance)
        {
            "name": "Arjun Patel",
            "email": "arjun@example.com",
            "phone_number": "7766554433",
            "location_address": "C-12, Phase 1, DLF, Gurgaon",
            "pincode": "122002",
            "rented_items": json.dumps([
                {"id": "AC_WIN_15", "name": "Window AC (1.5 Ton)", "start_date": "2023-05-10"},
                {"id": "FRIDGE_DBL_250", "name": "Double Door Fridge (250L)", "start_date": "2023-05-10"}
            ]),
            "is_active": True
        },
        # 5. Lead / Angry Unknown Customer (Will be treated as unknown, but forces escalation)
        {
            "name": "Rahul Verma",
            "email": "rahul.v@example.com",
            "phone_number": "9100000000",
            "location_address": "Unknown",
            "pincode": "000000",
            "rented_items": json.dumps([]),
            "is_active": False
        }
    ]

    for cust in customers:
        query = """
        INSERT INTO customers (name, email, phone_number, location_address, pincode, rented_items, is_active, member_since)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (phone_number) DO UPDATE SET
            is_active = EXCLUDED.is_active,
            rented_items = EXCLUDED.rented_items,
            name = EXCLUDED.name;
        """
        try:
            execute_query(query, (
                cust["name"], cust["email"], cust["phone_number"], 
                cust["location_address"], cust["pincode"], 
                cust["rented_items"], cust["is_active"]
            ))
            print(f"✅ Synced customer: {cust['name']} ({cust['phone_number']})")
        except Exception as e:
            print(f"❌ Error seeding {cust['name']}: {e}")

    print("\n✨ Seeding complete. Use these numbers for testing:")
    print("9958448249 -> ACTIVE_CUSTOMER (Hardik)")
    print("7766554433 -> ACTIVE_CUSTOMER (Arjun - Multiple Appliances)")
    print("9812345678 -> PAST_CUSTOMER (Ananya)")
    print("9100000000 -> UNKNOWN/LEAD / Angry Customer (Rahul)")

if __name__ == "__main__":
    seed_mock_data()
