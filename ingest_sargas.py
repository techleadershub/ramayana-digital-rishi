import json
import os
import yaml
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load Config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def ingest_full_sargas():
    # Initialize Qdrant
    mode = os.environ.get("QDRANT_MODE", config['qdrant'].get('mode', 'server'))
    host = os.environ.get("QDRANT_HOST", config['qdrant'].get('host', 'localhost'))
    port = int(os.environ.get("QDRANT_PORT", config['qdrant'].get('port', 6333)))
    qdrant_url = os.environ.get("QDRANT_URL")

    if mode == 'local':
        client = QdrantClient(path=config['qdrant']['path'])
    elif qdrant_url:
        client = QdrantClient(url=qdrant_url)
    else:
        client = QdrantClient(host=host, port=port)

    collection_name = config['qdrant']['sarga_collection_name']
    
    # Load Model
    # Explicitly load on CPU to avoid meta tensor issues
    # This prevents PyTorch meta tensor errors in production environments
    try:
        model = SentenceTransformer(config['embedding']['model_name'], device='cpu')
        model.eval()  # Set to evaluation mode
        print("Model loaded on CPU!")
    except Exception as e:
        print(f"Warning: Error loading with device='cpu': {e}")
        # Fallback to default loading
        model = SentenceTransformer(config['embedding']['model_name'])
        print("Model loaded with default settings!")
    
    # Create Collection
    # Use higher size if needed, but MiniLM is 384
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    
    # Load Raw Data
    with open(config['data']['source_file'], "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group by Sarga
    groups = {}
    for v in data:
        key = (v['kanda'], v['sarga'])
        if key not in groups: groups[key] = []
        groups[key].append(v)
        
    print(f"Ingesting {len(groups)} Full Sargas...")
    
    points = []
    for i, ((kanda, sarga), verses) in enumerate(tqdm(groups.items(), desc="Ingesting Sargas")):
        
        # 1. Combine all text for context
        full_text = "\n".join([f"Verse {v.get('shloka', '?')}: {v.get('explanation') or ''}" for v in verses])
        
        # 2. Extract a 'Searchable Anchor' (Thematic keywords + First few sentences)
        search_anchor = f"{kanda} Sarga {sarga}\n" + "\n".join([v.get('explanation') or '' for v in verses[:15]])
        
        # Generate Vector
        vector = model.encode(search_anchor).tolist()
        
        points.append(models.PointStruct(
            id=i,
            vector=vector,
            payload={
                "kanda": kanda,
                "sarga": sarga,
                "full_text": full_text,
                "verse_count": len(verses),
                "type": "sarga_chunk"
            }
        ))
        
        if len(points) >= 50:
            client.upsert(collection_name=collection_name, points=points)
            points = []
            
    if points:
        client.upsert(collection_name=collection_name, points=points)
        
    print("Full Sarga Ingestion complete!")

if __name__ == "__main__":
    ingest_full_sargas()
