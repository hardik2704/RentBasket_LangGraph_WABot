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
    print("9958448249 -> ACTIVE_CUSTOMER")
    print("9812345678 -> PAST_CUSTOMER")
    print("9100000000 -> UNKNOWN/LEAD")

if __name__ == "__main__":
    seed_mock_data()
