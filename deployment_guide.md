# 🚀 Deployment Guide: Railway

This guide explains how to deploy the **Ramayana Digital Rishi** to Railway.

## 🏗️ Architecture Overview
- **Backend**: FastAPI (Python)
- **Frontend**: Vite (React)
- **Vector DB**: Qdrant (Docker/Railway Service)
- **Relational DB**: SQLite (Local file, requires Railway Volume)

---

## 1️⃣ Step 1: Deploy Qdrant
The easiest way is to use Railway's built-in Qdrant template.
1. Click **New** -> **Templates** -> Search for **Qdrant**.
2. Deploy it.
3. Once deployed, note the **TCP URL** (e.g., `qdrant.railway.internal:6333`).

## 2️⃣ Step 2: Deploy the Backend
1. Click **New** -> **GitHub Repo** -> Select your repo.
2. In **Settings**:
   - **Root Directory**: Leave blank (root).
   - **Build Command**: `pip install -r requirements.txt` (Nixpacks handles this).
   - **Start Command**: `uvicorn agent_api.server:app --host 0.0.0.0 --port $PORT` (Defined in `Procfile`).
3. Add **Environment Variables**:
   - `OPENAI_API_KEY`: Your key.
   - `QDRANT_MODE`: `server`
   - `QDRANT_HOST`: (The internal Qdrant host from Step 1).
   - `QDRANT_PORT`: `6333`
   - `PORT`: Railway provides this automatically.

## 3️⃣ Step 3: Deploy the Frontend
1. Click **New** -> **GitHub Repo** -> Select your repo (yes, again).
2. In **Settings**:
   - **Service Name**: `frontend`
   - **Root Directory**: `ramayana-ui`
3. Add **Environment Variables**:
   - `VITE_API_URL`: The public URL of your **Backend Service** (e.g., `https://your-backend.railway.app`).
4. Railway will automatically build the static site.

---

## 💾 Important: Persistence (SQLite)
If you want to keep your chat history across restarts:
1. Go to your **Backend Service** on Railway.
2. Go to **Settings** -> **Volumes**.
3. Create a Volume and mount it to `/app`.
4. Ensure your `DATABASE_URL` in `database.py` points to a path within that volume.

## 📥 Ingesting Data on Railway
After deploying Qdrant and the Backend:
1. Open the Railway CLI or the **Web Terminal** for the Backend service.
2. Run: 
   ```bash
   python ingest_ramayana.py
   python ingest_sargas.py
   python agent_api/ingest.py
   ```
   *This will populate your production Qdrant and SQLite instances.*
