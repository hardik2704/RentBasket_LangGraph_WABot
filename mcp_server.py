# mcp_server.py
import os
import requests
import chromadb
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# Import local data as fallback
from data.products import id_to_name, category_to_id, id_to_price

mcp = FastMCP("rentbasket-products")
API_BASE = "https://testapi.rentbasket.com"

# Setup ChromaDB
CHROMA_PATH = "./data/chroma_db"
os.makedirs(os.path.dirname(CHROMA_PATH), exist_ok=True)

# OpenAI Embedding Function
# Using the key from environment as it's required for embeddings
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ.get("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name="products",
    embedding_function=openai_ef
)

def auth_headers() -> Dict[str, str]:
    key = os.environ.get("RENTBASKET_API_KEY", "")
    return {
        "Accept": "application/json",
        "x-api-key": key,
        "Authorization": f"Bearer {key}",
    }

@mcp.tool()
def build_semantic_index() -> str:
    """
    Build or refresh the semantic index from local product data.
    This creates searchable embeddings for each product.
    """
    ids = []
    documents = []
    metadatas = []
    
    # Reverse mapping for categories
    pid_to_cats = {}
    for cat, pids in category_to_id.items():
        for pid in pids:
            if pid not in pid_to_cats:
                pid_to_cats[pid] = []
            pid_to_cats[pid].append(cat)
            
    for pid, name in id_to_name.items():
        cats = ", ".join(pid_to_cats.get(pid, []))
        prices = id_to_price.get(pid, [0, 0, 0, 0])
        
        # Searchable text
        doc = f"{name} | {cats}"
        
        ids.append(str(pid))
        documents.append(doc)
        metadatas.append({
            "name": name,
            "categories": cats,
            "pid": pid,
            "price_12mo": float(prices[3])
        })
        
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    return f"Indexed {len(ids)} products successfully in ChromaDB."

@mcp.tool()
def semantic_product_search(
    query: str, 
    max_price: Optional[float] = None,
    n_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for products semantically using natural language.
    Example: "Double door fridge under 1000"
    """
    # Simple filtering (ChromaDB 'where' is limited)
    where = None
    if max_price:
        where = {"price_12mo": {"$lte": max_price}}
        
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where
    )
    
    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "name": results["metadatas"][0][i]["name"],
            "score": results["distances"][0][i],
            "price_12mo": results["metadatas"][0][i]["price_12mo"]
        })
    return output

@mcp.tool()
def get_amenity_types(category_id: int, subcategory_id: int, absolute_amenity_type: int) -> Dict[str, Any]:
    """
    Source-of-truth fetch from RentBasket API.
    """
    url = f"{API_BASE}/get-amenity-types"
    params = {
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "absolute_amenity_type": absolute_amenity_type,
    }
    r = requests.get(url, params=params, headers=auth_headers(), timeout=20)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    mcp.run()