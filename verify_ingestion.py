"""
Verification script to check if ingestion was successful.
Checks Qdrant collections for data and provides statistics.
"""

import os
import yaml
from qdrant_client import QdrantClient

def load_config(config_path: str = "config.yaml"):
    """Load configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def verify_ingestion():
    """Verify if ingestion was successful by checking Qdrant collections"""
    config = load_config()
    qdrant_config = config['qdrant']
    
    # Initialize Qdrant client
    mode = os.environ.get("QDRANT_MODE", qdrant_config.get('mode', 'server'))
    host = os.environ.get("QDRANT_HOST", qdrant_config.get('host', 'localhost'))
    port = int(os.environ.get("QDRANT_PORT", qdrant_config.get('port', 6333)))
    qdrant_url = os.environ.get("QDRANT_URL")
    
    print("=" * 60)
    print("INGESTION VERIFICATION")
    print("=" * 60)
    
    try:
        if mode == 'local':
            storage_path = qdrant_config.get('path', './qdrant_storage')
            print(f"Connecting to Qdrant (LOCAL) at: {storage_path}")
            client = QdrantClient(path=storage_path)
        elif qdrant_url:
            print(f"Connecting to Qdrant (URL): {qdrant_url}")
            client = QdrantClient(url=qdrant_url)
        else:
            print(f"Connecting to Qdrant (SERVER) at {host}:{port}")
            client = QdrantClient(host=host, port=port)
        
        # Get all collections
        collections = client.get_collections().collections
        print(f"\n✓ Connected to Qdrant successfully!")
        print(f"  Found {len(collections)} collection(s)")
        
        # Check required collections
        verse_collection = qdrant_config['collection_name']
        sarga_collection = qdrant_config.get('sarga_collection_name', 'ramayana_sargas')
        
        required = [verse_collection, sarga_collection]
        collection_names = [c.name for c in collections]
        
        print("\n" + "=" * 60)
        print("COLLECTION STATUS")
        print("=" * 60)
        
        all_good = True
        
        for collection_name in required:
            if collection_name in collection_names:
                try:
                    # Get collection info
                    info = client.get_collection(collection_name)
                    point_count = info.points_count
                    
                    print(f"\n✓ Collection: '{collection_name}'")
                    print(f"  Status: EXISTS")
                    print(f"  Points (vectors): {point_count:,}")
                    
                    if point_count == 0:
                        print(f"  ⚠️  WARNING: Collection is empty! Ingestion may have failed.")
                        all_good = False
                    elif point_count < 100:
                        print(f"  ⚠️  WARNING: Very few points ({point_count}). Ingestion may be incomplete.")
                        all_good = False
                    else:
                        print(f"  ✓ Collection has data")
                    
                    # Sample a few points to verify structure
                    if point_count > 0:
                        sample = client.scroll(
                            collection_name=collection_name,
                            limit=1
                        )[0]
                        if sample:
                            print(f"  Sample payload keys: {list(sample[0].payload.keys())}")
                            
                except Exception as e:
                    print(f"\n✗ Collection: '{collection_name}'")
                    print(f"  Status: ERROR - {e}")
                    all_good = False
            else:
                print(f"\n✗ Collection: '{collection_name}'")
                print(f"  Status: MISSING")
                print(f"  Action: Run ingestion script")
                all_good = False
        
        print("\n" + "=" * 60)
        if all_good:
            print("✓ INGESTION VERIFICATION: SUCCESS")
            print("  All collections exist and contain data.")
        else:
            print("✗ INGESTION VERIFICATION: FAILED")
            print("  Some collections are missing or empty.")
            print("\n  To fix:")
            print("  1. Run: python ingest_ramayana.py")
            print("  2. Run: python ingest_sargas.py")
            print("  3. Run: python agent_api/ingest.py")
        print("=" * 60)
        
        return all_good
        
    except Exception as e:
        print(f"\n✗ ERROR: Failed to connect to Qdrant")
        print(f"  {e}")
        print("\n  Check:")
        print("  - Qdrant is running")
        print("  - QDRANT_HOST and QDRANT_PORT are correct")
        print("  - Network connectivity")
        return False

if __name__ == "__main__":
    verify_ingestion()

