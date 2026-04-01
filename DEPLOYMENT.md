# GemmaWatch Deployment Guide v2.0

Comprehensive guide for deploying the High-Precision GemmaWatch platform to production.

## 🚀 Overview

- **Frontend**: Deployed to Vercel (Auto-scaling, Edge-optimized).
- **Backend**: Deployed to Railway using Docker (Handles `sqlite-vec` extension).
- **AI Intelligence**: Optimized for local `Ollama` or hosted LLM providers.

---

## 📦 Deployment Prerequisites

### sqlite-vec Extension (CRITICAL)
GemmaWatch 2.0 relies on `sqlite-vec` for its high-precision RAG.
- **Docker**: The provided `Dockerfile` must install `build-essential` and `tcl` to compile/load the extension if not using a pre-compiled binary.
- **Railway**: Ensure the environment supports custom C-extensions for SQLite.

---

## 🔑 Railway Environment Variables

In the Railway dashboard → Project → Variables, configure the following:

```env
# AI & Database
OLLAMA_URL=https://your-hosted-ollama-api  # Or local tunnel
MODEL_NAME=gemma:latest
EMBED_MODEL=nomic-embed-text

# Authentication (Mandatory for Production)
AUTH_SECRET=your-32-character-secure-string
GOOGLE_CLIENT_ID=your-google-id
GOOGLE_CLIENT_SECRET=your-google-secret
GITHUB_CLIENT_ID=your-github-id
GITHUB_CLIENT_SECRET=your-github-secret

# Frontend Configuration
FRONTEND_BASE_URL=https://your-gemmawatch.vercel.app
```

---

## 🤖 Production AI Considerations

### Analyst Persona Grounding
In production, ensure the `OLLAMA_URL` points to a stable endpoint. If the AI is unavailable:
- **Monitoring**: Continues to function (HTTP/TCP/DNS).
- **RCA**: Fails gracefully with a "Service Degraded" status.
- **Chat**: Switches to a "Platform Info" system persona.

### Intelligence Catalogue (HITL)
The `/catalogue/pending` endpoint is restricted to **Admin** users. Ensure you have configured yourself as an admin in the `users` table after your first login.

---

## 🛠️ Deployment Checklist

- [x] Configure OAuth Providers (Google/GitHub).
- [x] Generate a secure `AUTH_SECRET`.
- [x] Verify `sqlite-vec` loads correctly in the target environment.
- [x] Deploy Backend to Railway (Docker).
- [x] Deploy Frontend to Vercel (pointing to Railway URL).
- [x] Run a test check and verify **Analyst Response**.

## Frontend Deployment (Vercel)

**Already Deployed**: Frontend is live at https://gemmawatch.vercel.app

### Steps Taken
1. Configured environment variables for API URLs
2. Pushed code to GitHub
3. Connected Vercel to repo (auto-deploys on push)

### Current Status
```
Frontend: https://gemmawatch.vercel.app
```

---

## Backend Deployment (Railway)

### Prerequisites
- Railway.app account (free sign-up: https://railway.app)
- GitHub account (already have)
- Docker installed locally (only for testing, Railway builds it)

### Step 1: Create Railway Account
```bash
# Go to https://railway.app
# Sign up with GitHub (recommended)
# Authorize railway.app to access your repos
```

### Step 2: Connect GemmaWatch Repo to Railway
1. Log into Railway dashboard
2. Click "Create New Project"
3. Select "Deploy from GitHub repo"
4. Search for `GemmaWatch` repo
5. Click "Deploy"

Railway automatically detects:
- `Dockerfile` in root (uses it to build container)
- Environment variables settings

### Step 3: Configure Environment Variables
In Railway dashboard → Project → Variables:

```
OLLAMA_URL=http://localhost:11434
MODEL_NAME=gemma:latest
DEBUG=false
LOG_LEVEL=info
```

**Note about OLLAMA_URL:**
- If Ollama not available: backend will skip RCA, still monitor sites
- To enable Ollama: expose local Ollama via ngrok tunnel (advanced)
- Or replace with external API endpoint if using hosted Ollama

### Step 4: Wait for Deployment
Railway builds Docker image and deploys:
- Pull dependencies (requirements.txt)
- Build Docker container
- Deploy to Railway servers
- Assign public domain name

**Expected output in Railway logs:**
```
[INFO] Building image...
[INFO] Installing dependencies...
[INFO] Starting application...
Application running on http://0.0.0.0:PORT
```

### Step 5: Get the Backend URL
In Railway dashboard:
1. Click "Deployments"
2. Find "Production" deployment
3. Copy the public URL (looks like: `https://gemmawatch-backend.railway.app`)

### Step 6: Update Frontend Environment Variable
Update the frontend to point to deployed backend:

**Option A: Update in Vercel Dashboard**
1. Go to https://vercel.com → GemmaWatch project
2. Settings → Environment Variables
3. Update `VITE_API_BASE`:
   ```
   VITE_API_BASE=https://gemmawatch-backend.railway.app
   VITE_WS_BASE=wss://gemmawatch-backend.railway.app
   ```
4. Click "Save" (triggers redeploy)

**Option B: Update in Code & Push**
1. Edit `frontend/.env.example`:
   ```
   VITE_API_BASE=https://gemmawatch-backend.railway.app
   VITE_WS_BASE=wss://gemmawatch-backend.railway.app
   ```
2. In your local code, update Dashboard.tsx if hardcoded
3. Run: `git add . && git commit -m "Update backend URL" && git push origin main`
4. Vercel auto-redeploys

### Step 7: Verify Deployment
```bash
# Test backend health
curl https://gemmawatch-backend.railway.app/health

# Expected response:
# {"status":"healthy","gemma_available":false}
# (gemma_available=false is OK if Ollama not configured)
```

### Step 8: Test Full Integration
1. Open https://gemmawatch.vercel.app in browser
2. Add a site (e.g., https://google.com)
3. Run a check
4. Verify results appear in real-time

---

## Important Notes on Ollama

**Current Setup**: Ollama runs on your local machine
- Monitoring/screenshots work without Ollama
- RCA analysis is optional (skipped if Ollama unavailable)
- Backend can't reach local Ollama from Railway servers

**If you need RCA on deployed app:**

**Option 1: Keep Ollama Local (Dev-only)**
```bash
# On your local machine, keep running:
ollama serve
# This only works when you're offline testing
```

**Option 2: Use External Ollama API** (Production-Ready)
```bash
# Set OLLAMA_URL to hosted endpoint
# Examples: Replicate.com, HuggingFace Inference, etc.
OLLAMA_URL=https://api.replicate.com/v1/predictions
```

**Option 3: Deploy Ollama to Cloud** (Advanced)
```bash
# Expensive but works:
# - AWS EC2 t2.small (~$33/month)
# - DigitalOcean Droplet ($5/month minimum)
# - Include Docker image in Railway
```

For now, **Option 1 (dev-only)** is recommended. The monitoring still works great without RCA!

---

## Troubleshooting Deployment

**"Backend deployment failed"**
```
Check Railway build logs:
1. Go to Railway dashboard
2. Click "Logs" tab
3. Look for build errors
Common issues:
- requirements.txt has unsupported package
- PORT environment variable not set
Solution: Check Docker layer-by-layer
```

**"Frontend can't reach backend"**
```
1. Verify backend URL is correct:
   curl https://gemmawatch-backend.railway.app/health

2. Check CORS is enabled in FastAPI (it is by default)

3. Verify env variables in Vercel:
   Dashboard → Settings → Environment Variables
   VITE_API_BASE should point to Railway URL
   Trigger redeploy after changing

4. Check browser console (F12) for exact errors
```

**"WebSocket connection fails"**
```
1. WebSocket URL must use "wss://" (secure) for https sites
2. Verify: VITE_WS_BASE=wss://your-backend-url (not http://)
3. Check that + is configured in both env vars and code
```

**"Slow/no response from deployed backend"**
```
Railway free tier has sleep mode:
- Projects sleep after 7 days inactivity
- First request wakes them up (~10 second wait)
Solution:
- Keep making checks regularly
- Or upgrade Railway plan ($7+/month for always-on)
```

---

## Deployment Summary Checklist

- [ ] Create Railway account at railway.app
- [ ] Connect GitHub repo to Railway
- [ ] Deploy to Railway (auto from Dockerfile)
- [ ] Note the Railway backend URL
- [ ] Update Vercel env variables with new backend URL
- [ ] Wait for Vercel redeploy
- [ ] Test: `curl https://backend-url/health`
- [ ] Open https://gemmawatch.vercel.app
- [ ] Add a site and run a check
- [ ] Verify real-time updates work
