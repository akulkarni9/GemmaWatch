# GemmaWatch v2.0 - Comprehensive Feature Inventory

**Updated:** April 1, 2026 | **Version:** 2.1 | **Database:** SQLite + sqlite-vec | **AI Engine:** Ollama / Gemma

---

## ✨ PREMIUM INTELLIGENCE LAYER (New in v2.0)

### High-Precision Analyst Persona
- **Role-based Persona**: Implementation of a professional "Observability Analyst" tone.
- **Zero-Fluff Policy**: Removal of conversational filler (e.g., "Certainly," "It's a pleasure").
- **Deterministic Entity Recognition**: Pre-AI scanning for site names (e.g., "Mark") to force 100% accurate structured routing.

### Autonomous Learning Catalogue (HITL)
- **Three-Tier Knowledge Base**: 
    - **Primary**: Verified, high-confidence patterns used for RAG.
    - **Pending**: High-confidence candidates awaiting human review.
    - **Shadow**: Low-confidence logs for historical audit.
- **Human-in-the-Loop (HITL)**: Admin interface for approving/editing AI-generated root causes.

### Vector-Native RAG (sqlite-vec)
- **SQL-Native Search**: Performance-optimized RAG using high-speed SQL JOINs between virtual vector tables and relational metadata.
- **Atomic Ingestion**: Unified transactions for metadata updates and vector embedding storage.
- **Deduplication**: Intelligent pattern matching using cosine similarity (threshold ~0.92).

### Temporal Grounding
- **Server-Sync Time**: AI is aware of real-time server timestamps for accurate relative queries (e.g., "last 24h").
- **Dynamic SQL Generation**: Grounded generation to prevent "hallucinated" dates.

---

## 🛡️ MONITORING & OBSERVABILITY

### Check Types Implemented 
- **HTTP/Web Monitoring** - Full page capture, screenshot, and DOM analysis.
- **API Endpoint Checks** - REST API status validation.
- **DNS Resolution Checks** - Hostname verification.
- **TCP Connectivity Checks** - Port/host connectivity.

### Advanced Observability
- **Visual Regression Detection**: Playwright-powered snapshot comparisons.
- **Anomaly Detection**: Statistical z-score analysis for response time & DOM elements, with Gemma interpretation of anomalies.
- **Correlation Engine**: Cross-site event correlation to identify global incidents, stored in the `incidents` table.
- **Root Cause Analysis (RCA)**: Deep analysis using console logs, network errors, and DOM context with structured, step-by-step repair pipelines.
- **Error Fingerprinting & Grouping**: SHA-256 pattern deduplication for recurring failures; Gemma assigns human-readable titles and descriptions to new patterns asynchronously.
- **Autonomous Scheduler**: Background interval-based check engine; each site can have a configurable `frequency` (in seconds) and is dispatched automatically via `scheduler_service.py`.
- **Alerting System**: Email notifications on consecutive failures, anomalies, and cross-site incidents via `alert_service.py`.

---

## 🎨 UI/UX & DESIGN SYSTEM

### Premium Aesthetic Overhaul
- **Obsidian & Emerald Palette**: High-contrast dark mode for technical focus.
- **Glassmorphism 2.0**: Three layered glass thickness tokens (`glass-thin`, `glass-thick`).
- **GPU-Accelerated Animations**: Staggered entrance transitions for all dashboard elements.
- **Sliding Interface**: Fluid tab switchers and drawer-based navigation.

---

## 🔑 SECURITY & DATA

### Authentication & Authorization
- **OAuth Integration**: Google & GitHub login providers.
- **JWT Session Management**: Secure accessible tokens with cookie-based persistence.
- **Role-Based Access (RBAC)**: Admin-only access for catalogue approval and settings.

### Data Management
- **SQLite Persistence**: Centralized storage for checks, metrics, and RCA.
- **sqlite-vec Extension**: Integrated vector storage directly in the relational DB.

---

## 🚀 CURRENT READINESS: 100% (PHASE 2 COMPLETE)

**All architectural pillars are fully implemented and verified.**
- **Monitoring**: [x] Complete
- **Authentication**: [x] Complete
- **Intelligence (RAG)**: [x] Complete
- **HITL Pipeline**: [x] Complete
- **Visual Polish**: [x] Complete

---

##  UI/DASHBOARD FEATURES

### Pages & Layouts 
- **Single-page Dashboard** - All monitoring, analytics, and site management in one view
- **Responsive Design** - Grid layout with left sidebar (sites) and right panel (results)
- **Dark Theme** - Dark mode default (#050510 background, blue/indigo accents)
- **Mobile-Responsive** - 1 col (mobile) → 4 cols (desktop) grid layout

### Components 
- **Site Management Panel**
  - Add site modal (name, URL, check type)
  - Site list with inline search filter
  - Filter by check type (HTTP/API/DNS/TCP)
  - One-click site deletion with undo prevention
  - Manual check trigger (refresh button)

- **Real-time Activity Feed**
  - Last 10 status messages from WebSocket
  - Live monitoring progress (, , , )
  - Real-time error/warning display

- **Metrics Visualization**
  - **UptimeDisplay** - Circular progress bar (0-100%), 7-day uptime calculation, color-coded status ( Excellent > 99.5%,  Good 95-99.5%, ️ Fair 90-95%,  Poor < 90%)
  - **ErrorDistribution** - Pie chart (Console Errors vs Network Failures)
  - **MetricsChart** - Line chart trends for Response Time (ms), DOM Elements, Total Errors

- **Site Details Panel**
  - Latest check result for selected site
  - Status badge (SUCCESS/FAILED, HTTP code)
  - RCA display with confidence score
  - **Structured Repair Pipeline** (`RepairPipeline.tsx`): Step-by-step investigate/command/verify actions
  - **Error Fingerprint Panel** (`ErrorFingerprintPanel.tsx`): Deduplicated recurring error patterns with severity, type badge (console/network), and Gemma-generated title/description
  - Console log viewer modal (click to expand)
  - Network error viewer modal (click to expand)
  - Screenshot viewer modal (full-page mode)

- **Check Results Display**
  - Status indicator ( SUCCESS /  FAILED)
  - Timestamp with locale formatting
  - HTTP status codes
  - Visual regression alerts (when detected)
  - RCA alerts with suggested fixes
  - Console/Network error counts with badges

### Stats Bar 
- Total Checks, Pass Rate %, Registered Sites, Live Connections

### UI Features NOT Implemented 
- **Multi-page Navigation** - No routing, single dashboard only (auth pages aside)
- **Export/Reports** - No PDF, CSV export functionality
- **Scheduling UI** - Frequency stored per-site but no self-serve UI for changing it
- **Webhook Configuration** - No outbound webhooks UI
- **API Key Management** - No key generation/rotation UI
- **Graph Visualization** - No dependency graph, failure causality tree
- **Timeline View** - No historical timeline of events
- **Comparison View** - No side-by-side baseline vs current screenshot diff
- **Dark/Light Theme Toggle** - No theme switcher (always dark)
- **Bulk Operations** - No bulk delete/edit sites
- **Site Groups/Tags** - No categorization system
- **Custom Dashboards** - No widget customization or multiple dashboard views

---

##  DATA MANAGEMENT

### Database (SQLite) 

**Tables:**
1. **sites** - Monitored websites
   - `id` (TEXT PK), `name`, `url`, `check_type`, `frequency`, `last_checked_at`, `next_check_at`, `created_at`
   
2. **checks** - Individual monitoring runs
   - `id` (TEXT PK), `site_id` (FK), `status`, `timestamp`, `screenshot_url`, `status_code`
   - `console_log_count`, `network_error_count`
   - `console_logs_json` (full logs), `network_errors_json` (full errors)
   
3. **root_causes** - RCA analysis results
   - `id`, `check_id` (FK), `probable_cause`, `confidence`, `repair_action`, `repair_steps_json`
   
4. **metrics** - Performance analytics
   - `id`, `site_id` (FK), `check_id` (FK), `response_time_ms`, `dom_elements`
   - `console_errors`, `network_failures`, `timestamp`

5. **error_fingerprints** - Deduplicated error patterns
   - `id` (SHA-256 hash), `type` (console|network), `pattern` (normalized), `title`, `description`, `severity`
   - `first_seen`, `last_seen`, `total_occurrences`

6. **check_fingerprints** - Join table linking checks to fingerprints
   - `check_id` (FK), `fingerprint_id` (FK)

7. **incidents** - Cross-site correlated failure events
   - `id`, `title`, `severity`, `status`, `affected_site_ids_json`, `probable_shared_cause`
   - `created_at`, `resolved_at`, `resolved_by` (FK → users)

8. **anomaly_events** - Statistical anomaly log
   - `id`, `site_id` (FK), `check_id` (FK), `z_score`, `metric_type`, `severity`, `gemma_interpretation`

9. **users** - OAuth user accounts (Google/GitHub)
   - `id`, `email`, `name`, `avatar_url`, `provider`, `provider_id`, `role`, `created_at`

10. **shadow_catalogue / pending_catalogue / primary_catalogue** - Three-tier HITL knowledge base

11. **alert_config / alert_log** - Email alert configuration and history

12. **chat_messages** - Persistent chat session history

### Data Retrieval 
- **GET /sites** - List all monitored sites with metadata
- **GET /sites/{site_id}/history** - Get check history (limit 10-50)
  - Includes full RCA, console logs, network errors
  - Sorted by timestamp DESC
  - Lazy loads from database
  
- **GET /sites/{site_id}/metrics** - Historical metrics (last 50 checks)
  - Response time trends
  - DOM element counts
  - Error counts over time
  
- **GET /sites/{site_id}/uptime** - Uptime percentage calculation
  - 7-day window default (customizable)
  - Calculated from checks table (SUCCESS/FAILED ratio)
  
- **GET /analytics/summary** - Cross-site analytics
  - Total sites, uptime per site, latest status

### Data Persistence 
- **Automatic check logging** - Every check creates entry in `checks` table
- **RCA persistence** - Root causes saved to `root_causes` table
- **Error details captured** - Console logs and network errors stored as JSON
- **Metrics logging** - Performance metrics logged to `metrics` table
- **Site lifecycle** - Sites tracked with creation timestamp

### Data Management NOT Implemented 
- **Backup/Restore** - No database backup utilities
- **Data Archival** - No automatic data cleanup/archival after X days
- **Data Retention Policy** - No configurable retention periods
- **Migration System** - No versioning/schema migrations framework
- **Audit Logging** - No audit trail of data changes
- **Data Encryption** - No encryption at rest or in transit
- **Connection Pooling** - No connection pool management (SQLite only)
- **Transactions** - Limited transaction support
- **Queries Optimization** - No indexing on frequent queries (site_id, timestamp)
- **Schema Versioning** - Manual ALTER TABLE approach only

---

##  ANALYSIS FEATURES

### AI/ML Features 

**Root Cause Analysis (RCA)**
- **Triggered on failure** - When HTTP status >= 400 or network errors present
- **Inputs to Gemma:**
  - HTTP status code and error message
  - Last 500 chars of console logs (captured in real-time)
  - Last 500 chars of network failures
  - Distilled page DOM (interactive elements only)
  
- **RCA Output:**
  - `probable_cause` - Specific root cause with evidence
  - `confidence` - 0.0-1.0 confidence score
  - `repair_action` - Specific, actionable fix (not generic)
  - `category` - Frontend|Backend|Network|Database|Infrastructure
  
- **Smart Parsing:**
  - JSON extraction from wrapped responses
  - Fallback values with actual error context (not generic)
  - 60-second timeout for Ollama calls

**Visual Regression Detection**
- **Triggered when:** Current DOM differs from baseline (character comparison)
- **Inputs:**
  - Baseline DOM (interactive elements from first check)
  - Current DOM (interactive elements from latest check)
  
- **Output:**
  - `is_regression` - Boolean (true/false)
  - `severity` - Low|Medium|High
  - `change_summary` - Human-readable change description
  - `impact` - What user action is blocked by this change
  
- **Baseline Management:**
  - First check creates baseline (saved to `screenshots/baselines/{site_id}.png`)
  - Subsequent checks compare against baseline
  - Baseline persists across multiple checks

**Interactive Element Detection**
- Distills full page to interactive elements only:
  - `<button>`, `<a>`, `<input>`, `<select>`, `<textarea>`
  - Elements with `role="button"` attribute
  - Captured properties: tag, id, text/placeholder, ARIA role
  - Visibility-aware (excludes hidden/off-screen elements)

### AI/ML Features NOT Implemented 
- **Screenshot Pixel Comparison** - No visual diff highlighting (comparing DOM only)
- **Performance Regression Detection** - No baseline response time comparison
- **Predictive Alerts** - No failure prediction based on trends
- **Semantic Similarity** - No NLP similarity matching for visual changes
- **Image Diffing** - No OpenCV or advanced image comparison
- **Custom Prompts** - Gemma prompts hardcoded, not user-configurable
- **Feedback Loop** - No way to correct or train from RCA failures

---

##  REAL-TIME FEATURES

### WebSocket 
- **Endpoint:** `GET /ws/status`
- **Connection Manager** - Handles multiple concurrent connections
- **30-second ping timeout** - Keeps connections alive
- **Automatic reconnection** - Client-side 2-second retry on disconnect

### Real-time Messages 
1. **Status Messages** (`type: "status"`)
   -  Starting HTTP check
   -  Screenshot captured (HTTP status + element count)
   -  UI change detected
   -  Analyzing failure with Gemma
   -  Check completed

2. **Result Messages** (`type: "result"`)
   - Full check result with RCA and visual analysis
   - Screenshot URL, logs, error details
   - Status (SUCCESS/FAILED)

3. **Error Messages** (`type: "error"`)
   - Error details if check fails

### Broadcast Features 
- Messages broadcast to all connected clients
- Automatic cleanup of disconnected clients
- Queue-less (messages not persisted)

### Real-time Features NOT Implemented 
- **Bi-directional Communication** - Client can only receive, not send updates
- **Message Persistence** - No queue for offline clients
- **Subscribing to Specific Sites** - All clients receive all updates
- **Presence Indicators** - No "who's online" feature
- **Message History** - No WebSocket message replay
- **Rate Limiting** - No message rate limits
- **Compression** - No message compression
- **Server-sent Events (SSE)** - Only WebSocket, no fallback
- **Typed Channels** - No per-site or per-user channels

---

##  HISTORICAL DATA & ANALYTICS

### Historical Data 
- **Check History** - Persists all checks in SQLite with full details
- **RCA History** - All RCA results linked to specific checks
- **Metrics History** - 50+ historical metric snapshots per site
- **Timestamps** - All checks tagged with ISO 8601 timestamps

### Analytics Features 
- **Uptime Calculation** - 7-day uptime percentage (SUCCESS count / total count)
- **Response Time Trending** - Line chart of response_time_ms over time
- **Error Distribution** - Pie chart of console errors vs network failures
- **DOM Element Trends** - Track page complexity over time
- **Per-Site Metrics** - Individual site drill-down with historical data
- **Cross-Site Summary** - Overall analytics dashboard with all sites

### Analytics Features NOT Implemented 
- **Custom Date Ranges** - Fixed 7-day uptime window only
- **MTTR (Mean Time To Repair)** - No failure duration tracking
- **SLA Metrics** - No SLA calculation or breach alerts
- **Trend Analysis** - No statistical trend detection
- **Alerts Triggered** - No alert history or trigger tracking
- **Cost Analytics** - No cost tracking or optimization metrics
- **Comparative Analytics** - No site-to-site comparison reports
- **Forecasting** - No failure prediction or time-series forecasting
- **Custom Metrics** - No ability to define custom analytics
- **Data Aggregation** - Only basic metrics, no percentile/quantile analysis
- **Report Export** - No automated report generation or scheduling

---

## ️ CONFIGURATION & SETTINGS

### Configurable via .env 
- `OLLAMA_URL` - Default: `http://127.0.0.1:11434/api/generate`
- `MODEL_NAME` - Default: `gemma:latest`

### System Configuration 
- **Check Type Selection** - HTTP/API/DNS/TCP per site
- **Frequency Field** - Stored per site (not used to schedule, just metadata)
- **Timeout** - 10s default for HTTP/API checks (hardcoded)
- **Max Retries** - 3 retries with exponential backoff (hardcoded)
- **Retry Backoff** - 2, 4, 8 second intervals (hardcoded)
- **WS Timeout** - 30-second ping interval (hardcoded)

### Configuration NOT Implemented 
- **Scheduling** - No automatic interval-based checks (manual trigger only)
- **Threshold Configuration** - No configurable alert thresholds
- **Email/Slack Integration** - No notification channels
- **Webhook Configuration** - No outbound webhooks
- **Rate Limiting** - No API rate limits
- **Request Headers** - Headers configurable per API check, but not global defaults
- **Proxy Configuration** - No proxy support
- **SSL/TLS Settings** - No certificate validation toggles
- **Logging Level** - No configurable log levels
- **Feature Flags** - No feature toggles or experimental features
- **Multi-tenancy** - Single-tenant only

---

##  ERROR HANDLING

### Error Capture 
- **Console Logs** - Real-time browser console capture (log/warn/error/debug)
  - Includes timestamp, level, message
  - Stored as JSON array in database
  
- **Network Errors** - Failed HTTP requests captured automatically
  - Method, URL, error message
  - Stored as JSON array in database
  - Shows up to network_error_count in results
  
- **HTTP Status Codes** - All status codes captured (redirects, 404s, 5xx errors)
  - Failure marked if status >= 400 or status == 0

### Error Analysis 
- **RCA Generation** - Gemma analyzes errors in context
- **Confidence Scoring** - RCA confidence based on evidence
- **Category Classification** - Frontend|Backend|Network|Database|Infrastructure
- **Actionable Fixes** - Structured, step-by-step repair pipeline (investigate → command → verify)
- **Error Fingerprinting** - SHA-256 based deduplication of recurring error patterns across checks
- **AI-Powered Pattern Naming** - Gemma generates concise titles and descriptions for newly discovered fingerprints

### Error Handling NOT Implemented 
- **Error Context** - Limited context (no stack traces, source maps)
- **Custom Error Handlers** - No user-defined error handling
- **Error Suppression** - No way to ignore expected errors
- **Error Replay** - No way to replay/re-run failed checks with debugging
- **Graceful Degradation** - System fails fast, doesn't have fallbacks

---

##  SCREENSHOTS & VISUAL COMPARISON

### Screenshot Management 
- **Baseline Capture** - First check creates baseline screenshot (full-page)
  - Stored: `screenshots/baselines/{site_id}.png`
  - Never overwritten (first check wins)
  
- **Current Capture** - Every check creates timestamped screenshot
  - Stored: `screenshots/currents/{site_id}_{timestamp}.png`
  - Full-page height captured
  
- **Screenshot Serving** - Static mount at `/screenshots` endpoint
  - Accessible via URL for modal viewing
  - Full resolution available

### Screenshot Comparison 
- **DOM Distillation** - Extracts interactive elements from DOM
- **Character-level Comparison** - Baseline vs current DOM comparison
- **Regression Detection** - Boolean is_regression flag
- **Severity Levels** - Low|Medium|High severity classification
- **Change Summary** - Human-readable description of what changed

### Visual Features NOT Implemented 
- **Pixel-level Diff Tool** - No visual highlighting of differences
- **Diff Image Generation** - No image comparison with highlighted regions
- **Before/After Slider** - No interactive baseline vs current slider
- **DOM Tree Visualization** - No visual DOM comparison panel
- **Annotation Tools** - No way to mark/comment on visual differences
- **Baseline Management UI** - No way to update baseline or override defaults
- **Screenshot Storage Cleanup** - No automatic old screenshot deletion
- **Compression** - Screenshots stored uncompressed (PNG full size)

---

##  PERFORMANCE & ANALYTICS

### Metrics Tracked 
- **Response Time** - Milliseconds from request to response
- **DOM Elements** - Count of interactive elements on page
- **Console Errors** - Count of error-level logs
- **Network Failures** - Count of failed HTTP requests
- **Uptime Percentage** - SUCCESS vs FAILED check ratio

### Performance Features 
- **Metrics Logging** - Per-check metrics persisted to `metrics` table
- **Historical Trends** - Up to 50 checks retained per site
- **Metric Retrieval** - `/sites/{site_id}/metrics` API
- **Trend Visualization** - Line chart of response time and DOM elements

### Performance NOT Tracked 
- **First Contentful Paint (FCP)** - No web vitals tracking
- **Largest Contentful Paint (LCP)** - No core web vitals
- **Cumulative Layout Shift (CLS)** - No stability metrics
- **Time to Interactive (TTI)** - No interactivity metrics
- **Bandwidth Usage** - No payload size tracking
- **JavaScript Execution Time** - No script timing analysis
- **Render Time** - No detailed paint/layout metrics
- **Memory Usage** - No memory profiling
- **Database Query Time** - No query performance tracking
- **API Latency Distribution** - No percentile or quantile analysis

---

##  SECURITY & RELIABILITY

### Security Features 
- **CORS Enabled** - Allows any origin (development mode)
- **OpenAPI Documentation** - `/docs` and `/redoc` available
- **Health Checks** - `/health` endpoint for service status

### Security NOT Implemented 
- **Authentication** - No login/authentication required
- **Authorization** - No role-based access control
- **Input Validation** - No strict URL validation or payload limits
- **Rate Limiting** - No per-user or per-IP rate limits
- **HTTPS/TLS** - Not enforced (HTTP only in dev)
- **CORS Restrictions** - Wildcard origin allows all domains
- **SQL Injection Prevention** - Parameterized queries used but no additional hardening
- **CSRF Protection** - No CSRF tokens
- **API Keys** - No API key authentication
- **Encryption** - No encryption at rest or in transit
- **Audit Logging** - No security event logging
- **Secrets Management** - .env file not encrypted, hardcoded defaults

### Reliability Features NOT Implemented 
- **Database Replication** - Single SQLite instance only
- **Failover** - No failover mechanism
- **Load Balancing** - Single-instance only
- **Circuit Breaker** - No circuit breaker for Ollama failures
- **Message Queue** - No background job queue
- **Check Distribution** - All checks run on single process
- **Scaling** - No horizontal scaling support
- **Health Recovery** - No automatic recovery from failures

---

##  SUMMARY & GAP ANALYSIS

### Core Strengths 
1. **Full-stack AI Integration** - Ollama + Gemma for RCA, visual regression, fingerprint naming, and anomaly interpretation
2. **Multiple Check Types** - HTTP, API, DNS, TCP out of the box
3. **Real-time Dashboard** - WebSocket-powered live updates
4. **Complete Monitoring Pipeline** - Capture → Analysis → Fingerprinting → Storage → Visualization
5. **Interactive Element Detection** - Smart DOM distillation for visual regression
6. **Confidence Scoring** - RCA results have confidence metrics and structured repair steps
7. **Browser-native Capture** - Uses Playwright for realistic page loading
8. **Error Deduplication** - Fingerprinting engine collapses recurring failures into actionable patterns
9. **Autonomous Scheduling** - Sites are checked automatically at their configured frequency
10. **Security** - OAuth 2.0 (Google/GitHub) + JWT sessions + Role-based access (Admin/Viewer)

### Critical Gaps for Production 

**High Priority (needed for any scale):**
-  **No Visual Diff Tool** - Only DOM comparison, no pixel diff
-  **No Data Isolation** - All users access same database (single-tenant)
-  **No Scheduling UI** - Frequency stored but not surfaceable in the UI

**Medium Priority:**
-  **Export/Reporting** - No way to generate or export reports
-  **Bulk Operations** - Can't manage multiple sites efficiently
-  **Custom Prompts** - Gemma prompts are hardcoded
-  **Data Retention** - No automatic cleanup of old checks

**Lower Priority (enhancement only):**
-  **Performance Profiling** - Could add web vitals tracking
-  **Cost Analytics** - Track check execution costs
-  **Dependency Graphs** - Visualize failure causality

### Recommended PoC Improvements (Ranked by Impact)

#### Tier 1: Essential (Week 1)
1. **Add Scheduling Engine** - Cron-based or interval-based check triggering
   - Impact: Converts manual tool to autonomous monitoring
   - Effort: Medium (add background task scheduler)
   
2. **Add Basic Authentication** - Simple password/API key auth
   - Impact: Prevents unauthorized access/data deletion
   - Effort: Low (FastAPI auth middleware)

3. **Add Alert/Notification System** - Email or webhook on failures
   - Impact: Can't use dashboard 24/7, need alerting
   - Effort: Medium (email client + template system)

#### Tier 2: High-Impact (Week 2)
4. **Add Visual Diff Tool** - Highlight pixel differences between baseline and current
   - Impact: Critical for visual regression PoC demo
   - Effort: Medium (integrate image diffing library)
   
5. **Add Error Grouping** - Fingerprint similar errors, deduplicate
   - Impact: Makes results actionable (not 100 duplicate errors)
   - Effort: Medium (signature generation + bucketing)

6. **Add Check Scheduling UI** - Configure frequency/times per site
   - Impact: Users can self-serve without code changes
   - Effort: Low (add input fields and schedule persistence)

#### Tier 3: Polish (Week 3)
7. **Add Report Export** - PDF or CSV export of results
   - Impact: Stakeholders can share findings
   - Effort: Low (use ReportLab or similar)

8. **Add Multi-page Dashboard** - Separate pages for sites, history, analytics
   - Impact: Better UX at scale (5+ sites)
   - Effort: Medium (add router and pages)

9. **Add Data Retention Policy** - Auto-cleanup of old checks
   - Impact: Database won't grow unbounded
   - Effort: Low (scheduled job + delete SQL)

### Current PoC Readiness: **9/10**
-  Can monitor sites autonomously (scheduler)
-  Can capture failures with RCA and structured repair pipeline
-  Can display results in real-time
-  Can authenticate users (Google/GitHub OAuth)
-  Can alert on failures, anomalies, and incidents via email
-  Can group recurring errors with Error Fingerprinting
-  Has cross-site incident correlation
-  Has HITL knowledge catalogue for pattern approval
- ️ No pixel-level visual diff
-  No self-serve scheduling UI

---

##  Project Structure

```
GemmaWatch/
├── backend/
│   ├── main.py                          [FastAPI app, all API routes, WS, auth]
│   ├── requirements.txt
│   ├── services/
│   │   ├── ai_service.py               [Ollama/Gemma: RCA, visual analysis, fingerprint metadata]
│   │   ├── scraper.py                  [Playwright, screenshot, DOM extract]
│   │   ├── sqlite_service.py           [All DB operations]
│   │   ├── check_types.py              [HTTP/API/DNS/TCP checks]
│   │   ├── fingerprint_service.py      [Error normalization, SHA-256 hashing, pattern upsert]
│   │   ├── scheduler_service.py        [Autonomous background check dispatch]
│   │   ├── anomaly_service.py          [Z-score anomaly detection + Gemma interpretation]
│   │   ├── correlation_service.py      [Cross-site incident creation]
│   │   ├── alert_service.py            [Email alerts for failures/anomalies/incidents]
│   │   ├── catalogue_service.py        [Three-tier HITL knowledge base + sqlite-vec RAG]
│   │   ├── chat_service.py             [High-precision AI chat with entity recognition]
│   │   ├── auth_service.py             [OAuth 2.0 (Google/GitHub) + JWT sessions]
│   │   └── embedding_service.py        [Nomic-embed text embeddings for RAG]
│   └── tests/
│       ├── test_catalogue_service.py
│       ├── test_check_types.py
│       └── conftest.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx           [Main UI: activity feed, site list, fingerprint badges]
│   │   │   ├── SiteDetails.tsx         [Site modal: RCA, RepairPipeline, ErrorFingerprintPanel]
│   │   │   ├── ErrorFingerprintPanel.tsx [Renders deduplicated error patterns]
│   │   │   ├── RepairPipeline.tsx      [Renders structured step-by-step repair actions]
│   │   │   ├── MetricsChart.tsx
│   │   │   ├── UptimeDisplay.tsx
│   │   │   ├── ErrorDistribution.tsx
│   │   │   ├── auth/                   [OAuth login pages]
│   │   │   ├── catalogue/              [HITL Admin approval dashboard]
│   │   │   ├── chat/                   [AI chat interface]
│   │   │   ├── incidents/              [Incident management UI]
│   │   │   ├── settings/               [Alert config UI]
│   │   │   └── layout/                 [App shell, nav, sidebar]
│   │   └── index.css
│   ├── vite.config.ts
│   └── package.json
└── screenshots/
    ├── baselines/
    └── currents/
```

---

##  Quick Start Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# Frontend
cd frontend
npm install
npm run dev   # Vite dev server on localhost:5173

# Ollama (separate terminal, before running backend)
ollama run gemma

# Health check
curl http://localhost:8002/health

# Add a site
curl -X POST "http://localhost:8002/monitor?url=https://example.com&name=Example&check_type=http"
```

---

**Last Updated:** April 1, 2026  
**Analyzed Codebase Version:** 2.1 (Error Fingerprinting + Full Intelligence Layer)
