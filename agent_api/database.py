from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./ramayana_agent.db"

Base = declarative_base()

class Verse(Base):
    __tablename__ = "verses"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, index=True) # "ramayana", "gita"
    kanda = Column(String, index=True)
    sarga = Column(Integer, index=True)
    verse_number = Column(Integer)
    text = Column(Text) # Sanskrit/Original
    translation = Column(Text) # English
    explanation = Column(Text) # Purport/Meaning
    speaker = Column(String, nullable=True) # e.g. "Rama"
    
    # We will use SQLite's native FTS5, but for simplicity in SQLAlchemy 
    # we just define the model here. We'll create the FTS index manually 
    # or rely on simple LIKE queries for now if FTS is complex to set up via ORM.
    # Actually, let's stick to standard SQL matching first, or strictly use FTS if needed.
    # For now, standard text columns.

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
