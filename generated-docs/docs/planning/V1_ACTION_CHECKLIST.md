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

### 1.1 T3 Processing (Observation Simulation)

#### 1.1.1 Complete `epochsToSim()`
**File**: `simulateObservations.py:360-428`
- [ ] Analyze current implementation
- [ ] Implement coverage calculation
- [ ] Implement gap identification
- [ ] Implement epoch selection algorithm
- [ ] Test function independently

#### 1.1.2 Integrate into Create_Dataset.py
**File**: `Create_Dataset.py:104-107`
- [ ] Add T3 processing branch
- [ ] Loop through satellites needing simulation
- [ ] Call epochsToSim() and simulateObs()
- [ ] Merge simulated observations
- [ ] Mark simulated obs with dataMode='SIMULATED'
- [ ] Recalculate quality score

#### 1.1.3 Test T3
- [ ] Create test with sparse dataset
- [ ] Verify correct obs count added
- [ ] Verify physical realism
- [ ] Verify evaluation works

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

### 1.3 Downsampling (T1/T2)

#### 1.3.1 Create downsample.py
**File**: New `uct_benchmark/data/downsample.py`
- [ ] Create file with module structure
- [ ] Implement `downsample_random()`
- [ ] Implement `downsample_systematic()`
- [ ] Implement `downsample_track_aware()`
- [ ] Implement `downsample_coverage_preserving()`
- [ ] Implement main `downsample()` dispatcher

#### 1.3.2 Integrate into Create_Dataset.py
- [ ] Add T1/T2 processing branches
- [ ] Apply downsampling per satellite
- [ ] Log reduction statistics

#### 1.3.3 Test Downsampling
- [ ] Test each strategy
- [ ] Verify correct counts
- [ ] Verify evaluation works

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
| 1.1 T3 Processing | Not Started | | |
| 1.2 T4 Processing | Not Started | | Needs 1.1 |
| 1.3 Downsampling | Not Started | | |
| 2.1 PDF Report | Not Started | | |
| 2.2 Noise Modeling | Not Started | | |
| 3.1 Event Labeling | Not Started | | |
| 3.2 Performance | Not Started | | |
| 4.1 Open Evolve | Not Started | | Stretch goal |

---

## Files to Create

| File | Priority | Purpose |
|------|----------|---------|
| `simulation/simulateObjects.py` | P1 | T4 object simulation |
| `data/downsample.py` | P1 | T1/T2 downsampling |
| `simulation/noiseModels.py` | P2 | Realistic noise |
| `labelling/eventIntegration.py` | P3 | IU team integration |

## Files to Modify

| File | Priority | Changes |
|------|----------|---------|
| `Create_Dataset.py` | P1 | T1-T4 processing |
| `simulateObservations.py` | P1 | Complete epochsToSim() |
| `generatePDF.py` | P2 | Report improvements |

---

*Last Updated: 2026-01-17*
