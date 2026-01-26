# Implementation Plan: Downsampling and Simulation Integration

## Executive Summary

The downsampling and simulation modules are **substantially implemented** but **not yet integrated** into the main data pipeline. This plan outlines how to wire them into the API, backend workers, and UI without breaking existing functionality.

---

## Current State Analysis

### What Already Exists

| Component | Location | Status |
|-----------|----------|--------|
| Downsampling Core | `uct_benchmark/data/dataManipulation.py` | Implemented |
| Regime Detection | `dataManipulation.py:determine_orbital_regime()` | Implemented |
| Track Identification | `dataManipulation.py:identify_tracks()` | Implemented |
| Track-Preserving Thinning | `dataManipulation.py:thin_within_tracks()` | Implemented |
| Regime-Specific Profiles | `settings.py:DOWNSAMPLING_PROFILES` | Configured |
| Coverage Calculation | `dataManipulation.py:compute_arc_coverage()` | Implemented |
| Simulation Core | `uct_benchmark/simulation/simulateObservations.py` | Implemented |
| Gap Analysis | `simulateObservations.py:epochsToSim()` | Implemented |
| Atmospheric Refraction | `simulation/atmospheric.py` | Implemented |
| Velocity Aberration | `simulation/atmospheric.py` | Implemented |
| Sensor Noise Models | `simulation/noise_models.py` | Implemented |
| Config Dataclasses | `settings.py:DownsampleConfig, SimulationConfig` | Defined |
| Unit Tests | `tests/test_downsampling_enhancements.py` | 13 tests |
| Unit Tests | `tests/test_simulation_enhancements.py` | 11 tests |
| Validation Suite | `validation/run_validation.py` | Implemented |

### What Needs Integration

1. **`generateDataset()` in `apiIntegration.py`** - Does not call downsampling or simulation
2. **`run_dataset_generation()` in `workers.py`** - Does not pass config to pipeline
3. **API endpoints** - Don't expose downsampling/simulation options
4. **Frontend UI** - No controls for downsampling/simulation parameters
5. **Database schema** - Needs columns for `is_simulated`, `tier`, `downsample_config`

---

## Implementation Phases

### Phase 1: Core Pipeline Integration (Backend)

#### 1.1 Modify `apiIntegration.py:generateDataset()`

**File:** `uct_benchmark/api/apiIntegration.py`

**Changes:**
- Add optional `downsample_config: Optional[DownsampleConfig] = None` parameter
- Add optional `simulation_config: Optional[SimulationConfig] = None` parameter
- After pulling observations, call downsampling if config provided
- After downsampling, call simulation to fill gaps if config provided
- Flag simulated observations with `is_simulated=True` and `dataMode='SIMULATED'`
- Return metadata about downsampling/simulation applied

**Impact:** Low risk - new optional parameters, existing behavior unchanged

```python
def generateDataset(
    UDL_token, ESA_token, satIDs, timeframe, timeunit, dt=0.1, max_datapoints=0, end_time="now",
    use_database=False, db_path=None, dataset_name=None,
    # NEW PARAMETERS
    downsample_config: Optional[DownsampleConfig] = None,
    simulation_config: Optional[SimulationConfig] = None,
):
```

#### 1.2 Create Integration Helper Functions

**File:** `uct_benchmark/data/dataManipulation.py` (add new functions)

**New Functions:**
```python
def apply_downsampling(
    obs_df: pd.DataFrame,
    state_data: pd.DataFrame,
    elset_data: pd.DataFrame,
    config: DownsampleConfig
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Apply downsampling to observations with full config support."""

def apply_simulation_to_gaps(
    obs_df: pd.DataFrame,
    elset_data: pd.DataFrame,
    sensor_df: pd.DataFrame,
    config: SimulationConfig
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Generate synthetic observations to fill gaps."""
```

#### 1.3 Modify `workers.py:run_dataset_generation()`

**File:** `backend_api/jobs/workers.py`

**Changes:**
- Accept `downsample_config` and `simulation_config` in config dict
- Convert dict to dataclass instances
- Pass configs to `generateDataset()`
- Store applied config in job result

---

### Phase 2: API Endpoint Updates

#### 2.1 Update Dataset Generation Request Model

**File:** `backend_api/models/datasets.py` (or create if missing)

```python
class DownsampleOptions(BaseModel):
    enabled: bool = False
    tier: str = "T2"  # T1, T2, T3
    target_coverage: float = 0.05
    preserve_tracks: bool = True
    seed: Optional[int] = None

class SimulationOptions(BaseModel):
    enabled: bool = False
    fill_gaps: bool = True
    sensor_model: str = "GEODSS"
    apply_noise: bool = True
    seed: Optional[int] = None

class DatasetGenerateRequest(BaseModel):
    name: str
    regime: str  # LEO, MEO, GEO, HEO
    object_count: int = 10
    timeframe: int = 7
    satellites: Optional[List[int]] = None
    downsampling: Optional[DownsampleOptions] = None
    simulation: Optional[SimulationOptions] = None
```

#### 2.2 Update Dataset Router

**File:** `backend_api/routers/datasets.py`

**Changes:**
- Accept new request body fields
- Convert to config dataclasses
- Pass to worker

---

### Phase 3: Database Schema Updates

#### 3.1 Add Columns to `datasets` Table

**File:** `uct_benchmark/database/schema.py`

```sql
ALTER TABLE datasets ADD COLUMN tier VARCHAR(10);
ALTER TABLE datasets ADD COLUMN downsample_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE datasets ADD COLUMN simulation_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE datasets ADD COLUMN simulated_obs_count INTEGER DEFAULT 0;
ALTER TABLE datasets ADD COLUMN downsample_config JSON;
ALTER TABLE datasets ADD COLUMN simulation_config JSON;
```

#### 3.2 Add Column to `observations` Table

```sql
ALTER TABLE observations ADD COLUMN is_simulated BOOLEAN DEFAULT FALSE;
```

---

### Phase 4: Frontend Integration

#### 4.1 Add Downsampling Controls to Dataset Creation Form

**File:** `frontend/src/pages/CreateDatasetPage.tsx` (or similar)

**UI Elements:**
- Toggle: "Enable Downsampling"
- Dropdown: "Quality Tier" (T1 High, T2 Standard, T3 Low)
- Slider: "Target Coverage" (1% - 50%)
- Toggle: "Preserve Track Boundaries"

#### 4.2 Add Simulation Controls

**UI Elements:**
- Toggle: "Enable Gap Filling Simulation"
- Dropdown: "Sensor Model" (GEODSS, SBSS, Commercial)
- Toggle: "Apply Realistic Noise"

#### 4.3 Update API Client

**File:** `frontend/src/api/client.ts`

Add types and methods for new options.

---

### Phase 5: Testing Strategy

#### 5.1 Unit Tests

**New Test File:** `tests/test_pipeline_integration.py`

```python
class TestDownsamplingIntegration:
    """Test downsampling integration with generateDataset."""

    def test_generate_with_downsampling_config(self):
        """Verify downsampling is applied when config provided."""

    def test_generate_without_downsampling_unchanged(self):
        """Verify existing behavior unchanged when no config."""

    def test_regime_profiles_applied_correctly(self):
        """Verify correct profile used per regime."""

class TestSimulationIntegration:
    """Test simulation integration."""

    def test_generate_with_simulation_fills_gaps(self):
        """Verify gaps are filled with synthetic obs."""

    def test_simulated_obs_flagged_correctly(self):
        """Verify is_simulated=True on synthetic obs."""

    def test_simulation_respects_max_ratio(self):
        """Verify simulation doesn't exceed max_synthetic_ratio."""
```

#### 5.2 Integration Tests

**New Test File:** `backend_api/tests/test_dataset_pipeline.py`

```python
class TestDatasetGenerationEndpoint:
    """Test full pipeline through API."""

    def test_create_dataset_with_downsampling(self):
        """POST /datasets/generate with downsampling options."""

    def test_create_dataset_with_simulation(self):
        """POST /datasets/generate with simulation options."""

    def test_create_dataset_combined(self):
        """POST /datasets/generate with both options."""
```

#### 5.3 Regression Tests

**Ensure these existing tests still pass:**
- All tests in `test_downsampling_enhancements.py`
- All tests in `test_simulation_enhancements.py`
- All tests in `test_database.py`
- Validation suite: `python validation/run_validation.py`

---

## Implementation Order (Recommended)

| Step | Task | Files | Risk | Est. Effort |
|------|------|-------|------|-------------|
| 1 | Add helper functions in dataManipulation.py | 1 file | Low | 2-3 hours |
| 2 | Modify generateDataset() signature | 1 file | Low | 1-2 hours |
| 3 | Write unit tests for integration | 1 file | Low | 2-3 hours |
| 4 | Update workers.py to pass config | 1 file | Low | 1 hour |
| 5 | Update API request models | 1-2 files | Low | 1 hour |
| 6 | Update datasets router | 1 file | Low | 1 hour |
| 7 | Add database migrations | 1-2 files | Medium | 1-2 hours |
| 8 | Write integration tests | 1 file | Low | 2 hours |
| 9 | Update frontend forms | 2-3 files | Medium | 3-4 hours |
| 10 | Update frontend API client | 1 file | Low | 1 hour |
| 11 | End-to-end testing | - | Low | 2-3 hours |

**Total Estimated Effort:** 17-23 hours

---

## Risk Mitigation

### Breaking Change Prevention

1. **All new parameters are optional** - Existing code paths unaffected
2. **Feature flags** - Downsampling/simulation only run when explicitly enabled
3. **Backwards-compatible DB** - New columns have defaults
4. **Comprehensive tests** - Regression suite ensures no breakage

### Rollback Strategy

1. Each phase can be deployed independently
2. Config flags can disable features without code changes
3. Database migrations are additive only (no destructive changes)

---

## Success Criteria

1. **Unit tests pass:** All 24+ existing tests + new tests
2. **Integration tests pass:** API endpoints work correctly
3. **Validation suite passes:** `run_validation.py` returns PASS
4. **No regression:** Existing dataset generation works identically when options not provided
5. **UI functional:** Users can toggle options and see results

---

## Appendix: Key Code Locations

| Purpose | File Path | Line Reference |
|---------|-----------|----------------|
| Main downsampling | `uct_benchmark/data/dataManipulation.py` | `downsample_by_regime()` |
| Main simulation | `uct_benchmark/simulation/simulateObservations.py` | `simulateObs()` |
| Gap analysis | `uct_benchmark/simulation/simulateObservations.py` | `epochsToSim()` |
| Config classes | `uct_benchmark/settings.py` | `DownsampleConfig`, `SimulationConfig` |
| Dataset generation | `uct_benchmark/api/apiIntegration.py` | `generateDataset()` |
| Background worker | `backend_api/jobs/workers.py` | `run_dataset_generation()` |
| API router | `backend_api/routers/datasets.py` | `/generate` endpoint |
| Downsampling tests | `tests/test_downsampling_enhancements.py` | 13 tests |
| Simulation tests | `tests/test_simulation_enhancements.py` | 11 tests |
| Validation suite | `validation/run_validation.py` | Full pipeline test |
