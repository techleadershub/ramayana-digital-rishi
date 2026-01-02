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
   - **Build Command**: (Leave empty - Dockerfile handles this)
   - **Start Command**: (Leave empty - Dockerfile handles this)
3. Add **Environment Variables**:
   - `VITE_API_URL`: The public URL of your **Backend Service** (e.g., `https://your-backend.railway.app`)
   - **Important**: This must be set BEFORE the first build, as Vite bakes it into the build
4. Railway will automatically detect the `Dockerfile` and `railway.json` in the `ramayana-ui` directory and build accordingly.

### ⚠️ Troubleshooting Frontend Issues

If the frontend shows a blank page after deployment:

1. **Check Environment Variables**: Ensure `VITE_API_URL` is set correctly (no trailing slash)
   - Example: `https://your-backend.railway.app` (NOT `https://your-backend.railway.app/`)

2. **Verify Build Logs**: Check Railway build logs to ensure:
   - Dockerfile is being used (not Nixpacks)
   - Build completes successfully
   - `VITE_API_URL` is available during build

3. **Check Browser Console**: Open browser DevTools and check for:
   - 404 errors for assets (CSS/JS files)
   - CORS errors when calling the backend
   - Network errors

4. **Rebuild After Setting Variables**: If you set `VITE_API_URL` after the first build, you must trigger a new deployment:
   - Go to **Deployments** tab
   - Click **Redeploy** or push a new commit

5. **Verify Service Worker**: The app uses a service worker. If issues persist:
   - Clear browser cache
   - Unregister service worker in DevTools > Application > Service Workers

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
