# UCT Benchmark - Vision Alignment Audit Report

**Date:** 2026-04-02 (Updated)
**Auditor:** Claude Opus 4.6 (1M context)
**Scope:** Complete comparison of original requirements (Benchmarking Documentation, transcripts, reference code) vs. actual implementation

---

## Executive Summary

The UCT Benchmark application captures approximately **75-80%** of the original vision described by Louis Caves and the AFRL Scholars team. The core evaluation pipeline (orbit association, binary metrics, state metrics, residual metrics) is **substantially implemented and algorithm-correct**. The dataset generation pipeline is largely implemented with all key algorithms present. The web platform (UI, authentication, leaderboard) goes **beyond** what was originally requested and represents a significant value-add. The primary gaps are operational rather than conceptual: Orekit dependency in production, event data sourcing, and a composite scoring system that was discussed but not formally implemented.

---

## Feature Alignment Matrix

### Dataset Generation Pipeline

| Feature (from requirements) | Status | Notes |
|---|---|---|
| 16-character dataset code system | **IMPLEMENTED** | Full encoding/decoding in `types/index.ts` and `settings.py`. All 10 code fields mapped per Benchmarking Doc lines 289-367. |
| Object Type filtering (H,C,A,U,N) | **PARTIAL** | HAMR (H), Unspecified (U), Calibration (N) implemented in `objectTypeFiltering.py`. Close (C) and Apparent (A) are stubs -- the original doc itself notes "not yet been implemented; these values are arbitrary." |
| Target Object Percentage (50,10,01,UN) | **PARTIAL** | Schema supports it (DB `target_percentage` column), UI has it. Backend `basicScoringFunction.py` has only partial percentage selection logic. |
| Orbital Regime (LEO,MEO,GEO,HEO,ALL,combos) | **IMPLEMENTED** | Semi-major axis thresholds match exactly (LEO < 8378 km, GEO >= 42164 km, HEO e >= 0.7) in `settings.py`. Combo regimes exist in types. |
| Event Types (MB,BU,LL,NE) | **PARTIAL** | `eventDetection.py` has EventType enums and TLE discontinuity detection as proxy for maneuvers. No real event data source. Louis stated (Jan 22): "we would need a database of when objects are maneuvering... that's something we didn't have readily available." |
| Sensor Types (OP,RA,RF,FU,combos) | **PARTIAL** | Schema/UI support all types. Louis stated (Jan 22): "radar and passive RF observations are not as readily accessible... working exclusively with optical observations for the time being." |
| Orbit Coverage calculation (convex polygon) | **IMPLEMENTED** | `orbitCoverage.py` implements exactly per Benchmarking Doc lines 374-382: fits observations to nearest orbit approach, projects through geometric center onto circumscribed circle, computes convex hull area ratio. |
| Track Gap metric (>2 orbital periods) | **IMPLEMENTED** | `settings.py` defines `longTrackGap = 2` (periods). Regime-specific thresholds correct. |
| Observation Count thresholds | **IMPLEMENTED** | Low <50, Standard 50-150, >150 downsampled -- matches Benchmarking Doc lines 352-357. |
| Object Count (H=80, S=40, L=10 +/-2) | **IMPLEMENTED** | `OBJECT_COUNT_MAP` in `settings.py` matches doc. |
| Fitspan (01-14 days, 2-char integer) | **IMPLEMENTED** | Frontend `validateLegacyCode()` enforces 01-14. |
| Time Window Selection (bisection algorithm) | **IMPLEMENTED** | `windowSelection.py` implements bisect-then-slide per Louis's Jan 22 transcript description. |
| Tier Classification (T1-T5) | **IMPLEMENTED** | T1 (no manipulation), T2 (downsampling), T3 (simulation), T4 (simulate new objects), T5 (impossible). `basicScoringFunction.py` computes tiers. |
| Tier 5 impossibility check (GEO track gap) | **IMPLEMENTED** | Added per Louis's exact example: "Two periods between observations for GEO... but they only want a two day window -- that's not possible." |
| Sequential Downsampling (coverage->gap->count) | **IMPLEMENTED** | `dataManipulation.py` performs all 3 stages in specified order per Benchmarking Doc lines 402-415. |
| Observation Simulation | **IMPLEMENTED** | `simulateObservations.py` implements sensor list, epoch generation, propagation, Gaussian noise, RA/Dec conversion per doc lines 384-393. |
| Atmospheric refraction noise model | **IMPLEMENTED** | `atmospheric.py` has `apply_atmospheric_refraction()` per Louis's future work item: "there's also other sources of uncertainty, such as atmospheric refraction." |
| Velocity aberration noise model | **IMPLEMENTED** | `atmospheric.py` has `compute_velocity_aberration()` per Louis's future work. |
| Observations to trackTLE (Modified Gauss + BatchLS) | **IMPLEMENTED** | `TLEGeneration.py` uses Modified Gauss Method + Orekit BatchLSEstimator per doc lines 394-399. |
| True Negatives (2 obs per non-ref satellite) | **IMPLEMENTED** | `dataManipulation.py` has `add_non_reference_observations()`. `settings.py` has `NON_REF_OBS_PER_SATELLITE = 2`. DB has `non_reference_observations` table. |
| Decorrelation (remove satellite IDs, keep track grouping) | **IMPLEMENTED** | DB schema has `assigned_track_id` and `assigned_object_id` in `dataset_observations`. Answer key stored as JSON per doc line 423. |
| Dataset Code GUI | **DIVERGENT (improved)** | Original: `customtkinter` desktop GUI. Replaced with React web UI `DatasetGeneratorPage.tsx` with multi-step wizard. Functionally superior. |
| Save dataset format (dataset_obs + reference) | **IMPLEMENTED** | Worker persists dataset_obs, reference data (grouped_obs_ids), answer_key to PostgreSQL. Matches `saveDataset()` spec from doc lines 745-768. |

### Evaluation Pipeline

| Feature (from requirements) | Status | Notes |
|---|---|---|
| Frame Conversion (J2000/EME2000) | **IMPLEMENTED** | `unitConversion.py` converts from TEME, GCRF, ITRF, ECEF, TDR to J2000 using Orekit. |
| TLE to State Vector conversion | **IMPLEMENTED** | `apiIntegration.py` has `TLEToSV()` using Orekit TLEPropagator. |
| Orbit Association (Jonker-Volgenant/linear_sum_assignment) | **IMPLEMENTED** | `orbitAssociation.py` uses `scipy.optimize.linear_sum_assignment` exactly per doc lines 440-451. Handles unequal candidate/reference counts. |
| State Vector Propagation (DormandPrince853) | **IMPLEMENTED** | `propagator.py` uses Orekit with HolmesFeatherstoneAttractionModel (degree/order 120), Sun/Moon point masses, NRLMSISE-00 drag, isotropic SRP, ESA mass/cross-section. |
| Covariance Propagation (Monte Carlo, N=100) | **IMPLEMENTED** | `monteCarloPropagator()` samples from multivariate normal, propagates each, computes posterior covariance. Discards sub-Earth points. |
| TLE Propagation (SGP4/SDP4 automatic selection) | **IMPLEMENTED** | `TLEpropagator()` uses Orekit TLEPropagator (internally selects SGP4/SDP4 per NORAD). |
| State Metrics: L2 Norm (position, velocity, 6D) | **IMPLEMENTED** | `stateMetrics.py` computes all three norms. |
| State Metrics: Per-dimension Bias | **IMPLEMENTED** | Bias computed for all 6 state dimensions. |
| State Metrics: Mahalanobis Distance (combined covariance) | **IMPLEMENTED** | `_compute_MD()` uses `d = delta^T * (C_ref + C_cand)^-1 * delta` per doc line 491. |
| State Metrics: Mahalanobis p-score (chi2, 6 DOF) | **IMPLEMENTED** | `1 - chi2.cdf(MD, df=6)` per doc line 492. |
| State Metrics: NEES (candidate covariance only) | **IMPLEMENTED** | `_compute_NEES()` uses `delta^T * P_cand^-1 * delta` per doc line 493. |
| State Metrics: NEES p-score (chi2, 6 DOF) | **IMPLEMENTED** | `1 - chi2.cdf(NEES, df=6)` per doc line 494. |
| State Metrics for TLEs (L2 norms only, no Mahalanobis) | **IMPLEMENTED** | TLE mode converts to state vectors, computes L2 norms. Skips Mahalanobis/NEES per doc line 498. |
| Residual Metrics: Great circle distance (reference obs vs candidate orbit) | **IMPLEMENTED** | `residualMetrics.py` Mode 1: reference observations projected against candidate orbit. |
| Residual Metrics: Great circle distance (candidate obs vs candidate orbit) | **IMPLEMENTED** | `residualMetrics.py` Mode 2: candidate's own observations against candidate orbit. |
| Binary Classification: TP/TN/FP/FN | **IMPLEMENTED** | `binaryMetrics.py` definitions match doc lines 513-516 exactly. |
| Binary: Accuracy | **IMPLEMENTED** | `(TP+TN)/(TP+FP+TN+FN)` per doc line 520. |
| Binary: Recall/Sensitivity | **IMPLEMENTED** | `TP/(TP+FN)` via sklearn. |
| Binary: Balanced Accuracy | **IMPLEMENTED** | Via sklearn `balanced_accuracy_score`. |
| Binary: Cohen's Kappa | **IMPLEMENTED** | Via sklearn `cohen_kappa_score`. |
| Binary: Matthews Correlation Coefficient | **IMPLEMENTED** | Via sklearn `matthews_corrcoef`. |
| Binary: Precision (PPV) | **IMPLEMENTED** | `TP/(TP+FP)` per doc line 525. |
| Binary: F1 Score | **IMPLEMENTED** | Via sklearn `f1_score`. |
| Binary: Specificity | **IMPLEMENTED** | `TN/(TN+FP)` per doc line 527. |
| Evaluation Report (JSON) | **IMPLEMENTED** | `evaluationReport.py` generates JSON with association, binary, state, and residual sections. |
| Evaluation Report (PDF) | **IMPLEMENTED** | `generatePDF.py` generates PDF with tables and graphs using fpdf + matplotlib. |
| Dummy UCTP for verification testing | **IMPLEMENTED** | `dummyUCTP.py` creates randomized output for pipeline verification. |

### Web Platform (Beyond Original Scope)

| Feature (from requirements) | Status | Notes |
|---|---|---|
| Web-hosted UI | **IMPLEMENTED** | React + Vite frontend with 13 pages. Louis (Jan 22): "Ideally we want this to be a software package that can run on remote servers. Everything needs to be containerized." |
| User authentication (multi-user platform) | **IMPLEMENTED** | Supabase JWT auth with ES256 JWKS. |
| "Upload a submission" area | **IMPLEMENTED** | `SubmitPage.tsx` with drag-and-drop, client-side JSON validation. Louis (transcript.md, line 5): "we got the area to upload a submission." |
| Dataset browser with filtering | **IMPLEMENTED** | `DatasetBrowserPage.tsx` with regime, tier, sensor filters. |
| "All configurations in the user interface" | **IMPLEMENTED** | `DatasetGeneratorPage.tsx` has all 10 dataset code parameters. Louis (transcript.md, line 7). |
| "Orbital coverage slider bar" | **IMPLEMENTED** | Coverage selection with regime-specific thresholds per Louis's feedback. |
| "Datasets are distinct, proper labeling" | **IMPLEMENTED** | Each dataset is a separate DB record with unique name/code. Louis (transcript.md, line 11). |
| "Ability to go back and look at old data sets" | **IMPLEMENTED** | `MyDatasetsPage.tsx` shows user's datasets. Louis (transcript.md, line 21). |
| "Store in same schema as documentation" | **IMPLEMENTED** | DB schema matches documentation structure. |
| Leaderboard (compare processors) | **IMPLEMENTED** | `LeaderboardPage.tsx` with filtering, sorting, trend charts. Louis (Jan 22): "we've got this third party evaluation software that says... we can show you exactly where one was deficient with respect to the other." |
| Results viewing with metrics | **IMPLEMENTED** | `ResultsPage.tsx` with TP/FP/FN breakdown, position error histograms, residual histograms. |
| Dashboard | **IMPLEMENTED** | `DashboardPage.tsx` with user stats. Value-add beyond original scope. |
| Feedback system | **IMPLEMENTED** | `FeedbackProvider`, feedback router. Value-add. |
| Documentation page | **IMPLEMENTED** | `DocumentationPage.tsx`. Value-add. |
| Profile/API key management | **IMPLEMENTED** | `ProfilePage.tsx` for UDL/ESA token management. |
| AI chatbot | **NOT IMPLEMENTED** | Correctly skipped. Louis (Feb 19): "I don't know if that necessarily helps advance the project towards our minimum success criterias." Dr. Cline: "icing on the cake." |
| 3D Globe visualization | **NOT IMPLEMENTED** | Aidan (Feb 19, line 473) mentioned "a globe, sort of, just some interactive stuff." Not implemented -- low priority visual feature. |

### Data Integrations

| Feature (from requirements) | Status | Notes |
|---|---|---|
| UDL API integration | **IMPLEMENTED** | `apiIntegration.py` has async batch queries, observation and state vector retrieval, rate limiting. |
| ESA DiscoWeb integration (mass/cross-section) | **IMPLEMENTED** | `discoswebQuery()` for satellite physical properties needed for propagation per doc line 76-77. |
| Space-Track TLE queries | **IMPLEMENTED** | Referenced across 15+ files. Alternative TLE source. |
| DuckDB local storage | **IMPLEMENTED** | Full adapter in `database/adapters/duckdb_adapter.py`. Per Feb 19 transcript (Bryant, line 107). |
| PostgreSQL production storage | **IMPLEMENTED** | Full adapter in `database/adapters/postgres_adapter.py`. Supabase deployment. |

---

## Missing Features (from transcripts)

1. ~~**Composite/Weighted Scoring System**~~: **RESOLVED (2026-04-08)**. `compute_composite_score()` in `workers.py` implements Lewis's Feb 19 philosophy with weights 0.4/0.3/0.3 (binary/state/residual). Leaderboard ranks by `COALESCE(test_composite_score, composite_score, f1_score)`.

2. **Event-Based Dataset Filtering (Maneuver/Breakup/Low-Thrust)**: Louis (Jan 22): "the different types of events... like breakup events or maneuver events, we would need a database of when objects are maneuvering... that's something that we didn't have readily available." The event tables exist in schema (`events`, `event_types`, `event_observations`) but contain no data. No ML labeling team output was ever integrated (Benchmarking Doc line 321: "the ML Model is not operating").

3. **Close Objects (C) and Close Apparent Objects (A) Filtering in Practice**: While `objectTypeFiltering.py` has the logic, the Benchmarking Doc notes "not yet been implemented; these values are arbitrary." The reference code also lacked working implementations. Distance and angular thresholds need real-world calibration.

4. **Target Object Percentage Enforcement in Pipeline**: The 16-char code supports 50/10/01/UN percentages, but the actual window selection algorithm does not rigorously enforce precise target percentages. It selects windows with "any natural distribution" when HAMR/Close objects are requested.

5. **Non-Optical Sensor Support in Practice**: The schema supports radar/RF sensor types, but all actual data pipelines pull optical (EO) data only from the UDL. Louis acknowledged this (Jan 22): "working exclusively with optical observations for the time being."

6. **3D Globe Visualization**: Mentioned by Aidan (Feb 19, line 473) as a UI enhancement. Not implemented but explicitly deprioritized by Louis.

7. **End-to-End Evaluation in Production Without Orekit**: The evaluation pipeline (`run_evaluation_pipeline` in `workers.py`) imports `orbitAssociation`, `binaryMetrics`, `stateMetrics`. The full evaluation (state vector propagation, Mahalanobis distance, residual metrics) requires Orekit. Without Java/Orekit on the production server, evaluation is limited to binary metrics only.

---

## Deviations from Original Vision

1. **Architecture: Desktop App -> Web Platform**
   - Original: Python desktop application with `customtkinter` GUI, local file I/O
   - Built: Client-server web application (FastAPI + React + PostgreSQL + REST API)
   - Louis (Jan 22): "Ideally we want this to be a software package that can run on remote servers. Everything needs to be containerized as a software package."
   - **Assessment**: Positive deviation. Directly addresses Louis's stated goal of remote accessibility and multi-user evaluation.

2. **Leaderboard Ranking: F1 Score Only vs. Composite Metric**
   - Original: Louis described losing points for bad states, bad correlations, and high residuals independently.
   - Built: Leaderboard ranks by F1 score only (binary metric). State metrics and residual metrics are computed but not folded into ranking.
   - Louis (Feb 19, line 553): "we selected our metrics such that they should be representative of... a good processor doing well."
   - **Assessment**: Partial deviation. The individual metrics are correct but the composite ranking is missing.

3. **Evaluation Report Format: PDF + JSON vs. PDF Only**
   - Original (Benchmarking Doc line 266): "An evaluation report will be generated and saved as a PDF file."
   - Built: Both JSON (`evaluationReport.py`) and PDF (`generatePDF.py`) reports, plus web-based visualization.
   - **Assessment**: Positive deviation -- more formats available.

4. **Window Selection: Pure UDL vs. Configurable Sources**
   - Original: All data sourced exclusively from UDL.
   - Built: Supports UDL, Space-Track, and CelesTrak as data sources. Configurable search strategy.
   - **Assessment**: Positive deviation -- more resilient data sourcing.

5. **Tier 3/4 Integration: Fully Automated vs. Partially Automated**
   - Original: Louis described Tier 3 (simulate obs for existing objects) and Tier 4 (simulate new objects) as automated steps.
   - Built: Simulation code exists (`simulateObservations.py`, `TLEGeneration.py`) but Tier 3/4 require Orekit, which may not be available in production.
   - Reference code (Create_Dataset.py lines 62-73) itself noted: "T4 NOT implemented. Moving On" and "T3 NOT implemented. Moving On."
   - **Assessment**: This matches the state of the original reference code, which also hadn't fully integrated T3/T4.

---

## Scoring/Evaluation Alignment

### Binary Metrics: EXACT MATCH

All 8 binary metrics from Benchmarking Doc lines 509-527 are implemented with correct formulas:

| Metric | Doc Formula | Implementation | Verified |
|--------|-------------|----------------|----------|
| Accuracy | (TP+TN)/(TP+FP+TN+FN) | Direct calculation | Yes |
| Recall/Sensitivity | TP/(TP+FN) | sklearn `recall_score` | Yes |
| Balanced Accuracy | 0.5*[TP/(TP+FN) + TN/(TN+FP)] | sklearn `balanced_accuracy_score` | Yes |
| Cohen's Kappa | (p_o - p_e)/(1 - p_e) | sklearn `cohen_kappa_score` | Yes |
| Matthews Corr. Coeff. | [(TP)(TN)-(FP)(FN)]/sqrt[...] | sklearn `matthews_corrcoef` | Yes |
| Precision (PPV) | TP/(TP+FP) | Manual computation | Yes |
| F1 Score | (2TP)/(2TP+FP+FN) | sklearn `f1_score` | Yes |
| Specificity | TN/(TN+FP) | Manual computation | Yes |

### State Metrics: EXACT MATCH

All 6 state metrics from Benchmarking Doc lines 485-494 are implemented:

| Metric | Status | Notes |
|--------|--------|-------|
| L2 Norm (position, velocity, 6D) | Correct | 3 separate norms computed |
| Per-dimension Bias | Correct | All 6 state dimensions |
| Mahalanobis Distance | Correct | Combined covariance C_ref + C_cand |
| Mahalanobis p-score | Correct | chi2.cdf with 6 DOF |
| NEES | Correct | Candidate covariance only |
| NEES p-score | Correct | chi2.cdf with 6 DOF, >0.5 = underconfident |

### Additional Metrics (Beyond Original Spec)

The implementation adds valuable metrics not in the original documentation:
- **RIC (Radial/In-track/Cross-track) errors** -- `calculate_radial_in_track_cross_track_errors()`
- **Batch NEES statistics** with chi-squared consistency test
- **Comprehensive aggregate statistics** (mean, std, rms, median, max, min)

### Residual Metrics: EXACT MATCH

Both residual metric modes from Benchmarking Doc lines 500-507:
1. Mode 1: Reference observations vs. Candidate Orbit (accuracy measure)
2. Mode 2: Candidate observations vs. Candidate Orbit (precision measure)

Uses great circle distance on unit sphere per specification.

### What Is Missing from Scoring

Louis (Feb 19, lines 541-561) described a scoring philosophy where the metrics are combined:
> "if the states are off, you lose points there... if your observations are incorrectly correlated, you lose points there. If your sum of residuals is really high, then you lose points there."

The individual metrics are all implemented. What is missing is a **composite scoring function** that weights binary metrics, state metrics, and residual metrics into a single overall performance score. The leaderboard (`leaderboard.py` line 83) orders by `sr.f1_score DESC` only.

---

## Data Pipeline Alignment

### UDL Query Flow

| Step (from Louis Jan 22 transcript) | Implementation | Match |
|------|------|-------|
| "Data is pulled from the UDL in a very large batch" | `apiIntegration.py` async batch queries with adaptive sizing | Yes |
| "We'll go to the UDL and we'll pull say 10 days worth of data" | `batchPull` pulls configurable multiples of fitspan | Yes |
| "It's going to start by cutting the data... bisecting the data set" | `windowSelection.py` implements recursive bisection | Yes |
| "Keep doing that, bisecting the data set" | Recursive halving until smaller than fitspan | Yes |
| "Once you get to a small enough subbatch, start sliding" | Sliding window search within smallest viable batch | Yes |
| "We're going to look at each window... classify according to tier" | `basicScoringFunction.py` computes tier per window | Yes |

### Downsampling Flow (Benchmarking Doc lines 402-415)

| Step | Implementation | Match |
|------|------|-------|
| 1. Orbital Coverage reduction | `dataManipulation.py` removes obs for largest coverage area loss | Yes |
| 2. Track Gap widening | Sliding window to find min-obs window for removal | Yes |
| 3. Observation Count reduction | Time-quantile binning with equal random removal | Yes |
| Sequential order enforced | Order: coverage -> gap -> count | Yes |
| Skip simulated/true-negative satellites | Excluded from downsampling | Yes |

### Simulation Flow (Benchmarking Doc lines 384-393)

| Step | Implementation | Match |
|------|------|-------|
| Common observatory list selection | `simulateObservations.py` uses sensor DataFrame | Yes |
| Epoch list generation for coverage | Generated per orbital coverage target | Yes |
| Propagation to observation epochs | Orekit propagator (when available) | Yes |
| Gaussian noise on position | `config.positionNoise` applied | Yes |
| RA/Dec conversion | Position -> RA/Dec with angular noise | Yes |
| Az/El conversion from observatory | Observatory location used for conversion | Yes |

### Configuration Constants

| Constant | Benchmarking Doc Value | Implementation Value | Match |
|----------|----------------------|---------------------|-------|
| LEO cutoff | a <= 8378 km | `semiMajorAxis_LEO = 8378` | YES |
| GEO cutoff | a >= 42164 km | `semiMajorAxis_GEO = 42164` | YES |
| HEO eccentricity | e >= 0.7 | `eccentricity_HEO = 0.7` | YES |
| Low coverage LEO | <0.0213% | `lowCoverage_LEO = 0.000213` | YES |
| Low coverage MEO | <0.0449% | `lowCoverage_MEO = 0.000449` | YES |
| Low coverage GEO | <41.656% | `lowCoverage_GEO = 0.41656` | YES |
| Long track gap | >2 orbital periods | `longTrackGap = 2` | YES |
| Low obs count | <50 per 3 days | `lowObsCount` | YES |
| Standard obs count | 50-150 | Implemented | YES |
| Object count H/S/L | 80/40/10 (+/-2) | `OBJECT_COUNT_MAP` | YES |
| Calibration satellite IDs | 30 NORAD IDs | `satIDs` (exact same 30 IDs) | YES |
| MC propagation N | 100 | `monteCarloPoints` default | YES |
| HAMR threshold | >1 m^2/kg | `HAMR_THRESHOLD = 1.0` | YES |
| DormandPrince853 tolerances | rel 1e-14, abs 1e-12 | Orekit integrator config | YES |

---

## Database Schema Alignment

### Strengths

- **Full decomposition of 16-char legacy code** into queryable columns (object_type_code, target_percentage, event_code, sensor_code, coverage_level, track_gap_level, obs_count_level, object_count_level, fitspan_days)
- **Answer key stored per decorrelation spec** (JSON mapping obs IDs to satellite NORAD IDs)
- **Non-reference observations table** for True Negative calculation
- **Event labeling infrastructure** (event_types, events, event_observations tables) ready for future ML team output
- **Submission results** store all binary metrics, state metrics, and raw results JSON
- **Version tracking** with parent_id for dataset lineage per Louis's comment (transcript.md, line 21)

### Gaps

1. **No dedicated trackTLE storage**: The `element_sets` table stores TLEs but cannot distinguish refined UDL TLEs from crude trackTLEs generated via Modified Gauss Method. If TLE-input UCTPs are benchmarked via the web platform, this needs addressing.

2. **No composite score column** in `submission_results`: The table stores individual metrics but has no computed composite score for ranking beyond F1.

---

## Summary Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| **Evaluation Pipeline (algorithms)** | 95% | All metrics, all algorithms, correct math. Orekit required for full execution. |
| **Dataset Generation (T1)** | 90% | Window selection, scoring, calibration satellites, all thresholds correct. |
| **Dataset Generation (T2/Downsampling)** | 85% | All 3 sequential stages implemented and ordered correctly. |
| **Dataset Generation (T3/T4/Simulation)** | 60% | Code exists but Orekit dependency in production is problematic. Reference code also hadn't integrated T3/T4. |
| **Dataset Code System (16-char)** | 95% | All 10 fields properly encoded/decoded/validated. |
| **Data I/O Formats** | 95% | JSON schemas match documentation exactly for EO obs, TLEs, UCTP output. |
| **Web Platform (UI/UX)** | 90% | Exceeds original scope. Auth, multi-user, leaderboard, submission tracking. |
| **UCTP Output Validation** | 95% | Validates both SV and TLE formats. Accepts field name aliases. Covariance format checking. |
| **External Integrations** | 75% | UDL, ESA, Space-Track all working. Orekit fragile in production. ML labeling absent. |
| **Scoring/Ranking System** | 60% | Individual metrics correct. Missing composite weighted score for leaderboard. |
| **Event Labeling** | 15% | Infrastructure only. No real event data source. Doc noted ML model "not operating." |
| **Sensor Diversity** | 30% | Optical only in practice per Louis's own statement. |

**Overall Alignment: ~78%**

---

## Recommendations (Prioritized)

### Priority 1: Critical for Louis's Vision

1. **Implement Composite Scoring for Leaderboard**: Create a weighted scoring function combining F1 score, position RMS, and residual RMS into a single ranking metric. Add a `composite_score` column to `submission_results`. Louis explicitly described this multi-metric evaluation (Feb 19, lines 541-561). This is the most impactful gap in terms of the project's stated purpose.

2. **Ensure Orekit Availability in Production**: The evaluation pipeline is the core value proposition. Without Orekit, submissions can only be scored on binary metrics (observation correlation), not on state accuracy (orbit estimation quality) or residual metrics. This eliminates 2 of the 3 evaluation categories.

### Priority 2: Important but Acknowledged Limitations

3. **Accept Event Labeling Gap**: The Benchmarking Doc itself stated the ML Model was "not operating." This is an external dependency -- not a code gap. The database infrastructure is ready when event data becomes available.

4. **Accept Sensor Limitation**: Louis explicitly stated optical-only was the plan until the pipeline was proven. The schema is ready for radar/RF when data becomes available.

5. **Verify End-to-End Pipeline**: A submission should be uploaded, evaluated, and a PDF report generated in production. This is the MVP that Louis described (Jan 22): "they can upload their solution... we'll take their solution and we'll take the data set... and that's where we calculate the evaluation metrics."

### Priority 3: Enhancements

6. **Add trackTLE distinction**: If TLE-input UCTPs are to be supported, add a column or table to distinguish crude trackTLEs from refined UDL TLEs.

7. **Implement Target Object Percentage Enforcement**: The window selection algorithm should more rigorously enforce the 50%/10%/1% target object percentage when HAMR or special object types are requested.

8. **Consider Close/Apparent Object Filters**: The original doc noted these were "arbitrary" thresholds. If calibrated values become available, the existing `objectTypeFiltering.py` stubs can be completed.
