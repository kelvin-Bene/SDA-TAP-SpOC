# UDL Query Reliability Change Log

Date: 2026-02-19
Scope: Stabilize dataset generation when `eoobservation` queries with `satNo` fail in some UDL tenant configurations.

## Why this change was needed
- `fast` and `hybrid` strategies use `satNo`-filtered `eoobservation` calls.
- In affected environments, `eoobservation + satNo` fails server-side (500/JWT-client-cert path) even when Basic auth token is valid.
- `windowed` strategy could also return empty if the `range` filter excludes available records.

## Change 1: Add satNo fallback path (fast/hybrid)
Reasoning:
- Preserve existing behavior where `satNo` works.
- Auto-fallback to `obTime`-only pull when satNo path fails or returns empty.
- Filter by requested satellites client-side to keep dataset semantics.

Changed file:
- `uct_benchmark/api/apiIntegration.py`

Snippet:
```python
# Some UDL tenants reject eoobservation+satNo queries even with valid Basic auth.
logger.warning(
    f"FAST satNo query path failed ({e}); falling back to obTime-only windowed query."
)
data = _fetch_observations_by_time_only(..., sat_ids=sat_ids, ...)
```

Snippet:
```python
if all_results:
    return pd.concat(all_results, ignore_index=True)

logger.warning(
    "HYBRID satNo query path returned no data; falling back to obTime-only windowed query."
)
return _fetch_observations_by_time_only(..., sat_ids=sat_ids, ...)
```

## Change 2: Add shared `obTime`-only window query helper
Reasoning:
- Centralize fallback logic in one implementation.
- Reuse for windowed strategy and satNo fallback behavior.
- Keep only requested satellites when doing broad time-window pulls.

Changed file:
- `uct_benchmark/api/apiIntegration.py`

Snippet:
```python
def _fetch_observations_by_time_only(..., sat_ids=None, ...):
    params = {
        "obTime": f"{datetimeToUDL(current_time)}..{datetimeToUDL(window_end)}",
        "uct": "false",
        "dataMode": "REAL",
    }
    ...
    sat_series = pd.to_numeric(window_data["satNo"], errors="coerce")
    window_data = window_data[sat_series.isin(sat_filter)]
```

## Change 3: Make `windowed` range filter optional
Reasoning:
- Some runs returned empty data when `range` filter was present.
- Allow disabling server-side range filtering to use pure `obTime` windows.

Changed file:
- `uct_benchmark/api/apiIntegration.py`

Snippet:
```python
if disable_range_filter:
    logger.info("Windowed strategy using obTime-only queries (range filter disabled).")
...
return _fetch_observations_by_time_only(..., range_filter=None if disable_range_filter else range_filter)
```

## Change 4: Add pipeline flags for compatibility behavior
Reasoning:
- Make behavior explicit/configurable per dataset request.
- Default to robust behavior for environments where satNo path is unstable.

Changed files:
- `backend_api/models/__init__.py`
- `backend_api/routers/datasets.py`
- `backend_api/jobs/workers.py`
- `frontend/src/hooks/useDatasets.ts`

Snippet:
```python
disable_range_filter: bool = Field(default=True, ...)
allow_satno_fallback: bool = Field(default=True, ...)
```

Snippet:
```python
generation_params["disable_range_filter"] = request.disable_range_filter
generation_params["allow_satno_fallback"] = request.allow_satno_fallback
```

Snippet:
```python
generateDataset(...,
    disable_range_filter=disable_range_filter,
    allow_satno_fallback=allow_satno_fallback,
)
```

Snippet:
```ts
backendConfig.disable_range_filter = true;
backendConfig.allow_satno_fallback = true;
```

## Change 5: Add tests for fallback behavior
Reasoning:
- Ensure strategy behavior is deterministic and regression-resistant.
- Verify model defaults for new compatibility flags.

Changed file:
- `tests/test_search_strategies.py`

Snippet:
```python
def test_fast_strategy_falls_back_when_satno_path_fails(...):
    mock_batch_query.side_effect = RuntimeError("All batch queries failed")
    ...
    mock_time_fallback.assert_called_once()
```

Snippet:
```python
def test_hybrid_strategy_falls_back_when_all_sat_queries_fail(...):
    mock_smart_query.side_effect = Exception("satNo path failure")
    ...
    mock_time_fallback.assert_called_once()
```

## Notes
- Existing logic is preserved by default; fallback only activates when satNo query path fails or returns empty.
- This is an API-compatibility hardening change, not a token/auth credential change.

## Change 6: Make ESA Discosweb enrichment non-fatal on 401
Reasoning:
- Dataset generation should not fail when optional ESA enrichment token is missing/placeholder/invalid.
- In affected runs, ESA returned 401 and failed whole job despite UDL data being available.

Changed files:
- `backend_api/jobs/workers.py`
- `uct_benchmark/api/apiIntegration.py`

Snippet:
```python
if esa_token and esa_token.strip().lower() in {"your_esa_api_token_here", ...}:
    logger.warning("ESA_TOKEN appears to be a placeholder value; disabling Discosweb enrichment")
    esa_token = None
```

Snippet:
```python
try:
    resp = discoswebQuery(ESA_token, params)
except requests.exceptions.HTTPError as e:
    logger.warning("Discosweb query failed ... continuing without enrichment.")
    state_truth_data["mass"] = 0
    state_truth_data["crossSection"] = 0
```
