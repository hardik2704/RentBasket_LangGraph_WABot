import os
import psycopg2
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from data.products import id_to_name, id_to_price, category_to_id, get_all_categories

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in environment")
    sys.exit(1)

def seed():
    conn = None
    cur = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Cleaning tables...")
        cur.execute("TRUNCATE categories, products, product_base_prices RESTART IDENTITY CASCADE;")
        
        # 2. Insert Categories (with slug)
        # categories = ["geyser", "fridge", ...]
        main_categories = get_all_categories()
        category_map = {} # slug -> uuid
        
        for slug in main_categories:
            name = slug.replace("_", " ").title()
            cur.execute(
                "INSERT INTO categories (name, slug) VALUES (%s, %s) RETURNING id;",
                (name, slug)
            )
            cat_id = cur.fetchone()[0]
            category_map[slug] = cat_id
            
        print(f"Seeded {len(category_map)} categories.")

        # 3. Map PIDs to Categories
        pid_to_cat_slug = {}
        for slug, pids in category_to_id.items():
            if slug in category_map:
                for pid in pids:
                    pid_to_cat_slug[pid] = slug
        
        product_count = 0
        price_count = 0
        
        for pid, name in id_to_name.items():
            slug = pid_to_cat_slug.get(pid)
            if not slug:
                # Fallback search
                for main_slug in main_categories:
                    if pid in category_to_id.get(main_slug, []):
                        slug = main_slug
                        break
            
            if not slug:
                continue
                
            cat_id = category_map[slug]
            
            cur.execute(
                "INSERT INTO products (id, name, category_id) VALUES (%s, %s, %s);",
                (pid, name, cat_id)
            )
            product_count += 1
            
            prices = id_to_price.get(pid)
            if prices:
                duration_map = {3: 5, 6: 6, 9: 7, 12: 8}
                for duration, idx in duration_map.items():
                    if idx < len(prices):
                        price = prices[idx]
                        cur.execute(
                            "INSERT INTO product_base_prices (product_id, duration_months, base_price) VALUES (%s, %s, %s);",
                            (pid, duration, price)
                        )
                        price_count += 1
                
        conn.commit()
        print(f"✅ Success! Seeded {product_count} products and {price_count} price entries.")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    seed()
