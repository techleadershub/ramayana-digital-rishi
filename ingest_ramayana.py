"""
Ramayana Verse Ingestion to Qdrant Vector Database
Ingests Valmiki Ramayana verses for semantic search and thematic research
"""

import json
import yaml
import logging
from typing import List, Dict, Any
from pathlib import Path
from tqdm import tqdm

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class RamayanaIngestor:
    """Handles ingestion of Ramayana verses into Qdrant vector database"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the ingestor with configuration"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.client = None
        self.model = None
        self.stats = {
            'total_verses': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.config['processing']['log_file']
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_qdrant(self):
        """Initialize Qdrant client and create collection"""
        self.logger.info("Initializing Qdrant client...")
        
        qdrant_config = self.config['qdrant']
        mode = os.environ.get("QDRANT_MODE", qdrant_config.get('mode', 'server'))
        host = os.environ.get("QDRANT_HOST", qdrant_config.get('host', 'localhost'))
        port = int(os.environ.get("QDRANT_PORT", qdrant_config.get('port', 6333)))
        qdrant_url = os.environ.get("QDRANT_URL")
        
        try:
            if mode == 'local':
                storage_path = qdrant_config.get('path', './qdrant_storage')
                self.logger.info(f"Using Qdrant in LOCAL mode with storage at: {storage_path}")
                self.client = QdrantClient(path=storage_path)
            elif qdrant_url:
                self.logger.info(f"Using Qdrant via URL...")
                self.client = QdrantClient(url=qdrant_url)
            else:
                self.logger.info(f"Using Qdrant in SERVER mode at {host}:{port}")
                self.client = QdrantClient(host=host, port=port)
                
                # Test connection
                self.logger.info("Testing Qdrant connection...")
                collections = self.client.get_collections().collections
                self.logger.info(f"Successfully connected to Qdrant. Found {len(collections)} existing collections.")
            
        except Exception as e:
            if mode == 'server':
                self.logger.error(f"Failed to connect to Qdrant at {qdrant_config['host']}:{qdrant_config['port']}")
                self.logger.error("Make sure Qdrant is running. You can start it with: docker run -p 6333:6333 qdrant/qdrant")
                self.logger.error("Or change mode to 'local' in config.yaml to use file-based storage")
            else:
                self.logger.error(f"Failed to initialize local Qdrant at {storage_path}")
            raise ConnectionError(f"Cannot initialize Qdrant: {e}") from e
        
        collection_name = qdrant_config['collection_name']
        
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)
        
        if collection_exists:
            self.logger.warning(f"Collection '{collection_name}' already exists. Deleting...")
            try:
                self.client.delete_collection(collection_name)
                self.logger.info("Old collection deleted successfully")
            except Exception as e:
                self.logger.error(f"Failed to delete existing collection: {e}")
                raise
        
        # Create new collection
        self.logger.info(f"Creating collection '{collection_name}'...")
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384,  # Dimension for all-MiniLM-L6-v2
                    distance=Distance.COSINE
                )
            )
            self.logger.info("Collection created successfully!")
        except Exception as e:
            self.logger.error(f"Failed to create collection: {e}")
            raise
    
    def initialize_embedding_model(self):
        """Initialize sentence transformer model"""
        model_name = self.config['embedding']['model_name']
        self.logger.info(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.logger.info("Model loaded successfully!")
    
    def load_verses(self) -> List[Dict]:
        """Load verses from JSON file"""
        source_file = self.config['data']['source_file']
        self.logger.info(f"Loading verses from {source_file}...")
        
        with open(source_file, 'r', encoding='utf-8') as f:
            verses = json.load(f)
        
        self.stats['total_verses'] = len(verses)
        self.logger.info(f"Loaded {len(verses):,} verses")
        return verses
    
    def prepare_verse_for_embedding(self, verse: Dict) -> tuple[str, Dict, bool]:
        """
        Prepare a verse for embedding
        Returns: (embedding_text, metadata, should_process)
        """
        translation = verse.get('translation') or ''
        explanation = verse.get('explanation') or ''
        translation = translation.strip() if translation else ''
        explanation = explanation.strip() if explanation else ''
        
        # Skip if no content for embedding
        if self.config['data']['skip_without_content']:
            if not translation and not explanation:
                return None, None, False
        
        # Create embedding text (translation + explanation for thematic search)
        embedding_parts = []
        if translation:
            embedding_parts.append(translation)
        if explanation:
            embedding_parts.append(explanation)
        
        embedding_text = " ".join(embedding_parts)
        
        # If still no content, skip
        if not embedding_text:
            return None, None, False
        
        # Create verse ID
        kanda = verse.get('kanda', 'unknown')
        sarga = verse.get('sarga', 0)
        shloka = verse.get('shloka', 0)
        verse_id = f"{kanda.lower().replace(' ', '_')}_{sarga}_{shloka}"
        
        # Prepare metadata
        metadata = {
            'verse_id': verse_id,
            'kanda': kanda,
            'sarga': sarga,
            'shloka': shloka,
            'shloka_text': verse.get('shloka_text', ''),
            'transliteration': verse.get('transliteration', ''),
            'translation': translation,
            'explanation': explanation,
            'comments': verse.get('comments', ''),
            'has_translation': bool(translation),
            'has_explanation': bool(explanation),
        }
        
        return embedding_text, metadata, True
    
    def ingest_verses(self, verses: List[Dict]):
        """Ingest verses into Qdrant"""
        batch_size = self.config['embedding']['batch_size']
        collection_name = self.config['qdrant']['collection_name']
        
        self.logger.info(f"Starting verse ingestion with batch size: {batch_size}...")
        self.logger.info(f"Target collection: {collection_name}")
        
        # Prepare batches
        batch_texts = []
        batch_metadata = []
        batch_ids = []
        point_id = 0
        processed_count = 0
        
        # Process verses with progress bar
        for idx, verse in enumerate(tqdm(verses, desc="Processing verses", 
                         disable=not self.config['processing']['show_progress']), 1):
            try:
                embedding_text, metadata, should_process = self.prepare_verse_for_embedding(verse)
                
                if not should_process:
                    self.stats['skipped'] += 1
                    self.logger.debug(f"Skipped verse at index {idx} (no content)")
                    continue
                
                batch_texts.append(embedding_text)
                batch_metadata.append(metadata)
                batch_ids.append(point_id)
                point_id += 1
                
                # Log progress every 100 verses
                if idx % 100 == 0:
                    self.logger.info(f"Progress: {idx}/{len(verses)} verses examined, "
                                   f"{self.stats['processed']} indexed, "
                                   f"{self.stats['skipped']} skipped")
                
                # Process batch when full
                if len(batch_texts) >= batch_size:
                    try:
                        self._process_batch(batch_texts, batch_metadata, batch_ids, collection_name)
                        processed_count += len(batch_texts)
                        self.logger.info(f"Batch uploaded: {processed_count} verses indexed so far")
                    except Exception as batch_error:
                        self.logger.error(f"Failed to process batch: {batch_error}", exc_info=True)
                        self.stats['errors'] += len(batch_texts)
                    
                    batch_texts = []
                    batch_metadata = []
                    batch_ids = []
                
            except Exception as e:
                verse_ref = f"{verse.get('kanda', 'unknown')} {verse.get('sarga', '?')}:{verse.get('shloka', '?')}"
                self.logger.error(f"Error processing verse {verse_ref}: {e}", exc_info=True)
                self.stats['errors'] += 1
        
        # Process remaining batch
        if batch_texts:
            try:
                self.logger.info(f"Processing final batch of {len(batch_texts)} verses...")
                self._process_batch(batch_texts, batch_metadata, batch_ids, collection_name)
                self.logger.info("Final batch uploaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to process final batch: {e}", exc_info=True)
                self.stats['errors'] += len(batch_texts)
        
        self.logger.info("Ingestion completed!")
        self._print_stats()
    
    def _process_batch(self, texts: List[str], metadata_list: List[Dict], 
                      ids: List[int], collection_name: str):
        """Process a batch of verses"""
        try:
            self.logger.debug(f"Processing batch of {len(texts)} verses...")
            
            # Generate embeddings
            self.logger.debug("Generating embeddings...")
            embeddings = self.model.encode(texts, show_progress_bar=False)
            self.logger.debug(f"Generated {len(embeddings)} embeddings")
            
            # Create points
            self.logger.debug("Creating Qdrant points...")
            points = [
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=metadata
                )
                for point_id, embedding, metadata in zip(ids, embeddings, metadata_list)
            ]
            
            # Upload to Qdrant
            self.logger.debug(f"Uploading {len(points)} points to Qdrant...")
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            self.stats['processed'] += len(points)
            self.logger.debug(f"Batch processed successfully. Total processed: {self.stats['processed']}")
            
        except Exception as e:
            self.logger.error(f"Error processing batch: {e}", exc_info=True)
            self.stats['errors'] += len(texts)
            raise
    
    def _print_stats(self):
        """Print ingestion statistics"""
        self.logger.info("\n" + "="*50)
        self.logger.info("INGESTION STATISTICS")
        self.logger.info("="*50)
        self.logger.info(f"Total verses in file: {self.stats['total_verses']:,}")
        self.logger.info(f"Successfully processed: {self.stats['processed']:,}")
        self.logger.info(f"Skipped (no content): {self.stats['skipped']:,}")
        self.logger.info(f"Errors: {self.stats['errors']:,}")
        self.logger.info(f"Success rate: {self.stats['processed']/self.stats['total_verses']*100:.1f}%")
        self.logger.info("="*50)
    
    def run(self):
        """Run the complete ingestion pipeline"""
        try:
            self.logger.info("Starting Ramayana ingestion pipeline...")
            
            # Initialize components
            self.initialize_qdrant()
            self.initialize_embedding_model()
            
            # Load and ingest verses
            verses = self.load_verses()
            self.ingest_verses(verses)
            
            self.logger.info("Pipeline completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    print("="*60)
    print("Valmiki Ramayana - Vector Database Ingestion")
    print("="*60)
    print()
    
    ingestor = RamayanaIngestor()
    ingestor.run()


if __name__ == "__main__":
    main()
