# app.py
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import json
import os
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# Mongo + FAISS setup (matches store_to_mongo.py)
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "papers_db"
COLL_NAME = "neurips_2024"
FAISS_INDEX_PATH = "faiss_index.bin"
ID_MAP_PATH = "id_map.json"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Flask app
app = Flask(__name__)

# Connect to Mongo
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coll = db[COLL_NAME]

# Load embedding model
model = SentenceTransformer(EMBED_MODEL)

@app.route("/")
def home():
    return """
    <h2>🧠 NeurIPS 2024 Paper Search API</h2>
    <p>Use the endpoint: <code>/search?query=YOUR_QUERY&mode=exact|semantic&limit=10</code></p>
    <p>Example: <a href='/search?query=diffusion&mode=exact'>Search "diffusion"</a></p>
    """

# Load FAISS index and ID map
def load_faiss():
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(ID_MAP_PATH):
        raise RuntimeError("❌ FAISS index or id_map.json not found. Run store_to_mongo.py first.")
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(ID_MAP_PATH, "r", encoding="utf-8") as f:
        id_map = json.load(f)
    print(f"✅ Loaded FAISS index with {len(id_map)} vectors.")
    return index, id_map

faiss_index, id_map = load_faiss()

# --- SEMANTIC SEARCH ---
def semantic_search(query, top_k=10):
    qvec = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(qvec)
    D, I = faiss_index.search(qvec, top_k)
    results = []
    for idx in I[0]:
        if idx < 0 or idx >= len(id_map):
            continue
        mongo_id = id_map[idx]
        try:
            doc = coll.find_one({"_id": ObjectId(mongo_id)})
        except Exception:
            doc = coll.find_one({"_id": mongo_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
    return results


# --- EXACT SEARCH ---
def exact_search(query, limit=10):
    cursor = coll.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(limit)

    results = []
    for d in cursor:
        d["_id"] = str(d["_id"])
        results.append(d)
    return results


# --- ROUTE ---
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "")
    mode = request.args.get("mode", "exact").lower()
    limit = int(request.args.get("limit", 10))

    if not query:
        return jsonify({"error": "query parameter required"}), 400

    if mode == "exact":
        results = exact_search(query, limit)
    elif mode == "semantic":
        results = semantic_search(query, limit)
    else:
        return jsonify({"error": "mode must be 'exact' or 'semantic'"}), 400

    return jsonify({
        "query": query,
        "mode": mode,
        "count": len(results),
        "results": results
    })


# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
