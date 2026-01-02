import json
import os
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, Verse

def extract_speaker(text):
    if not text:
        return None
    if "Rama said" in text:
        return "Rama"
    if "Sita said" in text:
        return "Sita"
    if "Ravana said" in text:
        return "Ravana"
    return None

def ingest_data():
    print(f"Initializing Database...")
    from database import DATABASE_URL
    print(f"Using Database At: {DATABASE_URL}")
    init_db()
    
    json_path = "Valmiki_Ramayan_Shlokas.json"
    if not os.path.exists(json_path):
        json_path = "agent_api/Valmiki_Ramayan_Shlokas.json"
    if not os.path.exists(json_path):
        json_path = "../Valmiki_Ramayan_Shlokas.json"
        
    if not os.path.exists(json_path):
        print(f"Error: Valmiki_Ramayan_Shlokas.json not found.")
        return

    print(f"Loading JSON from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Found {len(data)} verses. Starting ingestion...")
    
    session = SessionLocal()
    
    # Optional: Clear existing data
    session.query(Verse).delete()
    
    batch = []
    count = 0
    for item in data:
        # Extract fields safely
        verse = Verse(
            source_id="ramayana",
            kanda=item.get("kanda"),
            sarga=item.get("sarga"),
            verse_number=item.get("shloka"),
            text=item.get("shloka_text"),
            translation=item.get("translation"), 
            explanation=item.get("explanation"),     
            speaker=extract_speaker(item.get("explanation"))
        )
        batch.append(verse)
        
        if len(batch) >= 1000:
            session.add_all(batch)
            session.commit()
            batch = []
            print(f"Ingested {count} verses...")
        
        count += 1

    if batch:
        session.add_all(batch)
        session.commit()

    print(f"Successfully ingested {count} verses into SQLite.")

if __name__ == "__main__":
    ingest_data()
