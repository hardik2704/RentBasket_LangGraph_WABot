
import os
from dotenv import load_dotenv
load_dotenv()

from tools.product_tools import get_price_tool
from utils.db import is_db_available

print(f"DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
print(f"DB Available: {is_db_available()}")

print("\n--- Testing Price for ID 1043 (6 months) ---")
result = get_price_tool.invoke({"product_id": 1043, "duration": 6})
print(result)

print("\n--- Testing Price for ID 1043 (3 months) ---")
result = get_price_tool.invoke({"product_id": 1043, "duration": 3})
print(result)
