import os
import numpy as np
from PIL import Image
from tqdm import tqdm
import torch
from transformers import AutoImageProcessor, ViTModel

IMAGE_DIR = "images"
QUERY_IMAGE = "query.jpg"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "google/vit-base-patch32-224-in21k"

processor = AutoImageProcessor.from_pretrained(MODEL_NAME, use_fast=True)
model = ViTModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()

def embed_image(img_path):
    img = Image.open(img_path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(DEVICE)
    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)
        emb = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    emb = emb / np.linalg.norm(emb)
    return emb

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def main():
    image_paths = [
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
    ]

    if not image_paths:
        print(f"No images found in '{IMAGE_DIR}'. Please add some images.")
        return

    path_to_emb = {}
    for path in tqdm(image_paths, desc="Embedding images"):
        try:
            path_to_emb[path] = embed_image(path)
        except Exception as e:
            print(f"Failed embedding {path}: {e}")

    if not os.path.exists(QUERY_IMAGE):
        print(f"Query image '{QUERY_IMAGE}' not found.")
        return

    query_emb = embed_image(QUERY_IMAGE)
    scores = [(cosine_similarity(query_emb, emb), path) for path, emb in path_to_emb.items()]
    scores.sort(reverse=True, key=lambda x: x[0])

    print("\nBest match:", scores[0][1], "→ score:", scores[0][0])
    print("\nTop 5 matches:")
    for s, p in scores[:5]:
        print(f"{p} → {s:.4f}")

if __name__ == "__main__":
    main()
