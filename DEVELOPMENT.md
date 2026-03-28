# Development Guide

Complete guide for developing and debugging GemmaWatch.

## 🚀 Quick Start

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd backend && source venv/bin/activate && python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# Terminal 3: Frontend
cd frontend && npm run dev

# Terminal 4: Verification (after services start)
curl http://localhost:8002/health
open http://localhost:5173
```

## 📁 Project Structure

```
GemmaWatch/
├── README.md                  # Main documentation
├── CONTRIBUTING.md            # Contribution guidelines
├── CODE_OF_CONDUCT.md        # Community standards
├── DEVELOPMENT.md            # This file
├── LICENSE                   # MIT License
├── .gitignore               # Git ignore patterns
├── .editorconfig            # Code style settings
├── FEATURE_INVENTORY.md     # Feature status
│
├── backend/
│   ├── main.py              # FastAPI app + WebSocket
│   ├── requirements.txt      # Python dependencies
│   ├── .env                 # Secrets (DON'T COMMIT)
│   ├── .env.example         # Template for .env
│   ├── .pytest.ini          # Pytest config
│   ├── gemmawatch.db        # SQLite database (auto-created)
│   ├── services/
│   │   ├── scraper.py       # Playwright browser automation
│   │   ├── ai_service.py    # Gemma RCA integration
│   │   ├── sqlite_service.py # Database persistence
│   │   └── neo4j_service.py # Unused graph DB
│   ├── screenshots/         # Generated screenshots
│   └── tests/              # Unit tests
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── Dashboard.tsx      # Main monitoring UI
│   │   │   ├── SiteDetails.tsx    # RCA display
│   │   │   └── ...
│   │   ├── App.tsx          # Root component
│   │   ├── main.tsx         # Entry point
│   │   └── index.css        # Global styles
│   ├── public/              # Static assets
│   ├── cypress/             # E2E tests
│   ├── package.json         # Node dependencies
│   ├── vite.config.ts       # Build configuration
│   ├── tsconfig.json        # TypeScript config
│   └── tailwind.config.js   # Tailwind CSS config
│
└── screenshots/             # Generated screenshot baselines
```

## 🔧 Environment Setup

### Backend Environment Variables

Create `backend/.env` (copy from `.env.example`):

```env
OLLAMA_URL=http://localhost:11434/api/generate
MODEL_NAME=gemma:latest
DEBUG=false
LOG_LEVEL=INFO
```

### Frontend Environment

Frontend uses Vite, default config loads from `.env*` files:
- `.env` - Loaded in all modes
- `.env.local` - Git-ignored, local overrides
- `.env.production` - Production-only variables

## 🏃 Running Services

### Background Execution (Recommended for Development)

**Start all services at once:**

```bash
# From root directory
./scripts/start-all.sh  # (if available, or use these commands)

# Terminal 1
ollama serve

# Terminal 2
cd backend && source venv/bin/activate && python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# Terminal 3
cd frontend && npm run dev
```

### Service Status

```bash
# Check services running
lsof -i :11434  # Ollama
lsof -i :8002   # Backend
lsof -i :5173   # Frontend

# List all running services
ps aux | grep -E "ollama|uvicorn|node"
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_scraper.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=services tests/

# Run specific test function
pytest tests/test_scraper.py::test_screenshot_capture
```

### Frontend Tests

```bash
cd frontend

# Run Vitest (unit/integration tests)
npm run test

# Watch mode
npm run test:watch

# UI mode
npm run test:ui

# Run E2E tests (Cypress)
npx cypress open

# Run E2E headless
npx cypress run

# Type checking
npx tsc --noEmit
```

## 🐛 Debugging

### Backend Debugging

**Enable debug logging:**

```bash
# In backend/.env
DEBUG=true
LOG_LEVEL=DEBUG
```

**Add breakpoints in VS Code:**
1. Set breakpoint in `.py` file
2. Run with debugger:
```bash
python -m debugpy --listen 5678 -m uvicorn main:app --reload
```

**Check service logs:**
```bash
# See recent backend logs
tail -f backend.log

# Real-time log streaming (if running in background)
ps aux | grep uvicorn
```

### Frontend Debugging

**Browser DevTools:**
1. Open http://localhost:5173
2. Press F12 (or Cmd+Option+I on macOS)
3. Inspect Components tab (React DevTools)
4. Check Network tab for API calls
5. Check Console for errors

**VS Code Debugging:**
1. Install "Debugger for Chrome" extension
2. Add launch config (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "chrome",
      "request": "attach",
      "name": "Attach to Chrome",
      "port": 9222
    }
  ]
}
```

**WebSocket Debugging:**
- Use Network tab in DevTools
- Filter for "WS" (WebSocket)
- Click to see messages in real-time

### Database Debugging

**Inspect SQLite database:**

```bash
# Open SQLite CLI
cd backend
sqlite3 gemmawatch.db

# View tables
.tables

# Schema of specific table
.schema checks

# Query data
SELECT * FROM sites;
SELECT COUNT(*) FROM checks;

# Exit
.quit
```

## 🔄 Hot Reload

Both backend and frontend support hot reload:

- **Backend**: Changes to `.py` files auto-reload (uvicorn `--reload`)
- **Frontend**: Changes to `.tsx`/`.css` files auto-refresh (Vite HMR)

## 📊 API Testing

### Using cURL

```bash
# Check health
curl http://localhost:8002/health

# Get all sites
curl http://localhost:8002/sites

# Get site history
curl http://localhost:8002/sites/{site_id}/history?limit=10

# Check Ollama
curl http://localhost:11434/api/tags

# Test Gemma
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"gemma:latest","prompt":"hello","stream":false}'
```

### Using Postman/Insomnia

1. Import collection (if available in `/postman/`)
2. Configure environment: `http://localhost:8002`
3. Test endpoints

## 🚀 Performance Profiling

### Backend Profiling

```bash
# Install profiler
pip install py-spy

# Profile uvicorn process
py-spy record -o profile.svg -- python -m uvicorn main:app

# View output
open profile.svg
```

### Frontend Profiling

1. Open DevTools (F12)
2. Performance tab
3. Record user actions
4. Analyze flame chart

## 📝 Code Quality

### Format Code

**Python (Black):**
```bash
cd backend
pip install black
black .
```

**TypeScript/JavaScript (Prettier):**
```bash
cd frontend
npm install --save-dev prettier
npx prettier --write .
```

**Python Linting:**
```bash
cd backend
pip install flake8
flake8 .
```

**TypeScript Linting:**
```bash
cd frontend
npm run lint
```

## 🔐 Security

### Secrets Management

**Never commit secrets:**
```bash
# ✅ Good - Add to .gitignore
.env
.env.local

# ❌ Bad - Don't hardcode in code
api_key = "sk-1234..."
secret = "password"
```

### Dependency Auditing

**Python:**
```bash
pip audit
```

**JavaScript:**
```bash
npm audit
```

## 🚢 Deployment Preview

### Build for Production

**Backend:**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8002
```

**Frontend:**
```bash
cd frontend
npm run build
npm run preview
```

## 📚 Useful Commands Cheatsheet

| Command | Purpose |
|---------|---------|
| `source venv/bin/activate` | Activate Python venv |
| `pip install -r requirements.txt` | Install backend deps |
| `npm install` | Install frontend deps |
| `pytest` | Run backend tests |
| `npm run test` | Run frontend tests |
| `npx tsc --noEmit` | Check TypeScript errors |
| `sqlite3 gemmawatch.db` | Access database |
| `curl http://localhost:8002/health` | Health check |
| `rm gemmawatch.db` | Reset database |

## 🆘 Common Issues

### "Ollama not connected"
```bash
# Make sure ollama serve is running
ollama serve
```

### "Port 8002 already in use"
```bash
# Find and kill process
lsof -i :8002
kill -9 <PID>
```

### "Module not found"
```bash
# Python
source venv/bin/activate
pip install -r requirements.txt

# Node
npm install
```

### "Database locked"
```bash
# Another process has database
ps aux | grep python
kill -9 <PID>
rm backend/gemmawatch.db  # Reset if needed
```

## 📖 Further Resources

- [README.md](README.md) - Main documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guide
- [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) - Feature status
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [Ollama Docs](https://ollama.ai/docs)

---

**Happy coding! 🚀**
