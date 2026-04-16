# Documentation Update Plan

## Executive Summary

After reviewing all recent changes and comparing the two documentation locations (`UCT-Benchmark-DMR/combined/docs/` and `generated-docs/docs/`), I've identified **14 specific gaps** that need to be addressed. The documentation is approximately **80% up to date** but has critical gaps around the recent alignment work.

---

## Documentation Locations

The project has **two documentation locations**:

| Location | Purpose | Status |
|----------|---------|--------|
| `UCT-Benchmark-DMR/combined/docs/` | Implementation-focused docs (3 files) | Up to date for alignment work |
| `generated-docs/docs/` | MkDocs site for all documentation (50+ files) | **Needs updates** |

**Recommendation**: The `generated-docs/` should be the authoritative source, and the `combined/docs/` files should be incorporated into it or linked as references.

---

## Gap Analysis

### GAP 1: CHANGELOG Missing Recent Alignment Work
**Priority: HIGH**
**Location**: `generated-docs/docs/reports/CHANGELOG.md`

**Issue**: The CHANGELOG ends at [1.2.0] - 2026-01-25. The alignment work from 2026-01-31 is not documented.

**Required Updates**:
Add a new version entry [1.3.0] - 2026-01-31 with:
- TIER_5 "Impossible Criteria" detection logic implemented
- TrackTLE BatchLSEstimator integration completed
- Close (C) object filter with velocity threshold added
- Target Percentage Enforcement from 16-char codes verified
- ML Model Fallback handling for event detection added
- 6 new comprehensive alignment test files added

---

### GAP 2: Inconsistent Dataset Code Formats
**Priority: HIGH**
**Location**: `generated-docs/docs/guides/DATASET_GENERATION.md`

**Issue**: This file uses a different code format (`{REGIME}_{OBJ}_{COVERAGE}_{GAPS}_{OBS}`) than the actual implementation uses (16-character legacy codes like `H50LEONEOPSSSS07`).

**Required Updates**:
- Replace the incorrect code format with the 16-character legacy format
- Copy the detailed code structure table from `combined/docs/DATASET_GENERATION.md`
- Update all code examples to use `LegacyDatasetCode.from_code()` API

---

### GAP 3: TIER_5 Documentation Incomplete
**Priority: HIGH**
**Location**: `generated-docs/docs/technical/PIPELINE.md` (lines 92-93)

**Issue**: Only mentions T5=0 "Impossible" but doesn't explain detection conditions.

**Required Updates**:
Add detailed TIER_5 detection conditions:
```
TIER_5 ("Impossible") is assigned when:
1. No objects exist in the entire search space (object_count == 0)
2. Requested more objects than exist in catalog (min_objects > max_available_objects)
3. Data window far below required fit span (duration_days < 10% of fit_span_days)
4. All satellites have zero orbital coverage (avg_coverage == 0)
```

---

### GAP 4: New Alignment Test Files Not Documented
**Priority: MEDIUM**
**Location**: `generated-docs/docs/technical/VALIDATION.md` (if exists) or create new section

**Issue**: The 6 new test files are not documented anywhere:
- `test_16char_code_comprehensive.py` - 38 tests for all 16-char code positions
- `test_tier5_impossible.py` - 10 tests for TIER_5 detection
- `test_tracktle_batch_ls.py` - 11 tests for TrackTLE pipeline
- `test_target_percentage_enforcement.py` - 13 tests for target percentage
- `test_close_velocity_filter.py` - 12 tests for Close (C) object filter
- `test_ml_fallback.py` - 8 tests for ML model fallback

**Required Updates**:
Add a section documenting these tests with their purpose and coverage.

---

### GAP 5: TrackTLE Module Not Documented
**Priority: HIGH**
**Location**: New file needed or update `generated-docs/docs/technical/ARCHITECTURE.md`

**Issue**: The `tracktle.py` module has new functions that are not documented:
- `Observation` dataclass
- `TrackTLEResult` dataclass
- `PropagatorConfig` dataclass
- `modified_gauss_iod()` - Initial Orbit Determination
- `batch_ls_refinement_orekit()` - Orbit refinement with Orekit
- `state_to_tle()` - State vector to TLE conversion
- `generate_tracktle()` - Main pipeline function
- `_add_force_models_to_builder()` - Force model configuration
- `_create_topocentric_frame()` - Ground station frame creation

**Required Updates**:
Create a new section or document for TrackTLE generation pipeline.

---

### GAP 6: Close (C) Object Filter Velocity Threshold
**Priority: MEDIUM**
**Location**: `generated-docs/docs/guides/DATASET_GENERATION.md`

**Issue**: The Close (C) object type description doesn't mention the velocity threshold requirement.

**Required Updates**:
Update the Object Type table to include:
```
| C | Close | Physical proximity: distance < 100 km AND velocity < 100 m/s |
```
And add a note that both position AND velocity thresholds must be met.

---

### GAP 7: Configuration Constants Not Documented
**Priority: MEDIUM**
**Location**: `generated-docs/docs/technical/CONFIGURATION.md`

**Issue**: New settings constants are not documented:
- `PROXIMITY_VELOCITY_THRESHOLD_M_S` = 100.0 m/s
- `PROXIMITY_DISTANCE_THRESHOLD_KM` = 100.0 km
- `PROXIMITY_ANGULAR_THRESHOLD_DEG` (for Apparent objects)

**Required Updates**:
Add these to the configuration documentation with descriptions.

---

### GAP 8: Event Detection ML Fallback Configuration
**Priority: MEDIUM**
**Location**: `generated-docs/docs/guides/DATASET_GENERATION.md` or create new section

**Issue**: The ML model fallback handling configuration is not documented:
- `ml_model_available` flag
- `use_tle_fallback` flag
- `warn_on_ml_unavailable` flag

**Required Updates**:
Document the EventDetectionConfig options and explain the fallback behavior.

---

### GAP 9: Project Status Needs Update
**Priority: LOW**
**Locations**:
- `generated-docs/docs/index.md` (line 100-101)
- `generated-docs/docs/planning/PROJECT_STATUS.md` (line 9)

**Issue**: Both say "~85%" but the alignment work brings this to ~90%.

**Required Updates**:
Update progress to "~90% Complete" and add a note about the alignment work.

---

### GAP 10: LegacyDatasetCode API Documentation
**Priority: HIGH**
**Location**: `generated-docs/docs/guides/DATASET_GENERATION.md`

**Issue**: The API examples use incorrect function names. The actual API is:
```python
# Correct:
from uct_benchmark.config.dataset_schema import LegacyDatasetCode
code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")

# NOT:
from uct_benchmark.data.windowTools import codeGenerator
```

**Required Updates**:
Update all code examples to use the correct `LegacyDatasetCode` class API.

---

### GAP 11: Duplicate Documentation Cleanup
**Priority: LOW**
**Location**: `UCT-Benchmark-DMR/combined/docs/` vs `generated-docs/docs/`

**Issue**: Three files in `combined/docs/` overlap with generated-docs content:
- `EVALUATION_METRICS.md` - overlaps with `generated-docs/docs/technical/EVALUATION_METRICS.md`
- `DATASET_GENERATION.md` - overlaps with `generated-docs/docs/guides/DATASET_GENERATION.md`
- `LIMITATIONS.md` - no equivalent in generated-docs (should be added)

**Required Updates**:
1. Merge unique content from `combined/docs/` into `generated-docs/docs/`
2. Add `LIMITATIONS.md` content to generated-docs
3. Consider removing `combined/docs/` or adding a note that generated-docs is authoritative

---

### GAP 12: Window Selection Tiers Table Inconsistent
**Priority: LOW**
**Locations**: Multiple files reference tiers differently

**Issue**: Different files describe tiers inconsistently:
- Some use "T1-T4" with T5 as error
- Others use "Tier 1-5" with different descriptions
- Window selection tiers vs. data quality tiers confusion

**Required Updates**:
Standardize tier descriptions across all documentation to match the implementation.

---

### GAP 13: Binary Metrics TN (True Negative) Support
**Priority: MEDIUM**
**Location**: `generated-docs/docs/technical/EVALUATION_METRICS.md`

**Issue**: The TN (True Negative) support via non-reference observations is not documented as thoroughly as in `combined/docs/EVALUATION_METRICS.md`.

**Required Updates**:
Add the detailed TN explanation and code examples from `combined/docs/EVALUATION_METRICS.md`.

---

### GAP 14: API Integration Functions
**Priority: MEDIUM**
**Location**: `generated-docs/docs/API_INTEGRATION.md` or `generated-docs/docs/technical/BACKEND_API.md`

**Issue**: New functions in `apiIntegration.py` are not documented:
- `enforce_target_percentage()` - Enforces target object percentage from dataset codes
- `compute_velocity_difference()` (in objectTypeFiltering.py) - For Close object filtering

**Required Updates**:
Document these functions with their signatures and usage examples.

---

## Action Plan

### Phase 1: Critical Updates (Priority HIGH)
**Estimated effort: 2-3 hours**

1. **Update CHANGELOG** (GAP 1)
   - Add [1.3.0] version entry with all alignment work

2. **Fix Dataset Code Format** (GAP 2)
   - Update `generated-docs/docs/guides/DATASET_GENERATION.md` with correct 16-char format

3. **Document TIER_5** (GAP 3)
   - Add detection conditions to `generated-docs/docs/technical/PIPELINE.md`

4. **Document TrackTLE** (GAP 5)
   - Add section to `generated-docs/docs/technical/ARCHITECTURE.md` or create new file

5. **Fix API Examples** (GAP 10)
   - Update all code examples to use `LegacyDatasetCode` class

### Phase 2: Important Updates (Priority MEDIUM)
**Estimated effort: 1-2 hours**

6. **Document New Tests** (GAP 4)
   - Add to validation documentation

7. **Update Close Object Description** (GAP 6)
   - Add velocity threshold requirement

8. **Document Configuration Constants** (GAP 7)
   - Add new settings to configuration docs

9. **Document ML Fallback** (GAP 8)
   - Add event detection fallback configuration

10. **Update Binary Metrics TN** (GAP 13)
    - Add detailed TN documentation

11. **Document New API Functions** (GAP 14)
    - Add function documentation

### Phase 3: Cleanup (Priority LOW)
**Estimated effort: 1 hour**

12. **Update Progress Percentage** (GAP 9)
    - Update to ~90%

13. **Resolve Duplicates** (GAP 11)
    - Merge and consolidate documentation

14. **Standardize Tier Descriptions** (GAP 12)
    - Make consistent across all files

---

## Files to Modify

| File | Changes Required |
|------|-----------------|
| `generated-docs/docs/reports/CHANGELOG.md` | Add [1.3.0] entry |
| `generated-docs/docs/guides/DATASET_GENERATION.md` | Fix code format, API examples |
| `generated-docs/docs/technical/PIPELINE.md` | Add TIER_5 details |
| `generated-docs/docs/technical/ARCHITECTURE.md` | Add TrackTLE section |
| `generated-docs/docs/technical/CONFIGURATION.md` | Add new constants |
| `generated-docs/docs/technical/EVALUATION_METRICS.md` | Add TN details |
| `generated-docs/docs/technical/VALIDATION.md` | Add new test files |
| `generated-docs/docs/index.md` | Update progress |
| `generated-docs/docs/planning/PROJECT_STATUS.md` | Update progress |

---

## Verification Checklist

After completing updates, verify:

- [ ] All 16-character code examples use correct format
- [ ] `LegacyDatasetCode.from_code()` API is used consistently
- [ ] TIER_5 detection conditions are documented
- [ ] TrackTLE pipeline is documented
- [ ] Close (C) velocity threshold is mentioned
- [ ] All 6 new test files are documented
- [ ] CHANGELOG includes [1.3.0] version
- [ ] Progress percentage updated to ~90%
- [ ] Configuration constants are documented
- [ ] ML fallback behavior is documented

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| HIGH Priority Gaps | 5 | Need immediate attention |
| MEDIUM Priority Gaps | 6 | Should be addressed soon |
| LOW Priority Gaps | 3 | Can be deferred |
| **Total Gaps** | **14** | **Documentation ~80% complete** |

**Estimated Total Effort**: 4-6 hours to bring documentation to 100% alignment with implementation.
