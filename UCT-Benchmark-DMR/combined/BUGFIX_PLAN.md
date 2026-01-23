# Bug Fix Implementation Plan

This document outlines the detailed plan to fix the top 5 functional bugs identified in the code review.

---

## Bug #1: Race Condition in Dataset Name Uniqueness

**Location**: `backend_api/routers/datasets.py:265-282`

**Problem**: The check-then-insert pattern allows two concurrent requests to both pass the uniqueness check and create duplicate dataset names.

**Current Code**:
```python
existing = db.execute(
    "SELECT COUNT(*) FROM datasets WHERE name = ?", (request.name,)
).fetchone()[0]

dataset_name = request.name
if existing > 0:
    counter = 2
    while True:
        candidate_name = f"{request.name}-{counter}"
        exists = db.execute(...).fetchone()[0]
        if exists == 0:
            dataset_name = candidate_name
            break
        counter += 1
```

**Solution**:
1. Add a UNIQUE constraint on the `name` column in the `datasets` table
2. Use INSERT with conflict handling (UPSERT pattern) or catch the constraint violation
3. Generate unique names using timestamp + random suffix instead of sequential counter

**Implementation Steps**:

### Step 1.1: Add database migration for UNIQUE constraint
File: `uct_benchmark/database/schema.py`
- Add `UNIQUE` constraint to `name` column in `datasets` table
- Or add migration that runs: `CREATE UNIQUE INDEX IF NOT EXISTS idx_datasets_name ON datasets(name)`

### Step 1.2: Update dataset creation logic
File: `backend_api/routers/datasets.py`
```python
import uuid
from datetime import datetime

# Generate unique name upfront using timestamp + short UUID
timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
unique_suffix = str(uuid.uuid4())[:8]
dataset_name = f"{request.name}-{timestamp}-{unique_suffix}"

try:
    result = db.execute(
        """INSERT INTO datasets (...) VALUES (...) RETURNING id""",
        (dataset_name, ...)
    )
    dataset_id = result.fetchone()[0]
except Exception as e:
    if "UNIQUE constraint" in str(e) or "duplicate" in str(e).lower():
        raise HTTPException(status_code=409, detail="Dataset name conflict, please retry")
    raise
```

### Step 1.3: Add test case
File: `backend_api/tests/test_datasets.py`
- Add concurrent request test using `asyncio.gather()` or threading

---

## Bug #2: Unhandled Integer Parsing for Dataset IDs

**Location**: `backend_api/routers/datasets.py` - lines 130, 359, 444, 507, 539, 581

**Problem**: `int(dataset_id)` raises `ValueError` for non-numeric strings, causing 500 errors.

**Current Code**:
```python
result = db.execute(
    "SELECT * FROM datasets WHERE id = ?",
    (int(dataset_id),)  # Crashes if dataset_id = "abc"
)
```

**Solution**: Create a reusable validation function or use Pydantic path parameter validation.

**Implementation Steps**:

### Step 2.1: Create validation helper
File: `backend_api/routers/datasets.py` (top of file)
```python
def validate_dataset_id(dataset_id: str) -> int:
    """Validate and convert dataset_id to integer."""
    try:
        id_int = int(dataset_id)
        if id_int <= 0:
            raise HTTPException(status_code=400, detail="Dataset ID must be a positive integer")
        return id_int
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dataset ID: '{dataset_id}' is not a valid integer")
```

### Step 2.2: Update all endpoints
Replace all `int(dataset_id)` calls with `validate_dataset_id(dataset_id)`:

```python
@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(dataset_id: str, db: DatabaseManager = Depends(get_db)):
    id_int = validate_dataset_id(dataset_id)
    result = db.execute("SELECT * FROM datasets WHERE id = ?", (id_int,))
    # ...
```

**Affected endpoints**:
- `get_dataset` (line 130)
- `get_dataset_observations` (line 359)
- `link_observations` (line 444)
- `update_dataset_coverage` (line 507)
- `delete_dataset` (line 539)
- `download_dataset` (line 581)

### Step 2.3: Alternative - Use Pydantic with Path validation
```python
from fastapi import Path

@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    dataset_id: int = Path(..., gt=0, description="Dataset ID"),
    db: DatabaseManager = Depends(get_db),
):
    # dataset_id is already validated and converted to int
```

### Step 2.4: Add test cases
```python
def test_get_dataset_invalid_id():
    response = client.get("/api/v1/datasets/abc")
    assert response.status_code == 400  # Not 500

def test_get_dataset_negative_id():
    response = client.get("/api/v1/datasets/-1")
    assert response.status_code == 400
```

---

## Bug #3: Silent Error Swallowing in Failure Handling

**Location**: `backend_api/jobs/workers.py:278-286`

**Problem**: If the database update fails when marking a dataset as "failed", the exception is silently swallowed. The dataset remains stuck in "generating" state.

**Current Code**:
```python
except Exception as e:
    error_msg = f"{type(e).__name__}: {str(e)}"
    logger.error(f"Dataset generation failed for job {job_id}: {error_msg}")

    try:
        from backend_api.database import get_db
        db = get_db()
        db.execute(
            "UPDATE datasets SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (dataset_id,),
        )
    except Exception:
        pass  # <-- PROBLEM: Silent swallow

    job_manager.fail_job(job_id, error_msg)
```

**Solution**: Log the secondary failure and include it in the job error message.

**Implementation Steps**:

### Step 3.1: Update error handling
File: `backend_api/jobs/workers.py`
```python
except Exception as e:
    error_msg = f"{type(e).__name__}: {str(e)}"
    logger.error(f"Dataset generation failed for job {job_id}: {error_msg}")
    logger.debug(traceback.format_exc())

    # Try to update dataset status to failed
    db_update_failed = False
    try:
        from backend_api.database import get_db
        db = get_db()
        db.execute(
            "UPDATE datasets SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (dataset_id,),
        )
    except Exception as db_error:
        db_update_failed = True
        logger.error(f"CRITICAL: Failed to mark dataset {dataset_id} as failed: {db_error}")
        # Append to error message so it's visible in job status
        error_msg = f"{error_msg} [Additionally, failed to update dataset status: {db_error}]"

    job_manager.fail_job(job_id, error_msg)
```

### Step 3.2: Add retry mechanism (optional enhancement)
```python
import time

def update_dataset_status_with_retry(db, dataset_id: int, status: str, max_retries: int = 3):
    """Update dataset status with retry logic."""
    for attempt in range(max_retries):
        try:
            db.execute(
                "UPDATE datasets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, dataset_id),
            )
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} to update dataset status failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
    return False
```

### Step 3.3: Apply same fix to evaluation pipeline
The same issue exists in `run_evaluation_pipeline` at lines 440-448.

---

## Bug #4: No Transaction Wrapping on Dataset Creation

**Location**: `backend_api/routers/datasets.py:288-319`

**Problem**: Dataset creation involves multiple database operations:
1. INSERT into datasets
2. UPDATE datasets with job_id

If step 2 fails, we have a dataset record without proper job linkage.

**Current Code**:
```python
# Step 1: Insert
result = db.execute("""INSERT INTO datasets (...) RETURNING id""", (...))
dataset_id = result.fetchone()[0]

# Step 2: Submit job
job = submit_dataset_generation(dataset_id, generation_params)

# Step 3: Update with job_id (could fail!)
db.execute("""UPDATE datasets SET generation_params = ? WHERE id = ?""",
    (json.dumps({**generation_params, "job_id": job.id}), dataset_id))
```

**Solution**: Wrap in explicit transaction with rollback on failure.

**Implementation Steps**:

### Step 4.1: Add transaction support to DatabaseManager
File: `uct_benchmark/database/connection.py`
```python
from contextlib import contextmanager

@contextmanager
def transaction(self):
    """Context manager for explicit transactions."""
    conn = self._get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
```

### Step 4.2: Update dataset creation endpoint
File: `backend_api/routers/datasets.py`
```python
@router.post("/", response_model=DatasetSummary)
async def create_dataset(
    request: DatasetCreate,
    db: DatabaseManager = Depends(get_db),
):
    # ... validation and name generation ...

    try:
        # Start transaction
        db.execute("BEGIN TRANSACTION")

        # Create dataset record
        result = db.execute(
            """INSERT INTO datasets (...) VALUES (...) RETURNING id""",
            (dataset_name, ...)
        )
        dataset_id = result.fetchone()[0]

        # Submit background job
        job = submit_dataset_generation(dataset_id, generation_params)

        # Update dataset with job_id
        db.execute(
            """UPDATE datasets SET generation_params = ? WHERE id = ?""",
            (json.dumps({**generation_params, "job_id": job.id}), dataset_id)
        )

        # Commit transaction
        db.execute("COMMIT")

    except Exception as e:
        db.execute("ROLLBACK")
        logger.error(f"Failed to create dataset: {e}")
        raise HTTPException(status_code=500, detail="Failed to create dataset")

    return DatasetSummary(...)
```

### Step 4.3: Consider job cancellation on rollback
If the transaction fails after job submission, we should cancel the job:
```python
except Exception as e:
    db.execute("ROLLBACK")
    # Cancel the submitted job if it exists
    if 'job' in locals():
        try:
            job_manager.cancel_job(job.id)
        except Exception:
            logger.warning(f"Could not cancel orphaned job {job.id}")
    raise HTTPException(status_code=500, detail="Failed to create dataset")
```

---

## Bug #5: Auto-Linking "Repair" Logic Indicates Root Bug

**Location**: `backend_api/routers/datasets.py:368-388`

**Problem**: The auto-linking code is a symptom that dataset creation doesn't properly link observations. The "repair" logic links the most recent N observations, which may be wrong if multiple datasets are created.

**Current Code**:
```python
if existing_links == 0 and total_count > 0:
    # Get the most recent observations and link them
    logger.info(f"Auto-linking {total_count} observations for dataset {dataset_id}")
    obs_result = db.execute(
        "SELECT id FROM observations ORDER BY created_at DESC LIMIT ?",
        (total_count,)
    )
    obs_ids = [row[0] for row in obs_result.fetchall()]
```

**Root Cause**: The `generateDataset` function in `apiIntegration.py` stores observations but the linking to dataset happens in `workers.py` - and it may fail silently or link wrong observations.

**Solution**: Fix the root cause by ensuring observations are properly linked during generation, and remove the auto-linking repair code.

**Implementation Steps**:

### Step 5.1: Audit observation linking in workers.py
File: `backend_api/jobs/workers.py:241-252`
```python
# Current code - check if this is actually working
if obs_truth is not None and not obs_truth.empty and 'id' in obs_truth.columns:
    obs_ids = obs_truth['id'].tolist()
    # ...
    try:
        db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)
    except Exception as e:
        logger.warning(f"Failed to link observations to dataset: {e}")  # <-- Warning not error!
```

**Issue Found**: The linking failure is logged as warning and continues. If this fails, dataset shows observations but they're not linked.

### Step 5.2: Make observation linking failure critical
```python
# Change from warning to error that fails the job
if obs_truth is not None and not obs_truth.empty and 'id' in obs_truth.columns:
    obs_ids = obs_truth['id'].tolist()
    track_assignments = {}
    if 'trackId' in obs_truth.columns:
        track_assignments = {
            row['id']: row.get('trackId') for _, row in obs_truth.iterrows()
        }

    # Make this a required step - fail if it doesn't work
    db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)
    logger.info(f"Linked {len(obs_ids)} observations to dataset {dataset_id}")
    # Remove try/except - let it propagate and fail the job
```

### Step 5.3: Remove auto-linking repair code
File: `backend_api/routers/datasets.py`
```python
# DELETE this entire block (lines 368-388):
# if existing_links == 0 and total_count > 0:
#     # Get the most recent observations and link them
#     ...
```

### Step 5.4: Add validation check instead
```python
@router.get("/{dataset_id}/observations")
async def get_dataset_observations(...):
    # ...

    # Check for data integrity issue
    if existing_links == 0 and total_count > 0:
        logger.error(f"Data integrity issue: Dataset {dataset_id} has observation_count={total_count} but no linked observations")
        raise HTTPException(
            status_code=500,
            detail="Dataset has corrupted observation links. Please regenerate the dataset."
        )

    # ... rest of function
```

### Step 5.5: Add database constraint (optional)
Consider adding a trigger or constraint that ensures `observation_count` matches actual linked observations count.

---

## Implementation Order

Recommended order based on impact and dependencies:

1. **Bug #2** (Integer validation) - Quick win, no dependencies
2. **Bug #3** (Silent error swallowing) - Quick win, improves debugging
3. **Bug #5** (Auto-linking root cause) - Fixes data integrity
4. **Bug #4** (Transaction wrapping) - Requires Bug #5 first
5. **Bug #1** (Race condition) - Requires schema change, test carefully

---

## Testing Checklist

- [ ] Bug #1: Concurrent dataset creation test
- [ ] Bug #2: Invalid ID returns 400, not 500
- [ ] Bug #3: Failed job shows detailed error message
- [ ] Bug #4: Partial failure rolls back cleanly
- [ ] Bug #5: Observations always link correctly
- [ ] Regression: Existing functionality still works

---

## Estimated Effort

| Bug | Complexity | Time Estimate |
|-----|------------|---------------|
| #1 | Medium | 2-3 hours |
| #2 | Low | 30 minutes |
| #3 | Low | 30 minutes |
| #4 | Medium | 1-2 hours |
| #5 | Medium | 1-2 hours |
| **Total** | | **5-8 hours** |
