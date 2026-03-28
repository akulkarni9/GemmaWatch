# Contributing to GemmaWatch

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to GemmaWatch.

##  Project Vision

GemmaWatch is an **AI-powered visual regression & monitoring platform** using Ollama + Gemma for RCA, visual regression detection, and real-time dashboards.

**Current Focus**: Building a robust PoC (50% complete). Our primary goal is to implement the **Big 3** features:
1.  Core monitoring (HTTP, API, DNS, TCP)
2.  AI-powered RCA (Gemma integration)
3.  Scheduling engine (autonomous check execution)
4.  Alert system (Email/Slack notifications)
5.  Visual diff tool (pixel-level comparison)

### TODO Features for Future
See [README.md - TODO Section](README.md#-todo---future-implementation) for full feature roadmap.

## ️ Development Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- Ollama with `gemma:latest`
- Git

### Local Development

1. **Clone and setup backend**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Setup frontend**:
```bash
cd frontend
npm install
```

3. **Start services**:
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd backend && source venv/bin/activate && python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# Terminal 3: Frontend
cd frontend && npm run dev
```

##  Code Style Guide

### Python
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints where possible
- Max line length: 100 characters
- Use docstrings for functions/classes

Example:
```python
async def create_check(
    self, 
    site_id: str, 
    check_id: str, 
    status: str, 
    timestamp: str
) -> None:
    """
    Create a new check result in database.
    
    Args:
        site_id: ID of the monitored site
        check_id: Unique check execution ID
        status: Check status (SUCCESS/FAILED)
        timestamp: ISO format timestamp
    """
    # Implementation
```

### TypeScript/React
- Use TypeScript strictly (no `any` types)
- Component naming: PascalCase (e.g., `Dashboard.tsx`)
- Hook naming: camelCase (e.g., `useWebSocket`)
- Props interface naming: `ComponentNameProps`
- Max line length: 100 characters

Example:
```typescript
interface DashboardProps {
  sites: Site[];
  selectedSiteId: string | null;
  onSiteSelect: (siteId: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  sites,
  selectedSiteId,
  onSiteSelect,
}) => {
  // Component code
};
```

##  Git Workflow

### Branch Naming
- Feature: `feature/description` (e.g., `feature/scheduling-engine`)
- Bug fix: `fix/description` (e.g., `fix/websocket-reconnection`)
- Docs: `docs/description` (e.g., `docs/setup-guide`)
- Refactor: `refactor/description` (e.g., `refactor/sqlite-service`)

### Commit Messages
Use descriptive commit messages:
```
feat: Add scheduling engine with APScheduler
fix: Handle WebSocket reconnection on network failure
docs: Update installation instructions
refactor: Extract shared validation logic
test: Add unit tests for RCA generation
```

### Pull Requests
1. Create a feature branch from `main`
2. Make focused changes (don't mix multiple features)
3. Write tests for new functionality
4. Update documentation if needed
5. Submit PR with clear description of changes

##  Testing

### Backend Tests
```bash
cd backend
pytest tests/  # Run all tests
pytest tests/test_scraper.py  # Run specific file
pytest -v  # Verbose output
```

### Frontend Tests
```bash
cd frontend
npm run test  # Run Vitest
npm run test:ui  # UI mode
```

### E2E Tests
```bash
cd frontend
npx cypress open  # Interactive mode
npx cypress run  # Headless mode
```

##  Code Organization

### Backend Structure
```
backend/
  ├── main.py              # FastAPI app entry point
  ├── requirements.txt     # Python dependencies
  ├── .env.example         # Environment variable template
  ├── services/
  │   ├── scraper.py       # Screenshot & DOM capture
  │   ├── ai_service.py    # Gemma RCA integration
  │   ├── sqlite_service.py # Database operations
  │   └── neo4j_service.py # Optional graph DB (unused)
  └── tests/
      └── test_services.py
```

### Frontend Structure
```
frontend/
  ├── src/
  │   ├── components/      # React components
  │   │   ├── Dashboard.tsx # Main dashboard
  │   │   ├── SiteDetails.tsx # RCA display
  │   │   └── ...
  │   ├── App.tsx         # Entry point
  │   ├── App.css         # Global styles
  │   └── main.tsx        # Bootstrap
  ├── cypress/            # E2E tests
  ├── package.json        # Dependencies
  └── vite.config.ts      # Build config
```

##  Before Submitting PR

- [ ] Code follows style guide
- [ ] All tests pass (`pytest` / `npm run test`)
- [ ] No console errors or warnings
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] Commit messages are descriptive
- [ ] No secret keys/credentials in code

##  Reporting Issues

1. **Check existing issues** - Avoid duplicates
2. **Provide context**:
   - OS and Python/Node version
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/logs if applicable

3. **Use issue template** (if available)

##  Development Resources

- **Architecture**: See [README.md - Architecture](README.md#architecture)
- **API Endpoints**: See [README.md - API Endpoints](README.md#-api-endpoints)
- **Tech Stack**: See [README.md - Tech Stack](README.md#technology-stack)
- **Ollama Docs**: https://ollama.ai/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/

##  Priority Features (Low Hanging Fruit)

Good starting points for contributors:

1. **Error Deduplication UI** - Group identical errors in results list
   - Effort: Medium (~6 hours)
   - Impact: Better UX at scale

2. **Custom RCA Prompts** - Make Gemma prompts configurable
   - Effort: Low (~4 hours)
   - Impact: Flexibility for different use cases

3. **Data Retention Policies** - Auto-cleanup old checks
   - Effort: Low (~2 hours)
   - Impact: Prevents unbounded database growth

4. **Multi-page Dashboard** - Split UI across multiple pages
   - Effort: Medium (~8 hours)
   - Impact: Better UX for 5+ monitored sites

##  Questions?

- Check [README.md](README.md) for general info
- Review [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) for detailed feature status
- Open a GitHub issue for clarification

---

**Thank you for contributing to GemmaWatch! **
