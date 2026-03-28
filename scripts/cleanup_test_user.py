import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.firebase_client import get_db

def cleanup_test_user():
    db = get_db()
    if not db:
        print("❌ Firebase not initialized.")
        return

    phone = "9958448249"
    print(f"🧹 Cleaning up test user: {phone}")

    # Delete from customers collection
    customer_ref = db.collection("customers").document(phone)
    if customer_ref.get().exists:
        customer_ref.delete()
        print(f"✅ Deleted customer document for {phone}")
    else:
        print(f"ℹ️ No customer document found for {phone}")

    # Optionally delete from leads too if you want a fresh start
    lead_ref = db.collection("leads").document(phone)
    if lead_ref.get().exists:
        lead_ref.delete()
        print(f"✅ Deleted lead document for {phone}")

    # Optionally delete sessions for a clean slate
    # Note: Sessions might be many, usually we don't delete them unless requested.

    print("✨ Cleanup complete!")

if __name__ == "__main__":
    cleanup_test_user()
