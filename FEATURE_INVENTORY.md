# GemmaWatch v2.0 - Comprehensive Feature Inventory

**Generated:** March 28, 2026 | **Version:** 2.0 | **Database:** SQLite | **AI Engine:** Ollama + Gemma 3B

---

##  MONITORING FEATURES

### Check Types Implemented 
- **HTTP/Web Monitoring** - Full webpage capture with screenshot and DOM analysis
- **API Endpoint Checks** - REST API status validation (GET/POST/custom methods)
- **DNS Resolution Checks** - Hostname to IP resolution validation
- **TCP Connectivity Checks** - Port/host connectivity verification

### Check Capabilities 
- Multiple check type support per site
- Automatic retry logic with exponential backoff (2, 4, 8 second intervals)
- Configurable timeout handling (10s default, extensible)
- HTTP status code capture (200-5xx range)
- Response time measurement (milliseconds)
- Custom headers support for API checks

### Check Capabilities NOT Implemented 
- HTTP HEAD request support (only GET/POST)
- SSL/TLS certificate validation reports
- Custom HTTP methods (PATCH, PUT, DELETE) - only GET/POST supported
- Request body validation/schema validation
- API response body schema validation
- GraphQL query checks
- gRPC endpoint monitoring
- WebSocket connection monitoring
- Load testing / performance profiling checks

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
- **Multi-page Navigation** - No routing, single dashboard only
- **User Authentication** - No login/permissions system
- **Export/Reports** - No PDF, CSV export functionality
- **Scheduling UI** - No frequency/schedule management interface
- **Alert Configuration** - No threshold/alert rule setup UI
- **Webhooks UI** - No integration management interface
- **API Key Management** - No key generation/rotation UI
- **Role-based Access Control** - No user roles or permissions
- **Graph Visualization** - No dependency graph, failure causality tree
- **Timeline View** - No historical timeline of events
- **Comparison View** - No side-by-side baseline vs current screenshot diff
- **Dark/Light Theme Toggle** - No theme switcher (always dark)
- **Notifications** - No in-app toast notifications, badges, or popups
- **Bulk Operations** - No bulk delete/edit sites
- **Site Groups/Tags** - No categorization system
- **Custom Dashboards** - No widget customization or multiple dashboard views

---

##  DATA MANAGEMENT

### Database (SQLite) 

**Tables:**
1. **sites** - Monitored websites
   - `id` (TEXT PK), `name`, `url`, `check_type`, `frequency`, `created_at`
   
2. **checks** - Individual monitoring runs
   - `id` (TEXT PK), `site_id` (FK), `status`, `timestamp`, `screenshot_url`, `status_code`
   - `console_log_count`, `network_error_count`
   - `console_logs_json` (full logs), `network_errors_json` (full errors)
   
3. **root_causes** - RCA analysis results
   - `id`, `check_id` (FK), `probable_cause`, `confidence`, `repair_action`
   - **Missing:** `category` (computed at runtime only)
   
4. **metrics** - Performance analytics
   - `id`, `site_id` (FK), `check_id` (FK), `response_time_ms`, `dom_elements`
   - `console_errors`, `network_failures`, `timestamp`

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
- **Custom ML Models** - Only using Ollama + Gemma (no custom models)
- **Screenshot Pixel Comparison** - No visual diff highlighting (comparing DOM only)
- **Pattern Recognition** - No learning from historical failures
- **Anomaly Detection** - No statistical anomaly detection (exact comparison only)
- **Performance Regression Detection** - No baseline response time comparison
- **Predictive Alerts** - No failure prediction based on trends
- **Semantic Similarity** - No NLP similarity matching for visual changes
- **Image Diffing** - No OpenCV or advanced image comparison
- **Custom Prompts** - Gemma prompts hardcoded, not user-configurable
- **RAG System** - No retrieval-augmented generation with knowledge base
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
- **Actionable Fixes** - Specific repair steps, not generic advice

### Error Handling NOT Implemented 
- **Error Grouping** - No deduplication or fingerprinting of similar errors
- **Error Context** - Limited context (no stack traces, source maps)
- **Custom Error Handlers** - No user-defined error handling
- **Error Suppression** - No way to ignore expected errors
- **Error Notifications** - No immediate alerts on first error
- **Error Replay** - No way to replay/re-run failed checks with debugging
- **Error Trends** - No detection of error patterns over time
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
1. **Full-stack AI Integration** - Ollama + Gemma for RCA and visual regression
2. **Multiple Check Types** - HTTP, API, DNS, TCP out of the box
3. **Real-time Dashboard** - WebSocket-powered live updates
4. **Complete Monitoring Pipeline** - Capture → Analysis → Storage → Visualization
5. **Interactive Element Detection** - Smart DOM distillation for visual regression
6. **Confidence Scoring** - RCA results have confidence metrics
7. **Browser-native Capture** - Uses Playwright for realistic page loading

### Critical Gaps for Production 

**High Priority (needed for any scale):**
-  **No Scheduling System** - Only manual check triggering
-  **No Authentication** - Anyone can access, modify, delete all data
-  **No Data Isolation** - All users access same database
-  **No Error Grouping** - Duplicate errors shown individually
-  **No Alert Notifications** - Results only visible in dashboard
-  **No Visual Diff Tool** - Only logcal comparison, no pixel diff

**Medium Priority (nice-to-have for PoC):**
-  **Export/Reporting** - No way to generate or export reports
-  **Bulk Operations** - Can't manage multiple sites efficiently
-  **Custom Prompts** - Gemma prompts are hardcoded
-  **Multi-page Navigation** - Everything crammed into single page
-  **Data Retention** - No automatic cleanup of old data

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

### Current PoC Readiness: **6/10**
-  Can monitor sites
-  Can capture failures with RCA
-  Can display results in real-time
-  Can't schedule checks (manual only)
-  Can't alert on failures
-  Can't compare visuals visually
-  No user authentication
- ️ Limited to single machine

---

##  Project Structure

```
GemmaWatch/
├── backend/
│   ├── main.py                          [FastAPI app, monitoring endpoints]
│   ├── requirements.txt
│   ├── services/
│   │   ├── ai_service.py               [Ollama/Gemma integration]
│   │   ├── scraper.py                  [Playwright, screenshot, DOM extract]
│   │   ├── sqlite_service.py           [Database operations]
│   │   └── check_types.py              [HTTP/API/DNS/TCP checks]
│   └── tests/
│       ├── test_check_types.py
│       └── test_sqlite_service.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx           [Main UI component]
│   │   │   ├── SiteDetails.tsx
│   │   │   ├── MetricsChart.tsx
│   │   │   ├── UptimeDisplay.tsx
│   │   │   └── ErrorDistribution.tsx
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

**Last Updated:** March 28, 2026  
**Analyzed Codebase Version:** 2.0 (SQLite Edition)
