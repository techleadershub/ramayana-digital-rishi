import sys
import os
from typing import List, Dict

# Add parent directory to path to import query_ramayana
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.tools import tool
from sqlalchemy.orm import Session
from database import SessionLocal, Verse
from query_ramayana import RamayanaSearcher

# Initialize Searcher (Lazy load to avoid overhead if not used)
_searcher = None

def get_searcher():
    global _searcher
    if _searcher is None:
        print("Initializing RamayanaSearcher for Agent...", flush=True)
        # Reduce k for agent speed? Or keep high for quality? 
        # Agent might want high quality.
        _searcher = RamayanaSearcher()
    return _searcher

@tool
def search_chapters(query: str) -> str:
    """
    Useful for getting a 'Macro View' or 'Summary' of whole chapters (Sargas) related to a topic.
    Use this to understand the broad context before looking for specific verses.
    Returns thematic summaries of relevant Sargas.
    """
    searcher = get_searcher()
    print(f"DEBUG: 📚 CHAPTER SEARCH: '{query}'", flush=True)
    results = searcher.search_sargas(query, limit=2)
    print(f"DEBUG: Found {len(results)} relevant chapters.", flush=True)
    
    formatted = []
    for r in results:
        # Full text can be large, we'll take top 10000 chars to be safe but typically sargas fit
        text = r.get('full_text', 'No text found.')
        if len(text) > 15000:
            text = text[:15000] + "\n... [Truncated for Context Window] ..."
            
        formatted.append(
            f"SOURCE: CHAPTER SUMMARY\n"
            f"Chapter: {r['kanda']} Sarga {r['sarga']}\n"
            f"Full Chapter Context:\n{text}\n"
            f"Total Verses: {r['verse_count']}\n"
        )
    return "\n---\n".join(formatted)

@tool
def search_principles(query: str) -> str:
    """
    Useful for finding wisdom, ethics, morals, or abstract concepts in the Ramayana.
    Use this for queries like 'leadership', 'stress management', 'dharma', 'relationships'.
    Returns a list of verses with 'Modern Take' and 'Explanation'.
    """
    searcher = get_searcher()
    print(f"DEBUG: 🔍 PRINCIPLE SEARCH: '{query}'", flush=True)
    # Use RAG search with lower k for speed? Or default?
    # Default is 150 candidates, 10 final. Good for depth.
    results = searcher.rag_search(query, final_limit=5) 
    
    # Format output for the Agent
    formatted = []
    for r in results:
        formatted.append(
            f"SOURCE: SPECIFIC VERSE\n"
            f"Verse: {r['verse_id']}\n"
            f"Location: {r.get('kanda', '')} {r.get('sarga', '')}:{r.get('shloka', '')}\n"
            f"Sanskrit: {r.get('shloka_text', 'N/A')}\n"
            f"Translation: {r.get('translation', 'N/A')}\n"
            f"Explanation: {r['explanation']}\n"
            f"Modern Take: {r.get('modern_take', 'N/A')}\n"
            f"Relevance: {r.get('relevance_reason', 'N/A')}\n"
        )
    return "\n---\n".join(formatted)

@tool
def search_narrative(query: str, speaker: str = None) -> str:
    """
    Useful for finding specific story events, dialogues, or plot points.
    Use this when looking for 'What happened when...', 'Verses where Rama spoke to...', 'Story of...'.
    Args:
        query: Keywords to search in the English translation/explanation (e.g. 'golden deer', 'sleeping giant').
        speaker: Optional. Filter by speaker (e.g. 'Rama', 'Sita').
    """
    session = SessionLocal()
    print(f"DEBUG: 📜 Agent Researching Narrative for: '{query}' (Speaker: {speaker})")
    try:
        # Simple LIKE query for now (FTS later)
        # Search in explanation OR translation
        q = session.query(Verse).filter(
            (Verse.explanation.ilike(f"%{query}%")) | 
            (Verse.translation.ilike(f"%{query}%"))
        )
        
        if speaker:
            q = q.filter(Verse.speaker.ilike(f"%{speaker}%"))
            
        results = q.limit(10).all()
        
        if not results:
            return "No narrative verses found."
            
        formatted = []
        for r in results:
            formatted.append(
                f"SOURCE: SPECIFIC VERSE\n"
                f"Location: {r.kanda} {r.sarga}:{r.verse_number}\n"
                f"Speaker: {r.speaker}\n"
                f"Text: {r.explanation}\n"
            )
        return "\n---\n".join(formatted)
    finally:
        session.close()

@tool
def get_verse_context(kanda: str, sarga: int, verse_number: int, window: int = 5) -> str:
    """
    Retrieves the surrounding verses (context) for a specific verse.
    Use this to understand the flow of conversation before/after a found verse.
    """
    session = SessionLocal()
    try:
        # Fetch range
        start = max(1, verse_number - window)
        end = verse_number + window
        
        verses = session.query(Verse).filter(
            Verse.kanda == kanda,
            Verse.sarga == sarga,
            Verse.verse_number >= start,
            Verse.verse_number <= end
        ).order_by(Verse.verse_number).all()
        
        formatted = []
        for r in verses:
            marker = ">>> " if r.verse_number == verse_number else "    "
            formatted.append(
                f"{marker}[{r.verse_number}] {r.speaker or 'Narrator'}: {r.explanation}"
            )
        return "\n".join(formatted)
    finally:
        session.close()

def get_verse_details(kanda: str, sarga: int, shloka: int):
    """
    Helper to fetch full verse details for API.
    """
    session = SessionLocal()
    try:
        # Normalize kanda name: strip trailing colons, dots, and whitespace
        clean_kanda = kanda.strip().replace(":", "").replace(".", "")
        
        verse = session.query(Verse).filter(
            Verse.kanda.ilike(f"%{clean_kanda}%"), 
            Verse.sarga == sarga,
            Verse.verse_number == shloka
        ).first()
        
        if not verse:
            return None
            
        return {
            "id": verse.id,
            "kanda": verse.kanda,
            "sarga": verse.sarga,
            "shloka": verse.verse_number,
            "sanskrit": verse.text, # Assuming 'text' is sanskrit
            "translation": verse.translation,
            "explanation": verse.explanation,
            "speaker": verse.speaker
        }
    except Exception as e:
        print(f"Error fetching verse: {e}")
        return None
    finally:
        session.close()

