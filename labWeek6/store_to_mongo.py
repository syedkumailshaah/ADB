# store_to_mongo.py
import json
from pymongo import MongoClient, ASCENDING, errors
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import os
from bson import ObjectId

PAPERS_JSON = "papers.json"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "papers_db"
COLL_NAME = "neurips_2024"
FAISS_INDEX_PATH = "faiss_index.bin"
ID_MAP_PATH = "id_map.json"  # maps faiss idx -> mongo _id (string)

def load_papers():
    with open(PAPERS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def connect_mongo(uri=MONGO_URI):
    client = MongoClient(uri)
    db = client[DB_NAME]
    coll = db[COLL_NAME]
    return coll

def ensure_indexes(coll):
    # text index for exact search on title, authors and keywords
    try:
        coll.create_index([("title", "text"), ("authors", "text"), ("keywords", "text")], default_language="english")
        coll.create_index([("link", ASCENDING)], unique=True)
        print("Indexes created (text index on title/authors/keywords, unique index on link).")
    except errors.OperationFailure as e:
        print("Index creation error:", e)

def compute_embeddings(papers, model_name="all-MiniLM-L6-v2", batch_size=32):
    model = SentenceTransformer(model_name)
    texts = []
    for p in papers:
        # combine title + authors as text for embedding
        txt = p.get("title", "")
        if p.get("authors"):
            txt += " | " + p["authors"]
        texts.append(txt)
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
    return embeddings

def upsert_papers_with_embeddings(coll, papers, embeddings):
    id_map = []  # vector index -> mongo _id
    for idx, p in enumerate(papers):
        doc = {
            "title": p.get("title"),
            "authors": p.get("authors"),
            "link": p.get("link"),
            "keywords": [],  # placeholder: you may add extracted keywords later
            "embedding": embeddings[idx].astype(float).tolist()
        }
        # upsert by link
        res = coll.update_one({"link": doc["link"]}, {"$set": doc}, upsert=True)
        if res.upserted_id:
            oid = res.upserted_id
        else:
            # find the document _id
            found = coll.find_one({"link": doc["link"]}, {"_id": 1})
            oid = found["_id"]
        id_map.append(str(oid))
    return id_map

def build_faiss(embeddings, id_map, index_path=FAISS_INDEX_PATH, id_map_path=ID_MAP_PATH):
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)  # inner product on normalized vectors (we'll normalize)
    # normalize embeddings for cosine similarity with inner product
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    faiss.write_index(index, index_path)
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2)
    print(f"FAISS index saved to {index_path}, id map to {id_map_path}")

def main():
    papers = load_papers()
    if not papers:
        print("No papers found in papers.json. Run scraper.py first.")
        return
    coll = connect_mongo()
    ensure_indexes(coll)
    print("Computing embeddings (sentence-transformers)...")
    embeddings = compute_embeddings(papers)
    print("Upserting papers into MongoDB (this stores embeddings too)...")
    id_map = upsert_papers_with_embeddings(coll, papers, embeddings)
    print("Building FAISS index...")
    build_faiss(embeddings.copy(), id_map)
    print("Done.")

if __name__ == "__main__":
    main()
