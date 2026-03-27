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

from utils.firebase_client import upsert_customer, get_db
from utils.phone_utils import normalize_phone
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
    """Insert dummy data into Firestore."""
    db = get_db()
    if not db:
        print("❌ Firebase not available. Check your FIREBASE_CONFIG in .env")
        return

    print("🚀 Seeding Customers into Firestore...")
    
    try:
        # 2. Insert Data
        print(f"📦 Seeding {len(CUSTOMERS_DATA)} records...")
        
        for cust in CUSTOMERS_DATA:
            # Normalize phone to use as Doc ID
            phone = cust["phone_number"]
            normalized = normalize_phone(phone)
            
            # Prepare data (ISO format strings for dates are fine for Firestore)
            upsert_customer(normalized, {
                "name": cust["name"],
                "email": cust["email"],
                "phone_number": normalized,
                "location_address": cust["location_address"],
                "pincode": cust["pincode"],
                "rented_items": cust["rented_items"],
                "member_since": cust["member_since"],
                "is_active": True,
                "updated_at": datetime.now(timezone.utc)
            })
            print(f"   ✔ Seeded/Updated: {cust['name']} ({normalized})")
            
        print("\n🎉 Seeding complete!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")

if __name__ == "__main__":
    seed_customers()
