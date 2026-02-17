# V1 Fixes Action Checklist

**Quick reference checklist for V1 fixes. See [V1_FIXES_MASTER_PLAN.md](V1_FIXES_MASTER_PLAN.md) for full details.**

---

## Priority 0: UCTP Validation (BLOCKING)

### 0.1 Contact Patrick Ramsey
- [ ] Get contact info from Atulya
- [ ] Send introduction email
- [ ] Schedule meeting
- [ ] Document UCTP input/output requirements

### 0.2 Prepare Validation Datasets
- [ ] Generate LEO T1 dataset
- [ ] Generate LEO T2 dataset
- [ ] Generate GEO T1 dataset
- [ ] Generate MEO T2 dataset (if possible)
- [ ] Document each dataset's characteristics
- [ ] Create `validation_datasets/README.md`

### 0.3 Run Validation
- [ ] Send datasets to Aerospace Corp
- [ ] Receive UCTP output
- [ ] Run evaluation on real output
- [ ] Document any issues
- [ ] Iterate until working

---

## Priority 1: Core Pipeline

### 1.1 T3 Processing (Observation Simulation) ✅ COMPLETE (2026-01-18)

**Note:** T3 simulation now fully implemented with time-bin based approach.

#### 1.1.1 Complete `epochsToSim()` ✅
**File**: `simulateObservations.py:358-507`
- [x] Rewrote with time-bin based approach
- [x] Divides observation window by orbital period
- [x] Identifies empty bins (coverage gaps)
- [x] Generates epochs in realistic tracks
- [x] Returns detailed statistics

#### 1.1.2 Integrate into Create_Dataset.py ✅
**File**: `Create_Dataset.py:66-175`
- [x] Add T3 processing branch
- [x] Loop through satellites needing simulation
- [x] Call epochsToSim() to determine epochs
- [x] Generate state vectors from orbital elements
- [x] Call simulateObs() to create observations
- [x] Mark simulated obs with dataMode='SIMULATED'

#### 1.1.3 Test T3 ✅
- [x] Created `test_simulation.py` - 3/3 tests pass
- [x] Tests epochsToSim() with sparse data
- [x] Tests with real sample data
- [x] Pipeline test: 8/8 stages pass

---

### 1.2 T4 Processing (Object Simulation)

#### 1.2.1 Create simulateObjects.py
**File**: New `uct_benchmark/simulation/simulateObjects.py`
- [ ] Create file with module structure
- [ ] Implement `determineObjectsNeeded()`
- [ ] Implement `generateSyntheticOrbit()` with regime logic
- [ ] Implement `generateSyntheticTLE()`
- [ ] Implement `simulateObjectObservations()`
- [ ] Implement main `createSyntheticObject()`

#### 1.2.2 Integrate into Create_Dataset.py
**File**: `Create_Dataset.py:104-107`
- [ ] Add T4 processing branch
- [ ] Calculate objects needed
- [ ] Generate synthetic objects
- [ ] Add to reference data
- [ ] Merge observations with dataMode='SYNTHETIC_OBJECT'

#### 1.2.3 Test T4
- [ ] Test with object-deficient scenario
- [ ] Verify orbital parameters realistic
- [ ] Verify evaluation works

---

### 1.3 Downsampling (T1/T2) ✅ COMPLETE (2026-01-18)

**Note:** Existing `downsampleData()` function in `uct_benchmark/data/dataManipulation.py` was already implemented but not integrated. Integration completed 2026-01-18.

#### 1.3.1 ~~Create downsample.py~~ (Used existing implementation)
**File**: `uct_benchmark/data/dataManipulation.py` (existing)
- [x] `downsampleData()` function already exists with:
  - Coverage-based downsampling
  - Track gap downsampling
  - Observation count downsampling
- [x] Fixed bug at line 627 (set indexer → list conversion)

#### 1.3.2 Integrate into Create_Dataset.py ✅
- [x] Add T1/T2 processing branches (lines 71-120)
- [x] Apply downsampling using `dataM.downsampleData()`
- [x] Log reduction statistics
- [x] Added config parameters to `uct_benchmark/config.py`

#### 1.3.3 Test Downsampling ✅
- [x] Created `test_downsampling.py` - 3/3 tests pass
- [x] Created `test_pipeline_e2e.py` - 8/8 stages pass
- [x] Verify correct counts - PASS
- [x] Verify evaluation works - PASS

---

## Priority 2: Quality Improvements

### 2.1 PDF Report

#### 2.1.1 Audit Current Report
**File**: `uct_benchmark/utils/generatePDF.py`
- [ ] Review current structure
- [ ] List visual issues
- [ ] Document improvement areas

#### 2.1.2 Implement Improvements
- [ ] Add cover page
- [ ] Add executive summary
- [ ] Improve charts (confusion matrix heatmap, histograms)
- [ ] Consistent styling
- [ ] Better tables

#### 2.1.3 Add HTML Export (Optional)
- [ ] Create HTML template
- [ ] Add interactive charts

---

### 2.2 Noise Modeling

#### 2.2.1 Research
- [ ] Review papers in provided-materials/
- [ ] Document noise sources

#### 2.2.2 Create noiseModels.py
**File**: New `uct_benchmark/simulation/noiseModels.py`
- [ ] Implement `atmospheric_refraction()`
- [ ] Implement `stellar_aberration()`
- [ ] Implement `atmospheric_scintillation()`
- [ ] Implement `sensor_noise()`
- [ ] Implement `total_observation_noise()`
- [ ] Implement `add_realistic_noise()`

#### 2.2.3 Integrate
- [ ] Replace Gaussian noise in simulateObservations.py
- [ ] Add configuration options

---

## Priority 3: Integration

### 3.1 Event Labeling (IU Team)
- [ ] Contact Atulya for IU team deliverables
- [ ] Obtain database/code
- [ ] Create integration layer
- [ ] Add to dataset generation

### 3.2 Performance
- [ ] Profile pipeline
- [ ] Identify bottlenecks
- [ ] Optimize slow operations
- [ ] Add progress indicators

---

## Priority 4: Future

### 4.1 Open Evolve
- [ ] Research Open Evolve architecture
- [ ] Design integration architecture
- [ ] Document API requirements

---

## Quick Status Tracker

| Task | Status | Assignee | Notes |
|------|--------|----------|-------|
| 0.1 Contact Patrick | Not Started | | |
| 0.2 Validation Datasets | Not Started | | |
| 0.3 Run Validation | Blocked | | Needs 0.1, 0.2 |
| 1.1 T3 Processing | ✅ **Complete** | Team | 2026-01-18, 3/3 simulation + 8/8 pipeline pass |
| 1.2 T4 Processing | Not Started | | |
| 1.3 Downsampling | ✅ **Complete** | Team | 2026-01-18, 3/3 + 8/8 tests pass |
| 2.1 PDF Report | Not Started | | Fixed bug in generatePDF.py |
| 2.2 Noise Modeling | Not Started | | |
| 3.1 Event Labeling | Not Started | | |
| 3.2 Performance | Not Started | | |
| 4.1 Open Evolve | Not Started | | Stretch goal |

---

## Files to Create

| File | Priority | Purpose | Status |
|------|----------|---------|--------|
| `simulation/simulateObjects.py` | P1 | T4 object simulation | Not Started |
| ~~`data/downsample.py`~~ | ~~P1~~ | ~~T1/T2 downsampling~~ | ✅ Used existing `dataManipulation.py` |
| `simulation/noiseModels.py` | P2 | Realistic noise | Not Started |
| `labelling/eventIntegration.py` | P3 | IU team integration | Not Started |

## Files Modified (2026-01-18)

| File | Changes Made | Status |
|------|--------------|--------|
| `uct_benchmark/config.py` | Added downsampling config parameters | ✅ Done |
| `src/Create_Dataset.py` | T1/T2 downsampling integration (lines 71-120) | ✅ Done |
| `uct_benchmark/data/dataManipulation.py` | Fixed set indexer bug at line 627 | ✅ Done |
| `src/libraries/generatePDF.py` | Fixed hardcoded path bug at line 419 | ✅ Done |

## Files to Modify (Remaining)

| File | Priority | Changes |
|------|----------|---------|
| `Create_Dataset.py` | P1 | T3/T4 processing (downsampling done) |
| `simulateObservations.py` | P1 | Complete epochsToSim() |
| `generatePDF.py` | P2 | Report visual improvements |

## Test Files Created (2026-01-18)

| File | Purpose | Status |
|------|---------|--------|
| `test_downsampling.py` | Standalone downsampling test | ✅ 3/3 pass |
| `test_pipeline_e2e.py` | End-to-end pipeline test | ✅ 8/8 pass |

---

*Last Updated: 2026-01-18*
