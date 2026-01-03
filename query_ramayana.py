"""
Query Interface for Ramayana Vector Database
Enables semantic search and thematic research on Ramayana verses using RAG (Retrieval Augmented Generation)
"""

import yaml
import os
import json
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Try importing OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: 'openai' library not found. RAG features will be disabled. Run 'pip install openai' to enable.")

class OpenAILLM:
    """Uses OpenAI API (gpt-4o-mini) for analysis."""
    def __init__(self, api_key: str = None):
        # Use provided key or env var
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API Key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"

    def analyze_verses_batch(self, verses: List[str], query: str) -> List[Dict]:
        """Calls OpenAI to classify a BATCH of verses."""
        verses_text = "\n\n".join([f"Verse {i+1}:\n{v}" for i, v in enumerate(verses)])
        
        prompt = f"""
        Analyze the following {len(verses)} Ramayana verses for the query: "{query}"

        {verses_text}

        TASK: IDENTIFY ONLY UNIVERSAL WISDOM ("SUBHASHITAS").
        
        We are building a "Book of General Leadership Quotes". 
        WE MUST REJECT 95% of the verses because they are narrative (story-telling).
        
        EXAMPLES:
        -----------------------
        Verse: "Rama, the son of Dasaratha, took his bow and looked at the ocean."
        -> REJECT (Narrative/Descriptive)
        
        Verse: "Sugriva said to Angada: 'Go south and find Sita'."
        -> REJECT (Specific Instruction/Dialog)
        
        Verse: "Enthusiasm is the root of prosperity; there is no greater enemy than laziness."
        -> KEEP (Universal Maxim)
        
        Verse: "A king who does not protect his subjects is like a barren cloud."
        -> KEEP (Universal Principle)
        -----------------------

        INSTRUCTIONS FOR EACH VERSE:
        1. "Is this a story beat (action/dialog)?" -> If YES, DISCARD immediately.
        2. "Does it mention specific names (Rama, Sugriva, Ravana) as the *subject* of the action?" -> If YES, DISCARD (usually).
        3. "Is it a general rule asking 'How should one behave?'" -> If YES, KEEP.
        
        Output ONLY JSON:
        {{
            "results": [
                {{ "index": 1, "keep": false, "category": "Narrative", "reason": "Describes specific action of a character" }},
                {{ "index": 2, "keep": true,  "category": "Wisdom",    "reason": "Universal rule about [Topic]", "modern_take": "..." }}
            ]
        }}
        """

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a ruthless editor. You REJECT almost everything. You NEVER hallucinates a lesson from a simple description."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = json.loads(completion.choices[0].message.content)
            results = content.get("results", [])
            # Fill missing entries if any
            if len(results) < len(verses):
                results.extend([{"index": i+1, "keep": False, "category": "Missing", "reason": "LLM output incomplete"} for i in range(len(results), len(verses))]) 
            return results
        except Exception as e:
            print(f"    ⚠️ LLM Batch Error: {e}")
            return [{"index": i+1, "keep": True, "category": "Error", "reason": f"Batch Error"} for i in range(len(verses))]


class RamayanaSearcher:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize searcher with configuration"""
        # Resolve config path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resolved_path = os.path.join(base_dir, config_path)
        
        with open(resolved_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Update path in config to be absolute as well
        if self.config['qdrant']['mode'] == 'local':
             # Resolve relative path in config
             storage_path = self.config['qdrant']['path']
             if not os.path.isabs(storage_path):
                 self.config['qdrant']['path'] = os.path.join(base_dir, storage_path)
        
        # Initialize Qdrant
        qdrant_config = self.config['qdrant']
        # Use env vars if available, otherwise config
        mode = os.environ.get("QDRANT_MODE", qdrant_config.get('mode', 'server'))
        host = os.environ.get("QDRANT_HOST", qdrant_config.get('host', 'localhost'))
        port = int(os.environ.get("QDRANT_PORT", qdrant_config.get('port', 6333)))
        qdrant_url = os.environ.get("QDRANT_URL") # For Railway public networks
        
        api_key = os.environ.get("QDRANT_API_KEY")
        timeout = int(os.environ.get("QDRANT_TIMEOUT", 30))
        
        if mode == 'local':
            storage_path = qdrant_config.get('path', './qdrant_storage')
            print(f"Using Qdrant in LOCAL mode with storage at: {storage_path}")
            self.client = QdrantClient(path=storage_path, timeout=timeout)
        elif qdrant_url:
            print(f"Using Qdrant via URL...")
            self.client = QdrantClient(url=qdrant_url, api_key=api_key, timeout=timeout)
        else:
            print(f"Using Qdrant in SERVER mode at {host}:{port}")
            self.client = QdrantClient(host=host, port=port, api_key=api_key, timeout=timeout)
        
        self.collection_name = qdrant_config['collection_name']
        self.sarga_collection_name = qdrant_config.get('sarga_collection_name', 'ramayana_sargas')
        
        # Load embedding model
        model_name = self.config['embedding']['model_name']
        print(f"Loading model: {model_name}...")
        try:
            self.model = SentenceTransformer(model_name)
            self.model.eval()
            print(f"Model {model_name} loaded successfully!")
        except Exception as e:
            print(f"CRITICAL ERROR loading model: {e}")
            self.model = None

        # Initialize LLM
        if OPENAI_AVAILABLE:
            try:
                self.llm = OpenAILLM()
                print("OpenAI LLM initialized (gpt-4o-mini). RAG Search enabled.")
            except Exception as e:
                print(f"Failed to init OpenAI LLM: {e}")
                self.llm = None
        else:
            self.llm = None

    def search_sargas(self, query: str, limit: int = 3) -> List[Dict]:
        """Search for whole chapters/sargas by theme"""
        # Check if collection exists
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            if self.sarga_collection_name not in collection_names:
                print(f"WARNING: Collection '{self.sarga_collection_name}' does not exist!")
                print(f"Available collections: {collection_names}")
                print("You need to run ingestion first. See deployment_guide.md")
                return []  # Return empty results instead of crashing
        except Exception as e:
            print(f"Error checking collections: {e}")
            # Continue anyway, let Qdrant handle the error
        
        # Encode query - this is where the meta tensor error occurs
        try:
            query_vector = self.model.encode(query).tolist()
        except Exception as e:
            print(f"ERROR encoding query: {e}")
            raise
        
        # Query Qdrant
        try:
            results = self.client.query_points(
                collection_name=self.sarga_collection_name,
                query=query_vector,
                limit=limit
            ).points
        except Exception as e:
            print(f"ERROR querying Qdrant: {e}")
            print(f"Collection '{self.sarga_collection_name}' may not exist or be empty.")
            print("You need to run ingestion. See deployment_guide.md")
            return []  # Return empty instead of crashing
        
        return [{
            'score': r.score,
            'kanda': r.payload['kanda'],
            'sarga': r.payload['sarga'],
            'full_text': r.payload.get('full_text', ''),
            'verse_count': r.payload['verse_count']
        } for r in results]

    def search(self, query: str, limit: int = 5, kanda_filter: str = None) -> List[Dict]:
        """Standard Semantic Search"""
        query_vector = self.model.encode(query).tolist()
        
        search_filter = None
        if kanda_filter:
            search_filter = {"must": [{"key": "kanda", "match": {"value": kanda_filter}}]}
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=search_filter
        ).points
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                'score': result.score,
                'verse_id': result.payload['verse_id'],
                'kanda': result.payload['kanda'],
                'sarga': result.payload['sarga'],
                'shloka': result.payload['shloka'],
                'shloka_text': result.payload['shloka_text'],
                'translation': result.payload['translation'],
                'explanation': result.payload['explanation']
            })
        
        return formatted_results

    def rag_search(self, query: str, final_limit: int = 10) -> List[Dict]:
        """Deep Analysis Search using RAG (Retrieve -> Filter -> Rank)"""
        if not self.llm:
            print("RAG not available. Falling back to standard search.", flush=True)
            return self.search(query, limit=final_limit)
            
        print(f"DEBUG: 🧠 RAG Deep Search for: '{query}'", flush=True)
        print(f"1. retrieving candidates...", flush=True)
        # Reduced from 50 to 20 for speed/cost as per user request
        raw_results = self.search(query, limit=20)
        
        print(f"2. analyzing {len(raw_results)} verses with OpenAI (gpt-4o-mini) Batch...", flush=True)
        verse_contents = [f"{res['translation']} {res['explanation']}" for res in raw_results]
        
        final_results = []
        BATCH_SIZE = 15 # Increased batch size slightly for speed
        
        import math
        total_batches = math.ceil(len(raw_results) / BATCH_SIZE)
        
        for i in range(0, len(raw_results), BATCH_SIZE):
            batch_content = verse_contents[i : i + BATCH_SIZE]
            batch_indices = range(i, i + len(batch_content))
            
            print(f"   - Processing batch {i//BATCH_SIZE + 1}/{total_batches}...")
            batch_analysis = self.llm.analyze_verses_batch(batch_content, query)
            
            for j, analysis in enumerate(batch_analysis):
                # Map analysis items back via relative index
                if j >= len(batch_indices): break # Safety
                
                real_idx = batch_indices[j]
                res = raw_results[real_idx]
                
                # Check strict keep
                if analysis.get('keep'):
                    res['rag_analysis'] = analysis
                    final_results.append(res)
        
        print(f"3. filtered out {len(raw_results) - len(final_results)} low-relevance verses. Kept {len(final_results)}.")
        return final_results[:final_limit]
    
    def print_results(self, results: List[Dict], rag_mode: bool = False):
        """Pretty print search results"""
        if not results:
            print("No results found.")
            return
        
        print(f"\nFound {len(results)} results:\n")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            score = f"Score: {result['score']:.3f}"
            print(f"\n{i}. {result['verse_id']} ({score})")
            
            # RAG Insights
            if rag_mode and 'rag_analysis' in result:
                analysis = result['rag_analysis']
                category = analysis.get('category', 'Unknown')
                reason = analysis.get('reason', 'N/A')
                modern = analysis.get('modern_take', '')
                
                print(f"   category: [{category}]")
                if modern:
                    print(f"   💡 MODERN TAKE: {modern}")
                print(f"   Reason: {reason}")
                print(f"   {'-'*40}")

            print(f"   Location: {result['kanda']}, Sarga {result['sarga']}, Verse {result['shloka']}")
            print(f"   Explanation: {result['explanation']}")
            print("="*80)
    
    def save_results(self, results: List[Dict], query: str, filename: str = "ramayana_research_log.md"):
        """Save results to a markdown file"""
        if not results: return
        
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"\n# Query: {query}\n")
            f.write(f"_Saved on {os.path.basename(filename)}_\n\n")
            
            for i, result in enumerate(results, 1):
                analysis = result.get('rag_analysis', {})
                category = analysis.get('category', 'Standard Search')
                modern = analysis.get('modern_take', '')
                reason = analysis.get('reason', '')
                
                f.write(f"### {i}. {result['verse_id']} (Score: {result['score']:.3f})\n")
                if modern:
                    f.write(f"> **💡 Modern Take:** {modern}\n\n")
                if reason:
                    f.write(f"**Why Relevant:** {reason}\n\n")
                
                f.write(f"- **Category:** {category}\n")
                f.write(f"- **Location:** {result['kanda']}, Sarga {result['sarga']}, Verse {result['shloka']}\n")
                f.write(f"- **Explanation:** {result['explanation']}\n")
                f.write("\n---\n")
        
        print(f"\n[Saved results to {filename}]")

    def close(self):
        if hasattr(self, 'client'):
            self.client.close()

def main():
    """Interactive search interface"""
    print("="*80)
    print("Valmiki Ramayana - Semantic Search & RAG Interface")
    print("="*80)
    
    searcher = RamayanaSearcher()
    
    print("\nExample Queries:")
    print("  - 'leadership in crisis'")
    print("  - 'handling grief'")
    print("  - 'diplomacy strategies'")
    
    while True:
        print("\n")
        query = input("Enter search query (or 'q' to exit): ").strip()
        
        if query.lower() in ['q', 'quit', 'exit']:
            searcher.close()
            print("Goodbye!")
            break
        
        if not query: continue
        
        # Mode Selection
        use_rag = True 
        mode = input("Use Deep Analysis (RAG)? [Y/n]: ").strip().lower()
        if mode == 'n': use_rag = False
        
        print("\nSearching...")
        if use_rag:
            results = searcher.rag_search(query, final_limit=10)
            searcher.print_results(results, rag_mode=True)
        else:
            results = searcher.search(query, limit=5)
            searcher.print_results(results, rag_mode=False)
            
        # Auto-save
        searcher.save_results(results, query)

if __name__ == "__main__":
    main()
