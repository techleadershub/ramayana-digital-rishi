# Ramayana Digital Rishi 🕉️

**The Ramayana Digital Rishi is a deep research agent that bridges ancient wisdom and modern living using Agentic AI and Vector RAG.**

Built on the Valmiki Ramayana (20,000+ verses), this system uses a "Hierarchical Research" approach—combining macro-level chapter summaries with micro-level shloka analysis—to provide authoritative guidance on leadership, ethics, mental health, and decision-making.

---

## 🚀 Key Features
- **The Digital Rishi Agent**: A multi-step research agent that plans and executes complex queries.
- **Hierarchical RAG**: Searches both whole chapter (Sarga) summaries and individual verses.
- **Relational Context**: Uses SQLite to provide surrounding verses for every cited shloka.
- **Modern Wisdom**: Bridges the gap between 2nd-century BCE ethics and 21st-century corporate/personal life.
- **Web Interface**: A premium React-based UI with "Thinking" visualization and interactive citations.

---

## 🛠️ Technology Stack
- **Backend**: FastAPI (Python), LangGraph (Agentic Framework), SQLAlchemy.
- **Frontend**: React (Vite), Framer Motion, Tailwind CSS.
- **Vector DB**: Qdrant (Docker).
- **Relational DB**: SQLite (Localized Narrative & Context).
- **AI Models**: OpenAI GPT-4o-mini, Sentence-Transformers (all-MiniLM-L6-v2).

---

## 🏗️ Quick Start (Local)

### 1. Start Qdrant
```bash
docker-compose up -d
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
cd ramayana-ui && npm install
```

### 3. Populating the Knowledge Base
Run the ingestion scripts to populate Qdrant and SQLite:
```bash
python ingest_ramayana.py
python ingest_sargas.py
python agent_api/ingest.py
```

### 4. Run the Application
**Backend:** `python agent_api/server.py`
**Frontend:** `cd ramayana-ui && npm run dev`

---

## ☁️ Deployment (Railway)
See the [**Deployment Guide**](./deployment_guide.md) for step-by-step instructions on deploying to Railway.

### 📥 One-Click Production Ingestion
Once deployed, trigger the full population of your production DBs with a single request:
```bash
curl -X POST https://your-backend-url.railway.app/admin/ingest
```

---

## 📜 Legal & Spiritual Disclaimer
**This is an AI-powered research tool, not a substitute for traditional spiritual guidance or professional advice.**
- **AI Hallucinations**: While the agent is programmed for "Scriptural Fidelity," AI can sometimes misinterpret context or generate incorrect citations. Always cross-reference with a physical copy of the Valmiki Ramayana.
- **Respectful Research**: This tool is designed for educational and thematic research. Please use it with the reverence appropriate for a sacred text.

## 📚 Data Sources
The primary source for this project is the **Valmiki Ramayana**. 
- Sanskrit verses and English translations are derived from the [Valmiki_Ramayan_Dataset](https://github.com/Ashutosh-Vijay/Valmiki_Ramayan_Dataset) by Ashutosh Vijay.
- If you are a copyright holder of any specific commentary included and wish for its removal, please open an issue.

---

**Built with reverence for the timeless verses of Valmiki.** 🙏
