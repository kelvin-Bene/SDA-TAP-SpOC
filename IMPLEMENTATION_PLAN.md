# UCT Benchmark - Implementation Plan: Fixing All Identified Issues

**Date:** 2026-03-25 (Updated with final decisions)
**Based on:** QA Deep Test Report (Round 2) + TEST_REPORT.md (Round 1) + Kelvin's feedback
**Codebase locations:**
- Backend: `D:\DMR(kelvinallignment)\combined-new\backend_api\`
- Frontend: `D:\DMR(kelvinallignment)\UCT-Benchmark-DMR\combined\frontend\src\`
- Core library: `D:\DMR(kelvinallignment)\combined-new\uct_benchmark\`

---

## Decisions Made

1. **Per-user API keys**: Remove silent fallback for user operations. Add `ADMIN_UDL_TOKEN`/`ADMIN_ESA_TOKEN` env vars for admin-role users and system batch jobs only. Normal users MUST configure their own tokens in Profile Settings.

2. **Satellite data scraping**: Admin-only, uses `ADMIN_UDL_TOKEN` env var. Not per-user.

3. **Dataset cleanup**: Delete the 11 failed datasets.

4. **Results `/report` endpoint**: Implement basic JSON report endpoint.

5. **Directory consolidation**: Consolidate into a platform-agnostic `backend/` + `frontend/` structure with independent Dockerfiles and a root `docker-compose.yml`. No Railway-specific config. Designed for Docker, bare metal, Kubernetes, or air-gapped internal deployment. This is Fix #0 below.

---

## Critical Finding: Codebase Split

The production backend (`combined-new/`) is NOT tracked in git. It has auth, feedback, and other routers missing from the git-tracked `UCT-Benchmark-DMR/combined/`. A `git clone` gives you an incomplete, broken system. Fix #0 addresses this by consolidating everything into one git-tracked structure.

---

## Issue Inventory (Consolidated from Both Reports)

### Critical (P0)
| # | Issue | Source | Component |
|---|-------|--------|-----------|
| 1 | Dataset download returns 500 on ALL datasets | QA Round 2 B1 | Backend |

### High (P1)
| # | Issue | Source | Component |
|---|-------|--------|-----------|
| 2 | Results page shows "Not Found" for valid data | QA Round 2 B2 | Frontend |
| 3 | Server file paths leaked in API responses | QA Round 2 B3 | Backend |
| 4 | Per-user UDL/ESA keys not enforced (shared key) | User request | Backend + Frontend |

### Medium (P2)
| # | Issue | Source | Component |
|---|-------|--------|-----------|
| 5 | Submit form shows no validation errors | QA Round 2 B4 | Frontend |
| 6 | Delete button has no confirmation dialog | QA Round 2 B5 | Frontend |
| 7 | Dashboard TOP RANK stuck on "Loading..." | QA Round 2 B6 | Frontend |
| 8 | 3 API endpoints not implemented | QA Round 2 B7 | Backend |

### Low (P3)
| # | Issue | Source | Component |
|---|-------|--------|-----------|
| 9 | Missing security headers (HSTS, CSP) | QA Round 2 B8 | Backend |
| 10 | track_id stored as string "nan" | QA Round 2 B9 | Backend/DB |
| 11 | Leaderboard dataset_id/name null | QA Round 2 B10 | Backend |
| 12 | 11/17 datasets in failed state | QA Round 2 B11 | DB cleanup |
| 13 | satellites array empty despite count=8 | QA Round 2 B12 | Backend |
| 14 | Download error shows no user feedback | QA Round 2 U1 | Frontend |
| 15 | No CI/CD pipeline | Round 1 | Infrastructure |
| 16 | No end-to-end pipeline tests | Round 1 | Testing |
| 17 | No load testing | Round 1 | Testing |

---

## Detailed Fix Plans

---

### Fix #0: Codebase Consolidation (PREREQUISITE)

**Problem:** The codebase is split across two directories that have diverged:
- `combined-new/` — has the production backend (auth, feedback, 7 routers, start.py) but is NOT in git
- `UCT-Benchmark-DMR/combined/` — git-tracked but missing auth module, only 5 routers, no feedback
- `frontend-deploy/` — a third copy of just the built frontend dist

A `git clone` gives you a broken system. The product owners can't deploy this.

**Target Structure:**
```
project-root/
├── backend/                    # Python FastAPI service
│   ├── Dockerfile              # Standalone, no Railway dependency
│   ├── pyproject.toml
│   ├── .env.example
│   ├── backend_api/            # From combined-new/backend_api/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── middleware/
│   │   ├── routers/            # All 7 routers
│   │   ├── jobs/
│   │   ├── models/
│   │   └── services/
│   ├── uct_benchmark/          # Core library from combined-new/
│   ├── data/                   # Runtime data directory
│   └── tests/
│
├── frontend/                   # React + Vite service
│   ├── Dockerfile              # Multi-stage: Node build → nginx serve
│   ├── nginx.conf              # API proxy config (not Railway-specific)
│   ├── package.json
│   ├── vite.config.ts
│   ├── .env.example
│   ├── src/                    # From UCT-Benchmark-DMR/combined/frontend/src/
│   └── public/
│
├── docker-compose.yml          # Local dev: backend + frontend + postgres
├── docker-compose.prod.yml     # Production: same but with resource limits
├── .env.example                # Root-level env template
├── README.md                   # Setup instructions
└── docs/
```

**Why this structure:**
- **Docker:** `docker compose up` runs everything locally
- **Bare metal:** Run backend with `uvicorn`, frontend with `nginx`/`serve`
- **Kubernetes:** Each directory → Deployment + Service + Ingress
- **Air-gapped:** `docker save` both images, transfer, `docker load`
- **Any PaaS:** Point each service at its Dockerfile

**Implementation Steps:**
1. Create `backend/` directory, merge `combined-new/backend_api/` + `combined-new/uct_benchmark/` into it
2. Create `frontend/` directory, move `UCT-Benchmark-DMR/combined/frontend/src/` into it
3. Update Dockerfiles to remove Railway-specific configs (use standard ENV vars)
4. Create `docker-compose.yml` with backend/frontend/postgres services
5. Create `.env.example` documenting all required env vars
6. Update nginx.conf to proxy `/api/v1` to backend service
7. Update frontend `vite.config.ts` proxy for local dev
8. Delete `combined-new/`, `frontend-deploy/`, old nested structure
9. Commit everything to git

**nginx.conf (platform-agnostic):**
```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # API proxy - backend host configurable via env
    location /api/ {
        proxy_pass http://${BACKEND_HOST:-backend}:${BACKEND_PORT:-8000};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**docker-compose.yml:**
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - BACKEND_HOST=backend
      - BACKEND_PORT=8000
    depends_on: [backend]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: uct_benchmark
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-localdev}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

volumes:
  pgdata:
```

---

### Fix #1: Dataset Download 500 Error (P0 CRITICAL)

**Root Cause:** The download endpoint at `datasets.py:664-671` runs:
```sql
SELECT o.*, dso.assigned_track_id, dso.assigned_object_id
FROM observations o
JOIN dataset_observations dso ON o.id = dso.observation_id
WHERE dso.dataset_id = ?
```
This fails because `SELECT o.*` expands ALL columns from `observations`, and when combined with `dso.assigned_track_id` and `dso.assigned_object_id`, there may be:
- Column name collisions (both tables might have an `id` column)
- The `dataset_observations` table might be empty for these datasets (INNER JOIN returns 0 rows, but the error is 500 not empty)
- DuckDB/PostgreSQL type conversion issues with datetime columns during JSON serialization

**Fix Plan:**

**File:** `combined-new/backend_api/routers/datasets.py` lines 664-708

1. Replace `SELECT o.*` with explicit column list to avoid collisions:
```python
obs_result = db.execute(
    """
    SELECT o.id, o.sat_no, o.ob_time, o.ra, o.declination,
           o.range_km, o.range_rate_km_s, o.azimuth, o.elevation,
           o.sensor_name, o.data_mode, o.track_id,
           dso.assigned_track_id, dso.assigned_object_id
    FROM observations o
    JOIN dataset_observations dso ON o.id = dso.observation_id
    WHERE dso.dataset_id = ?
    ORDER BY o.ob_time
    """,
    (id_int,),
)
```

2. Add LEFT JOIN instead of INNER JOIN so datasets with no linked observations still return (with nulls):
```python
LEFT JOIN dataset_observations dso ON o.id = dso.observation_id
```

3. Wrap the entire download handler in a try/except that returns a proper JSON error instead of plain text 500:
```python
except Exception as e:
    logger.error(f"Download failed for dataset {dataset_id}: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to prepare download: {str(e)}")
```

4. Add fallback path: if `dataset_observations` has no rows, fall back to direct observations query using the dataset's `observation_count` and `created_at` to identify the right observations.

**Verification:** `curl GET /api/v1/datasets/72/download` should return JSON file with `Content-Disposition: attachment`.

---

### Fix #2: Results Page "Not Found" for Valid Data (P1)

**Root Cause Analysis:**

The frontend `ResultsPage.tsx:108` shows "Not Found" when `resultsError || !results`. The `useResults` hook (`useSubmissions.ts:185-193`) calls `api.getResults(submissionId)` which hits `GET /results/{submissionId}/`.

The API at `results.py:91` returns data successfully (confirmed by curl). The failure is in the frontend transform. Looking at `transformResults()` (line 95-126):

```typescript
satelliteResults: data.satellite_results.map((sr) => ({...}))
```

If `data.satellite_results` is `null` (which it is — the backend returns `"satellite_results": []` but the raw_results processing may return null), calling `.map()` on null/undefined throws an error. This unhandled error causes React Query to set `resultsError`, which triggers the "Not Found" UI.

**Fix Plan:**

**File:** `UCT-Benchmark-DMR/combined/frontend/src/hooks/useSubmissions.ts` line 111

1. Add null-safe access to `satellite_results`:
```typescript
satelliteResults: (data.satellite_results || []).map((sr) => ({
    satelliteId: sr.satellite_id,
    status: sr.status as 'TP' | 'FP' | 'FN',
    observationsUsed: sr.observations_used,
    totalObservations: sr.total_observations,
    positionErrorKm: sr.position_error_km,
    velocityErrorKmS: sr.velocity_error_km_s,
    confidence: sr.confidence,
})),
```

2. Also null-guard the numeric fields that could be null from the LEFT JOIN:
```typescript
truePositives: data.true_positives ?? 0,
falsePositives: data.false_positives ?? 0,
falseNegatives: data.false_negatives ?? 0,
precision: data.precision ?? 0,
recall: data.recall ?? 0,
f1Score: data.f1_score ?? 0,
positionRmsKm: data.position_rms_km ?? 0,
velocityRmsKmS: data.velocity_rms_km_s ?? 0,
```

3. In `ResultsPage.tsx`, add a more helpful error state that distinguishes between "not found" and "error loading":
```typescript
if (resultsError) {
    return <ErrorCard message="Failed to load results" retry={() => refetch()} />;
}
if (!results) {
    return <NotFoundCard message="Results not available yet" />;
}
```

**Verification:** Navigate to `/results/3` and confirm all 4 tabs render with data (even if all metrics are 0.0).

---

### Fix #3: Server File Paths Leaked (P1 SECURITY)

**Root Cause:** `submissions.py:143` returns raw `file_path` from database which contains full Windows path like `C:\Users\kelvi\Desktop\DMR\...`.

**Fix Plan:**

**File:** `combined-new/backend_api/routers/submissions.py` line 143

1. Strip file_path to just the filename:
```python
from pathlib import Path

raw_path = row_dict.get("file_path")
safe_path = Path(raw_path).name if raw_path else None
# Returns just "abc123.json" instead of "C:\Users\kelvi\...\abc123.json"
```

2. Apply same fix in `results.py` export endpoint where `file_path` appears in the export response.

3. Also apply in the `SubmissionDetail` model - add a validator:
```python
@field_validator('file_path', mode='before')
@classmethod
def strip_file_path(cls, v):
    if v and ('/' in v or '\\' in v):
        return Path(v).name
    return v
```

**Verification:** `curl GET /api/v1/submissions/3` should show `file_path: "abc123.json"` not full path.

---

### Fix #4: Per-User UDL/ESA Key Enforcement (P1 - USER REQUEST)

**Current State:** The system already supports per-user keys in `workers.py:91-128`:
1. Try user's tokens from `profiles` table
2. Fall back to server-wide env vars (`UDL_TOKEN`, `ESA_TOKEN`)

The problem: the fallback means everyone can use Kelvin's personal key.

**Fix Plan:**

**A. Backend Changes:**

**File:** `combined-new/backend_api/jobs/workers.py` lines 118-128

1. Remove env var fallback for dataset generation (keep only for admin/satellite scraping):
```python
# REMOVE these lines from run_dataset_generation():
# if not udl_token:
#     udl_token = os.getenv("UDL_TOKEN")
# if not esa_token:
#     esa_token = os.getenv("ESA_TOKEN")

# REPLACE with clear error:
if not udl_token or not esa_token:
    missing = []
    if not udl_token: missing.append("UDL")
    if not esa_token: missing.append("ESA")
    raise ValueError(
        f"Missing API tokens: {', '.join(missing)}. "
        f"Please add your API tokens in Profile Settings > Data Source API Tokens."
    )
```

2. Ensure the error message propagates to the job status so users can see it:
```python
# In the except block of run_dataset_generation:
job.fail(str(e))  # This already happens - verify error is visible in UI
```

**File:** `combined-new/backend_api/routers/datasets.py`

3. Add a pre-check before submitting generation job — verify user has tokens:
```python
@router.post("/")
async def create_dataset(config, user=Depends(get_current_user), db=Depends(get_db)):
    # Check user has API tokens configured
    profile = db.execute(
        "SELECT udl_token, esa_token FROM profiles WHERE id = ?",
        (user.id,)
    ).fetchone()

    if not profile or not profile[0] or not profile[1]:
        raise HTTPException(
            status_code=400,
            detail="API tokens required. Please configure your UDL and ESA tokens in Profile Settings before generating datasets."
        )
    # ... proceed with generation
```

**B. Frontend Changes:**

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/DatasetGeneratorPage.tsx`

4. Before starting generation, check if user has tokens via profile API. Show a banner if missing:
```tsx
const { data: profile } = useProfile();
const hasTokens = profile?.udlToken && profile?.esaToken;

// At top of wizard:
{!hasTokens && (
    <Alert variant="warning">
        <AlertTitle>API Tokens Required</AlertTitle>
        <AlertDescription>
            You need to configure your UDL and ESA API tokens before generating datasets.
            <Link to="/profile">Go to Profile Settings</Link>
        </AlertDescription>
    </Alert>
)}
```

5. Disable the "Generate Dataset" button if tokens are missing.

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/ProfilePage.tsx`

6. Add validation feedback when tokens are saved — show a green checkmark or "Token saved" toast.

**C. Keep env var fallback ONLY for:**
- `scrape_satellite_data.py` (admin-only operation)
- Health checks
- Any background admin tasks

**Verification:** Create a new user account → try to generate dataset without tokens → should see clear error. Add tokens in profile → generation should work.

---

### Fix #5: Submit Form Validation Feedback (P2)

**Root Cause:** `SubmitPage.tsx` relies on a disabled button (`canSubmit` check) with no visual feedback explaining WHY it's disabled.

**Fix Plan:**

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/SubmitPage.tsx`

1. Add state tracking for attempted submission:
```typescript
const [submitAttempted, setSubmitAttempted] = useState(false);
```

2. On "Submit for Evaluation" click, if form is invalid, set `submitAttempted = true` and show inline errors:
```typescript
const handleSubmitClick = () => {
    setSubmitAttempted(true);
    if (!canSubmit) return; // Don't proceed
    // ... actual submit logic
};
```

3. Add inline error messages below each required field:
```tsx
{submitAttempted && !file && (
    <p className="text-sm text-red-500 mt-1">Please upload a submission file</p>
)}
{submitAttempted && !datasetId && (
    <p className="text-sm text-red-500 mt-1">Please select a target dataset</p>
)}
{submitAttempted && !algorithmName && (
    <p className="text-sm text-red-500 mt-1">Algorithm name is required</p>
)}
{submitAttempted && !version && (
    <p className="text-sm text-red-500 mt-1">Version is required</p>
)}
```

4. Add red border styling to empty required fields when `submitAttempted` is true:
```tsx
<Input
    className={cn(submitAttempted && !algorithmName && "border-red-500")}
    ...
/>
```

**Verification:** Click "Submit for Evaluation" with empty form → see red error messages under each required field.

---

### Fix #6: Delete Confirmation Dialog (P2)

**Finding from code review:** The confirmation dialog code ALREADY EXISTS in `MyDatasetsPage.tsx:244-274`. The issue is likely one of:
- The Dialog component isn't rendering due to a state bug
- The delete button click handler isn't setting `datasetToDelete`

**Fix Plan:**

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/MyDatasetsPage.tsx`

1. Verify the delete button's `onClick` handler calls `handleDeleteClick(dataset)`:
```tsx
<Button variant="ghost" size="icon" onClick={() => handleDeleteClick(dataset)}>
    <Trash2 className="h-4 w-4 text-red-500" />
</Button>
```

2. Verify the Dialog is rendered at the component root level (not inside a conditional that might prevent rendering).

3. If the dialog code doesn't exist in the deployed version, add it:
```tsx
<AlertDialog open={!!datasetToDelete} onOpenChange={() => setDatasetToDelete(null)}>
    <AlertDialogContent>
        <AlertDialogHeader>
            <AlertDialogTitle>Delete Dataset</AlertDialogTitle>
            <AlertDialogDescription>
                Are you sure you want to delete "{datasetToDelete?.name}"?
                This action cannot be undone.
            </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600">
                Delete
            </AlertDialogAction>
        </AlertDialogFooter>
    </AlertDialogContent>
</AlertDialog>
```

**Verification:** Click delete icon on My Datasets → confirmation dialog appears → Cancel works → Delete works.

---

### Fix #7: Dashboard TOP RANK Stuck on "Loading..." (P2)

**Root Cause:** `useDashboardStats.ts:59-63` uses `Promise.all()` for 3 API calls. If ANY fails, the entire query fails and stays in loading state because there's no error handling in the component.

**Fix Plan:**

**File:** `UCT-Benchmark-DMR/combined/frontend/src/hooks/useDashboardStats.ts`

1. Replace `Promise.all()` with `Promise.allSettled()` so partial failures don't block everything:
```typescript
const [leaderboardResult, statsResult, submissionsResult] = await Promise.allSettled([
    api.getLeaderboard({ limit: '10' }),
    api.getLeaderboardStatistics({}),
    api.getSubmissions({ limit: '100' }),
]);

const leaderboard = leaderboardResult.status === 'fulfilled'
    ? leaderboardResult.value.data : { entries: [] };
const stats = statsResult.status === 'fulfilled'
    ? statsResult.value.data : {};
const submissions = submissionsResult.status === 'fulfilled'
    ? submissionsResult.value.data : [];
```

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/DashboardPage.tsx`

2. Show "N/A" or "—" for TOP RANK when data is unavailable instead of "Loading...":
```typescript
const rankDisplay = stats?.topRank ? `#${stats.topRank}` : '—';
const rankSubtext = stats?.topRank ? stats.topAlgorithmName : 'No submissions yet';
```

3. Add error state display:
```tsx
{error && (
    <p className="text-xs text-yellow-500">Some data may be unavailable</p>
)}
```

**Verification:** Dashboard loads with all stat cards showing values (even "—" for no data).

---

### Fix #8: Implement 3 Missing API Endpoints (P2)

**8a. GET /api/v1/datasets/config**

**File:** `combined-new/backend_api/routers/datasets.py`

Must be defined BEFORE the `/{dataset_id}` route so it doesn't get caught by the ID parameter:

```python
@router.get("/config")
async def get_datasets_config():
    """Return dataset generation configuration (coverage thresholds, etc.)."""
    return {
        "coverage_thresholds": {
            "high": 0.05,
            "standard_min": 0.0005,
            "standard_max": 0.05,
            "low": 0.0005,
        },
        "orbital_regimes": ["LEO", "MEO", "GEO", "HEO"],
        "data_tiers": ["T1", "T2", "T3", "T4"],
        "max_objects": 200,
        "max_fitspan_days": 14,
        "max_date_range_days": 90,
    }
```

**8b. GET /api/v1/datasets/{id}/versions**

```python
@router.get("/{dataset_id}/versions")
async def get_dataset_versions(dataset_id: str, db=Depends(get_db)):
    """Return version history for a dataset (datasets with same base name)."""
    id_int = int(dataset_id)
    dataset = db.execute("SELECT name FROM datasets WHERE id = ?", (id_int,)).fetchone()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Find datasets with similar names (same base name pattern)
    base_name = dataset[0].rsplit('-', 1)[0]  # Strip timestamp suffix
    versions = db.execute(
        "SELECT id, name, status, created_at, observation_count FROM datasets WHERE name LIKE ? ORDER BY created_at DESC",
        (f"{base_name}%",)
    ).fetchall()

    return {
        "dataset_id": id_int,
        "versions": [{"id": v[0], "name": v[1], "status": v[2], "created_at": str(v[3]), "observation_count": v[4]} for v in versions]
    }
```

**8c. GET /api/v1/results/{id}/report**

```python
@router.get("/{submission_id}/report")
async def get_result_report(submission_id: str, format: str = "json", db=Depends(get_db)):
    """Generate an evaluation report for a submission."""
    # Reuse the existing results data
    results = await get_full_results(submission_id, db=db)

    if format == "json":
        return results  # Return as JSON
    else:
        raise HTTPException(status_code=400, detail=f"Format '{format}' not yet supported. Use 'json'.")
```

**Verification:** All 3 endpoints return 200 with proper data.

---

### Fix #9: Add Missing Security Headers (P3)

**File:** `combined-new/backend_api/middleware/logging.py` lines 94-105

The code already adds HSTS conditionally for HTTPS. The issue is it checks `request.url.scheme == "https"` which may not be true behind Railway's reverse proxy.

**Fix:**
```python
# Always add HSTS in production (Railway terminates TLS at proxy)
environment = os.getenv("RAILWAY_ENVIRONMENT", "development")
if environment == "production":
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

# Add CSP and Permissions-Policy
response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
```

---

### Fix #10: Clean Up track_id="nan" (P3)

**Fix:** Run a one-time SQL migration:
```sql
UPDATE observations SET track_id = NULL WHERE track_id = 'nan';
```

Add to a migration script or run via the database manager. The worker code at `workers.py:313` already has `pd.isna()` check, so new data won't have this issue.

---

### Fix #11: Leaderboard dataset_id/name Null (P3)

**Root Cause:** `leaderboard.py:116` returns the query parameter `dataset_id` (which is None when not provided) instead of the actual dataset_id from the query results.

**File:** `combined-new/backend_api/routers/leaderboard.py`

**Fix:** Extract dataset info from the query results:
```python
# After building entries list:
if entries:
    actual_dataset_id = entries[0].get("dataset_id")  # From query results
    ds_result = db.execute("SELECT name FROM datasets WHERE id = ?", (actual_dataset_id,)).fetchone()
    dataset_name = ds_result[0] if ds_result else "Unknown"
else:
    actual_dataset_id = dataset_id
    dataset_name = None

return LeaderboardResponse(
    dataset_id=actual_dataset_id,  # Use actual value, not query param
    dataset_name=dataset_name,
    ...
)
```

---

### Fix #12: Clean Up Failed Datasets (P3)

**Options:**
- A) Delete failed datasets: `DELETE FROM datasets WHERE status = 'failed'`
- B) Add a `hidden` column and filter them out of list endpoints
- C) Add a status filter to the frontend (already exists but shows all by default)

**Recommended: Option A** — delete the 11 failed datasets that have 0 observations and serve no purpose. They're test failures from development.

---

### Fix #13: Satellites Array Empty Despite Count=8 (P3)

**Root Cause:** The dataset detail endpoint at `datasets.py` returns `satellites: []` because the query doesn't join the satellites table.

**Fix:** In `get_dataset()`, add a query to populate the satellites array:
```python
# After getting dataset details, fetch associated satellites
sat_result = db.execute(
    """
    SELECT DISTINCT o.sat_no, s.name
    FROM observations o
    JOIN dataset_observations dso ON o.id = dso.observation_id
    LEFT JOIN satellites s ON o.sat_no = s.sat_no
    WHERE dso.dataset_id = ?
    """,
    (id_int,)
).fetchall()

satellites = [{"sat_no": r[0], "name": r[1]} for r in sat_result]
```

---

### Fix #14: Download Error Silent Failure (P3)

**File:** `UCT-Benchmark-DMR/combined/frontend/src/pages/DatasetBrowserPage.tsx`

Add error toast on download failure:
```typescript
const handleDownload = async (datasetId: string) => {
    try {
        const blob = await api.downloadDataset(datasetId);
        // ... download logic
    } catch (error) {
        toast({
            title: 'Download failed',
            description: 'Unable to download dataset. The server may be experiencing issues.',
            variant: 'destructive',
        });
    }
};
```

---

## Implementation Order

| Phase | Fixes | Effort | Impact |
|-------|-------|--------|--------|
| **Phase 0: Foundation** | #0 (consolidate codebase into backend/ + frontend/) | ~2 hours | Everything else depends on this |
| **Phase 1: Critical Bugs** | #1 (download 500), #2 (results page), #3 (file path leak) | ~2 hours | Unblocks core workflows |
| **Phase 2: User Keys** | #4 (per-user key enforcement, remove shared key) | ~1 hour | Addresses key sharing concern |
| **Phase 3: UX Polish** | #5 (validation), #6 (delete dialog), #7 (dashboard loading), #14 (download toast) | ~1.5 hours | Professional UX |
| **Phase 4: API Gaps** | #8 (3 missing endpoints), #11 (leaderboard null) | ~1 hour | API completeness |
| **Phase 5: Cleanup** | #9 (security headers), #10 (nan cleanup), #12 (delete failed datasets), #13 (satellites) | ~30 min | Data quality |

**Total estimated effort: ~8 hours**

---

## UDL/ESA Key Architecture (Final Design)

**Current state:** Per-user keys exist in `profiles` table. `workers.py` resolves: user profile first → env var fallback.

**Problem:** The fallback means your personal key is used for everyone.

**New design:**
```
Token Resolution (user-facing operations like dataset generation):
  1. Load tokens from profiles table for the requesting user
  2. If missing → FAIL with clear error message
  3. No env var fallback for normal users

Token Resolution (admin operations like satellite scraping):
  1. Check if user has role=admin
  2. If admin → can use ADMIN_UDL_TOKEN / ADMIN_ESA_TOKEN from env
  3. If not admin → same as user-facing (must have own tokens)
```

**Env var naming change:**
- `UDL_TOKEN` / `ESA_TOKEN` → REMOVE (too easy to accidentally use)
- `ADMIN_UDL_TOKEN` / `ADMIN_ESA_TOKEN` → NEW (explicit admin-only)

**Frontend UX:**
- Generator wizard shows warning banner if tokens not configured
- "Generate Dataset" button disabled without tokens
- Profile page shows clear status: "Token configured" or "Not configured"
- Error messages link directly to Profile Settings page
