# UCT Benchmark Project: Single Source of Truth

**Version:** 1.0.0
**Date:** 2026-04-02
**Status:** Authoritative Reference Document
**Scope:** Complete vision, architecture, specifications, and implementation details derived from all provided materials, reference code, transcripts, PDFs, and active codebase.

---

## Table of Contents

1. [Project Identity and Mission](#1-project-identity-and-mission)
2. [Organizational Context](#2-organizational-context)
3. [The Problem: Why UCT Benchmarking Matters](#3-the-problem-why-uct-benchmarking-matters)
4. [The Common Task Framework Foundation](#4-the-common-task-framework-foundation)
5. [Project Goal and Vision](#5-project-goal-and-vision)
6. [Team Structure and Responsibilities](#6-team-structure-and-responsibilities)
7. [Dataset Generation Pipeline](#7-dataset-generation-pipeline)
8. [The 16-Character Dataset Code System](#8-the-16-character-dataset-code-system)
9. [Data Sources and API Integrations](#9-data-sources-and-api-integrations)
10. [Observation Data Formats](#10-observation-data-formats)
11. [UCT Processor Output Format](#11-uct-processor-output-format)
12. [Evaluation Pipeline](#12-evaluation-pipeline)
13. [Evaluation Metrics Specification](#13-evaluation-metrics-specification)
14. [Web Platform Architecture](#14-web-platform-architecture)
15. [Backend API Design](#15-backend-api-design)
16. [Frontend Application Design](#16-frontend-application-design)
17. [Database Architecture](#17-database-architecture)
18. [Authentication and Security](#18-authentication-and-security)
19. [Deployment and Infrastructure](#19-deployment-and-infrastructure)
20. [Configuration Constants and Thresholds](#20-configuration-constants-and-thresholds)
21. [Key Design Decisions from Stakeholder Meetings](#21-key-design-decisions-from-stakeholder-meetings)
22. [Implementation Status and Gaps](#22-implementation-status-and-gaps)
23. [Reference Code Lineage](#23-reference-code-lineage)
24. [Glossary of Terms](#24-glossary-of-terms)
25. [Document Sources and Traceability](#25-document-sources-and-traceability)

---

## 1. Project Identity and Mission

**Full Title:** Processing Uncorrelated Tracks (UCTs) in the Common Task Framework: Benchmark Dataset Generation and Evaluation Criteria

**Organizations:**
- **SDA TAP Lab** - Space Domain Awareness Tools, Applications, & Processing Lab (Space Systems Command, USSF)
- **SpOC** - Space Operations Command (USSF)
- **The Data Mine** - Purdue University's Data Mine living-learning community (academic partner)
- **AFRL** - Air Force Research Laboratory (2025 summer interns authored the original system documentation)

**Project Origin:** From the SpOC-SDA-Description.pdf:

> "SpOC in partnership with SDA TAP Lab developing [a] fully automated data annotation pipeline...following Donoho 2017 Common Task Framework. Open-source development community for space domain is very small with no widely accepted ontologies. Goal to accelerate delivery of space battle management software."

**Requirement Context:** This project requires U.S. citizenship. Project locations include West Lafayette, IN and the Rockies. Meeting schedule: Fall/Spring mentor time Thursday 3:30 PM Eastern, Fall/Spring lab time Tuesday 3:30 PM Eastern.

---

## 2. Organizational Context

### 2.1 Space Domain Awareness Crisis

From the SpOC-SDA-Description.pdf, the space domain is rapidly becoming congested:

- **Total Tracked Objects:** 45,100 (196% increase from 2008 to 2024)
- **Active Satellites on Orbit:** 10,200 (317% increase)
- **Worldwide Launches:** 177 in 2023 (203% growth per year)
- **Satellites Launched:** 2,621 in 2023 (2544% growth per year)
- **Debris Conjunctions:** 1,330 in 2023 (1108% growth per year)
- **SDA Operations:** 41,400 total (9% increase since Dec 31, 2021; 173% increase since 2011)
- **Active Spacecraft:** 10,000+

> "Global space industry projected to generate over $1 trillion in revenue by 2040, up from current $350 billion."

### 2.2 USSF Mission

> "Secure our nation's interests IN, FROM, and TO SPACE"

Three pillars:
1. **Assured Space Access:** Deploy and sustain equipment in space
2. **Space Superiority:** Defend against space and counterspace threats
3. **Global Mission Operations:** Globally integrate joint functions across all domains

### 2.3 SDA TAP Lab Mission

From the ProjectProposal.pdf:

> "Rapidly predict, detect, track, identify, warn, characterize, and attribute threats to U.S., commercial, allied, and partner space systems."

The TAP Lab operates under Apollo Accelerators: 3-month initiatives decomposing kill chains with industry, academia, and government partners.

### 2.4 Space Operations Command Structure

SpOC oversees Space Mission Deltas (2, 3, 4, 6, 7, 9) and Space Base Deltas (1, 2), covering:
- SDA and Electromagnetic Warfare (Delta 2)
- Missile Warning (Delta 4)
- Cyber Operations (Delta 6)
- Satellite Communications (Delta 7)
- Orbital Warfare (Delta 9)
- Navigational Warfare (Delta 3)

### 2.5 High Priority Common Tasks

From the project briefs, the high-priority common tasks in SDA are:
1. **UCT Processing** (this project's focus)
2. **State Estimation**
3. **Object Identification**

> "Software tools must pull event data from available sources, label according to predefined classifications, parse and extract measurement data, clean and store in centralized database."

---

## 3. The Problem: Why UCT Benchmarking Matters

### 3.1 What Are Uncorrelated Tracks?

From the Benchmarking Documentation (authored by 2025 AFRL Scholars, Rev 8/13/2025):

An **Uncorrelated Track (UCT)** is a track of observations (from telescopes, radars, or RF sensors) that cannot be matched to any known satellite in the catalog. A **UCT Processor (UCTP)** takes these unmatched observations and attempts to:
1. Determine the orbit of the unknown object
2. Correlate the observations to build a coherent track
3. Potentially match the object to a known catalog entry

### 3.2 The Benchmarking Gap

From Louis's January 22, 2026 presentation (Lewis_Transcript-1-22.md):

> "In our community, there is little agreement on the common task to be benchmarked, few benchmark data sets, and no consensus on the evaluation metrics. So, what we need to do is we need to bring elements of common task framework to the world of space domain awareness. We need to be able to agree on what it is we're trying to improve. We need to agree on how it needs to be improved, how we can evaluate the thing to make it better. And we need benchmark data sets that a standardized input such that when you feed it into your processor, you can get a standardized output that can then be evaluated."

### 3.3 The Common Task Framework Applied to UCT Processing

From Louis's presentation:

> "So what that looks like is a common task framework. So it starts with standardized data sets. The same data set will be fed into many different algorithms that you know exist in many different forms that are owned by many different people that are all meant to do a very similar thing and they'll all give a separate output. Then you evaluate them all based on the same evaluation metrics and that allows you to compare each one of these different things that are tested on the same data set and can be evaluated."

### 3.4 The Need for UCT Benchmarking

From the provided-materials "Need for UCT Benchmarking.pdf" and the LLNL Common Task Framework paper:

The open-source development community for the space domain is very small with no widely accepted ontologies. There are currently:
- No standardized benchmark datasets for UCT processing
- No agreed-upon evaluation metrics
- No platform for comparing different UCTP algorithms
- No systematic way to assess algorithm improvements

This project directly addresses all four gaps.

---

## 4. The Common Task Framework Foundation

### 4.1 Theoretical Basis

The project follows the Common Task Framework (CTF) described in Donoho's 2017 paper "50 Years of Data Science." The CTF accelerates progress in a field through three components:

1. **Standardized Datasets** - Publicly available benchmark datasets with known ground truth
2. **Standard Evaluation Metrics** - Agreed-upon measures of performance
3. **Public Leaderboard** - Transparent comparison of algorithm performance

### 4.2 CTF Applied to SDA (from the LLNL Paper)

From the provided-materials "A common task framework for testing and evaluation at the Space Domain Awareness" (both .docx and .pdf versions):

The paper describes applying the CTF methodology specifically to SDA tasks, with UCT Processing as the primary common task. It establishes:
- The rationale for standardized benchmarking
- The types of metrics appropriate for orbit determination
- The need for both synthetic and real data in benchmarks
- The importance of covering multiple orbital regimes

### 4.3 CTF at SDA TAP Lab

From the Learning Docs "CTF at SDA TAP Lab.docx":

The TAP Lab adopted the CTF methodology to create a systematic framework for:
- Generating datasets with controlled difficulty levels (tiers)
- Evaluating UCT processors against those datasets
- Comparing performance across multiple algorithms
- Tracking improvement over time through leaderboards

---

## 5. Project Goal and Vision

### 5.1 Primary Goal

From the SpOC-SDA-Description.pdf:

> "Develop benchmark dataset generation and evaluation criteria for processing UCTs in the Common Task Framework, resulting in a web-hosted user interface for algorithm developers to generate/download benchmark datasets and upload solutions for objective evaluation and comparison."

### 5.2 What the Platform Must Enable

From the README.md:

> "Build a Web-hosted User Interface where algorithm developers can:
> 1. Generate and download benchmark datasets for UCT Processing
> 2. Train their algorithms on standardized data
> 3. Upload results to be objectively evaluated
> 4. Compare performance against other solutions"

### 5.3 Louis's Vision for the Data Flow

From transcript.md (Louis Caves):

> "How is the data actually being queried, stored, and saved, right? So, like, we had that dataset code from before. We don't have to use that exact same naming convention if we don't want to, but all of those characters that represented something, all of those configurations that we had to begin with, we need all those same configurations in the user interface."

> "The data set observation should be a list of observations with the object association removed from each observation. When we make multiple datasets, we want to make sure those are stored as separate entries. Right now, it looks like it's just kind of stacking all of the observations and date vectors and everything else just right on top of each other."

> "So we want to make sure that our datasets are distinct, that our datasets have proper labeling conventions, and that we're still capturing all those same areas of interest that we wanted out of the data set."

### 5.4 Dataset Versioning Vision

From transcript.md (Louis Caves):

> "Well, my thoughts... if you did have a change, you want to have the ability to go back and look at the old data sets, but at the same time, look at the newer data sets."

### 5.5 Black Box UCTP Philosophy

From the Feb 19, 2026 meeting (2-19Transcript.md), Louis explicitly stated the project should NOT build its own UCTP:

> The team should focus on dataset generation and evaluation metrics instead. The evaluation pipeline is designed to work with any processor output if it follows the required schema. UCT Processors are treated as "black boxes" - the benchmark system doesn't need to know how they work internally.

### 5.6 MVP Focus

From the Feb 19, 2026 meeting:
- **Priority 1:** Complete dataset generation pipeline (user input -> UDL queries -> observation pulling -> state factors)
- **Priority 2:** Implement time window selection and tier scoring
- **Priority 3:** Determine when simulation vs downsampling is needed
- AI chatbot/globe visualization classified as "icing on the cake" - nice-to-have but not essential

---

## 6. Team Structure and Responsibilities

### 6.1 SDA TAP Lab Team

**Focus:** Labelling & Data Storage

**Key Deliverables:**
- UDL data pulling and API integration
- Event labelling (maneuvers, breakups, launches, proximity events)
- Centralized database for datasets and results
- Data ingestion pipeline
- Window selection algorithms
- Downsampling pipeline (T1/T2)
- Observation simulation (T3)

### 6.2 SpOC Team

**Focus:** Benchmark & Evaluation

**Key Deliverables:**
- Web UI (React frontend)
- Algorithm submission interface
- Evaluation metrics implementation
- Leaderboard system
- Backend API (FastAPI)
- PDF report generation

### 6.3 Key Personnel (from transcripts and documentation)

| Person | Role | Key Contributions |
|--------|------|-------------------|
| **Louis Caves** | Tech Lead (SDA TAP Lab) | Defined all specifications, dataset codes, evaluation metrics, pipeline architecture |
| **Jon Cline (Dr. Cline)** | Faculty Advisor / Architect | Created the refactored architecture (uct-benchmark-refactor-joncline branch), best code organization |
| **Jovan** | Developer | Linux testing branch, DuckDB integration, Polars data processing, setup automation |
| **Bryant Ortega** | Team Lead / Coordinator | Meeting facilitation, task assignment, project management |
| **Kelvin Benedict** | Developer | Web platform development, production deployment |
| **David Xiao** | Developer | UCTP analysis, evaluation pipeline |
| **James** | Developer | Data ingestion, dashboard, UDL query fixes |
| **Kara McCormick** | Developer | Team member |
| **Aidan Schlesinger** | Developer | Team member |
| **Major Sean Allen** | Military Advisor | Provided initial project motivation and context |
| **Patrick Ramsey** | Aerospace Corp | External UCTP developer for real-world validation |

### 6.4 Inter-Team Dependencies

From the DEPENDENCIES.md document:

**Critical handoffs:**
1. SDA TAP Lab must provide the database schema and API for SpOC's web UI
2. Event labelling (SDA TAP) feeds into dataset generation (shared)
3. Evaluation metrics (SpOC) depend on standardized data formats (SDA TAP)
4. Both teams share the propagator codebase (Orekit)

---

## 7. Dataset Generation Pipeline

### 7.1 Pipeline Overview

From the Benchmarking Documentation (AFRL Scholars, Rev 8/13/2025):

The dataset generation pipeline creates benchmark datasets with known ground truth for testing UCT processors. The complete workflow is:

```
User Input (Dataset Code or UI Configuration)
    |
    v
Time Window Selection
    |
    v
UDL API Queries (Observations + State Vectors + TLEs)
    |
    v
Basic Scoring (Tier Classification: T1/T2/T3/T4)
    |
    v
Object Type Filtering (if specified)
    |
    v
Event Filtering (if specified)
    |
    v
[If T2] Downsampling (3-stage pipeline)
    |
    v
[If T3] Observation Simulation (Orekit gap-filling)
    |
    v
Track Binning (group obs into tracks)
    |
    v
TrackTLE Generation (IOD on each track)
    |
    v
True Negative Addition (non-reference observations)
    |
    v
Decorrelation (strip satellite IDs)
    |
    v
Dataset Output (JSON with known ground truth)
```

### 7.2 Tier System

From the Benchmarking Documentation and Beginner Guide:

| Tier | Name | Description | Difficulty | Action Required |
|------|------|-------------|------------|-----------------|
| **T1** | Pristine | Full real observations meeting all criteria naturally | Easy | None - data used as-is |
| **T2** | Downsampled | Real observations strategically reduced | Medium | 3-stage downsampling |
| **T3** | Simulated | Gaps filled with simulated observations | Medium-Hard | Orekit simulation |
| **T4** | Fully Synthetic | Entirely synthetic satellites and observations | Hard | Full simulation |
| **T5** | Impossible | Criteria that cannot be physically achieved | N/A | Detection only (flag as impossible) |

### 7.3 Time Window Selection

From the Benchmarking Documentation:

> "Time Window Selection: The algorithm searches for time windows where the desired dataset characteristics can be met. Orbital Regime and Fitspan take precedence over track gap, so it may not be possible to achieve the desired track gap given the desired regime and fitspan (e.g. you cannot have a 2-period track gap for GEO objects with a 1-day fitspan)."

The window selection uses a bisection algorithm to find optimal observation windows meeting the quality criteria encoded in the dataset code.

### 7.4 Three-Stage Downsampling Pipeline

From the Benchmarking Documentation and Louis's specifications:

**Stage 1: Coverage Reduction** (`_lowerOrbitCoverage`)
- Remove observations to reduce the orbital coverage arc
- Target ranges vary per tier and orbital regime
- Preserves track structure (minimum 3 observations per track)

**Stage 2: Gap Widening** (`_increaseTrackDistance`)
- Remove observations to increase gaps between tracks
- A "long" track gap is defined as >2 orbital periods
- Maintains track integrity

**Stage 3: Observation Count Reduction** (`_downsampleAbsolute`)
- Reduce observations per satellite per 3-day timespan
- Uses time-binned approach to ensure even distribution
- Preserves track structure

### 7.5 Observation Simulation (T3)

From the Benchmarking Documentation:

> "Simulation of Observations: For data tiers requiring gap-filling, the system uses Orekit-based orbit propagation to generate synthetic observations. The simulateObs function creates RA/Dec observations from TLE using Orekit-generated ephemeris."

The simulation includes:
- Noise models per sensor type (position noise in meters, angular noise in degrees)
- Sensor visibility calculations
- Atmospheric effects
- Multiple sensor geometry

### 7.6 True Negatives

From the Benchmarking Documentation:

> "True Negatives: Non-reference observations are added to the dataset to create true negative cases. These are observations from satellites NOT in the reference set, making it impossible for a UCTP to correctly associate them. The system adds 2 non-reference observations per satellite by default, insufficient for Initial Orbit Determination (IOD), ensuring they cannot be correlated."

### 7.7 Decorrelation

From the Benchmarking Documentation:

> "Decorrelate: The process in which the state vector and associated observations or TLE and trackTLEs of a Reference Orbit are separated and stripped of NORAD IDs. This makes the observations 'Uncorrelated', which are used to create benchmark datasets that is fed into the UCTP."

### 7.8 TrackTLE Generation

From the code and documentation:

TrackTLEs are generated by performing Initial Orbit Determination (IOD) on individual tracks of observations. The pipeline uses:
1. Modified Gauss IOD for initial orbit estimate
2. BatchLSEstimator for orbit refinement
3. Conversion to TLE format for UCTP input

---

## 8. The 16-Character Dataset Code System

### 8.1 Code Structure

From the Benchmarking Documentation (the authoritative specification):

```
Position:  1     2-3    4-6    7-8   9-10   11    12    13    14    15-16
Meaning:   OBJ   TGT%   REG    EVT   SEN    COV   GAP   OBS   CNT   FIT
Example:   H     50     LEO    MB    OP     A     S     N     H     07
```

**Full code example:** `H50LEOMBOPASNH07`

### 8.2 Position 1: Target Object Type

| Code | Meaning | Definition |
|------|---------|------------|
| **H** | HAMR (High Area-to-Mass Ratio) | A/M ratio > 1.0 m²/kg |
| **C** | Close Objects | distance < X km AND velocity < X m/s |
| **A** | Close Apparent Objects | Angles within X degrees |
| **U** | Unspecified | Datasets unconstrained by object types |
| **N** | Calibration | Well-tracked objects only |

From the Benchmarking Documentation:

> "Note: Close objects and close apparent objects have not yet been implemented; these values are arbitrary until more research is conducted."

Potential Calibration/Well-tracked Satellites (NORAD IDs):
1328, 5398, 7646, 8820, 16908, 19751, 20026, 22195, 22314, 22824, 23613, 24876, 25544, 26360, 27566, 27944, 32711, 36508, 39070, 39086, 39504, 40730, 41240, 41335, 42915, 43476, 43477, 43873, 46826, 48859

### 8.3 Positions 2-3: Target Object Percentage

| Code | Meaning |
|------|---------|
| **50** | 50% of objects match target type |
| **10** | 10% of objects match target type |
| **01** | 1% of objects match target type |
| **UN** | Unspecified (any natural distribution) |

> "For target object type unspecified (U), this must be unspecified (UN) as well."

### 8.4 Positions 4-6: Orbital Regime

Semi-major axis *a* measured in km:

| Code | Regime | Definition |
|------|--------|------------|
| **LEO** | Low Earth Orbit | a <= 8378 km (mean altitude < 2000 km) |
| **MEO** | Medium Earth Orbit | 8378 < a < 42164 km |
| **GEO** | Geosynchronous Orbit | a >= 42164 km |
| **HEO** | Highly Elliptical Orbit | Eccentricity e >= 0.7 |
| **ALL** | All Regimes | Combined |
| **LMO** | LEO + MEO | Combination |
| **LMG** | LEO + MEO + GEO | Combination |
| **MGH** | MEO + GEO + HEO | Combination |

> "Designator for combination of 2 Regimes is the first letter of the two regimes in the order above, followed by an 'O'. EX: LEO/MEO -> 'LMO'"

### 8.5 Positions 7-8: Event Type

| Code | Meaning |
|------|---------|
| **MB** | Maneuver Between Observations |
| **BU** | Breakup |
| **LL** | Long Duration/Low Thrust |
| **NE** | No Events |

> "Only one type of event selection is allowed, as each event constrains the possible time windows in which the dataset can be generated. Since the UDL does not contain these events directly, we are relying on the ML Labelling Team to feed us the NORAD IDs and Observation times corresponding to these events. As of the writing of this report, the ML Model is not operating."

### 8.6 Positions 9-10: Sensor Type

| Code | Meaning |
|------|---------|
| **OP** | Optical |
| **RA** | Radar |
| **RF** | Radio Frequency |
| **FU** | Fusion of all sensor types |
| **OR** | Optical + RF |
| **RO** | Optical + Radar |
| **RR** | Radar + RF |

### 8.7 Position 11: Orbital Coverage Quality

| Code | Meaning |
|------|---------|
| **A** | >90% of objects have low orbital coverage (sparse/hard) |
| **S** | 40-60% of objects have low orbital coverage (standard/mixed) |
| **N** | <10% of objects have low orbital coverage (dense/easy) |

### 8.8 Position 12: Track Gap Quality

| Code | Meaning |
|------|---------|
| **A** | >90% of objects have a long track gap |
| **S** | 40-60% of objects have a long track gap |
| **N** | <10% of objects have a long track gap |

A "long" track gap = duration exceeding 2 orbital periods.

### 8.9 Position 13: Observation Count Quality

| Code | Meaning |
|------|---------|
| **A** | >90% of objects have low observation count |
| **S** | 40-60% of objects have low observation count |
| **N** | <10% of objects have low observation count |

Per 3-day timespan: "Low" = < 50 observations, "Standard" = 50-150, objects with > 150 either excluded or downsampled.

### 8.10 Position 14: Object Count

| Code | Count |
|------|-------|
| **H** | High: 80 +/- 2 objects |
| **S** | Standard: 40 +/- 2 objects |
| **L** | Low: 10 +/- 2 objects |

### 8.11 Positions 15-16: Fitspan (Days)

2-character integer between 01-14 representing the duration in days the dataset spans.

### 8.12 Enhanced Dataset Code Format (New)

The codebase also supports a newer 7-component format:

```
{OBJ}_{REG}_{EVT}_{SEN}_{QTY}_{WIN}_{VER}
Example: HAMR_LEO_NRM_EO_T2S_07D_001
```

Components:
- `OBJ`: Object type (HAMR, PROX, NORM, DEBR)
- `REG`: Orbital regime
- `EVT`: Event type (NRM, MAN, BRK, PRX)
- `SEN`: Sensor type (EO, RA, RF, MX)
- `QTY`: Quality tier + coverage/gap/obs levels
- `WIN`: Window duration
- `VER`: Version number

---

## 9. Data Sources and API Integrations

### 9.1 Unified Data Library (UDL)

**Primary data source.** From the Benchmarking Documentation:

> "UDL: Unified Data Library, the source of state vector and observation data used in this UCT evaluation product."

The UDL provides:
- **Observation services:** eoobservation, radarobservation, rfobservation, sarobservation, passiveradarobservation, gnssobservationset
- **State services:** statevector, elset, ephemeris, ephemerisset, orbitdetermination

**API Integration Details (from apiIntegration.py):**
- Authentication via Base64-encoded token
- Response caching: 900-second TTL, 1000-entry limit
- Rate limiting: 0.1s base delay, max 10 concurrent requests
- Smart query routing using count API for size estimation
- Async batch querying for parallel data retrieval

**Token Generation:**
```python
def UDLTokenGen(username, password):
    # Get UDL API token from credentials
```

**UDL v1.39.0 Impact (from UDL-v1.39.0-impact-analysis.md):**
- New 429 rate limiting on POST endpoints (HIGH severity)
- Must update retry logic with exponential backoff
- UTC timestamp 'Z' suffix requirements
- Future SCS migration considerations

### 9.2 ESA Discosweb

Provides satellite physical properties (mass, cross-sectional area) needed for:
- Atmospheric drag modeling
- Solar radiation pressure calculations
- HAMR classification (area-to-mass ratio)

### 9.3 Space-Track

From the reference code and documentation:
- TLE catalog access
- Historical TLE data
- Satellite catalog information

### 9.4 CelesTrak

- Public satellite data
- TLE data in various formats
- Supplemental catalog information

---

## 10. Observation Data Formats

### 10.1 EO Observation Dataset Format

From the Benchmarking Documentation, observations are in JSON format:

```json
{
    "id": "9dabe8c8-2f14-4c63-9a3d-2d810f54e3e2",
    "classificationMarking": "U//PR-EXO-OBS",
    "obTime": "2025-06-23T19:45:00.225171Z",
    "idOnOrbit": "41586",
    "idSensor": "EXO7151",
    "satNo": 41586,
    "uct": false,
    "azimuth": 310.5277466167,
    "elevation": 53.0376017287,
    "range": 36903.668121356,
    "ra": 314.8563772662,
    "declination": 1.9389976251,
    "senlat": -23.767372,
    "senlon": 133.915083,
    "senalt": 0.545,
    "mag": 13.214783,
    "type": "OPTICAL"
}
```

**Fields used by evaluation:** `"id"`, `"obTime"`, `"satNo"`, `"uct"`, `"ra"`, `"declination"`

### 10.2 TLE Dataset Format

```json
{
    "idElset": "d688d8a2-81d3-4ceb-8032-c945128b5a41",
    "epoch": "2025-07-02T20:50:51.681027Z",
    "meanMotion": 1.0027191749074,
    "eccentricity": 0.00500568344535229,
    "inclination": 6.64966633097932,
    "raan": 15.1408773270208,
    "argOfPerigee": 49.8819406821671,
    "meanAnomaly": 274.278737836812,
    "semiMajorAxis": 42164.6968714354,
    "line1": "1 99999U 00000A   25183.86865372...",
    "line2": "2 99999   6.6497  15.1409 0050057..."
}
```

### 10.3 Dataset Output Structure

From apiIntegration.saveDataset:

```json
{
    "dataset_obs": "DataFrame of decorrelated observations",
    "dataset_elset": "DataFrame of decorrelated track TLEs",
    "reference": {
        "groupedObs": "Truth observations grouped by satellite",
        "groupedObsIds": "Truth observation IDs",
        "groupedElsets": "Truth TLEs grouped by satellite",
        "groupedElsetIds": "Truth TLE IDs"
    }
}
```

---

## 11. UCT Processor Output Format

### 11.1 State Vector Output

From the Benchmarking Documentation:

```json
{
    "idStateVector": "unique alphanumeric string",
    "grouped_ops": ["observation ID", "observation ID"],
    "source_data_types": ["EO", "EO", "EO"],
    "epoch": "yyyy-mm-ddThh:mm:ss.ssssssZ",
    "xpos": "float in units of km",
    "ypos": "float",
    "zpos": "float",
    "xvel": "float in units of km/s",
    "yvel": "float",
    "zvel": "float",
    "referenceFrame": "J2000",
    "covReferenceFrame": "J2000",
    "cov": "list of 21 values giving lower triangular elements of covariance matrix"
}
```

> "Of these fields, the entries used are 'grouped_ops' (alias: sourcedData), 'epoch', 'xpos', 'ypos', 'zpos', 'xvel', 'yvel', 'zvel', 'referenceFrame', 'covReferenceFrame', 'cov'."

### 11.2 TLE Output

```json
{
    "idElset": "57887e64-85fd-40f5-a65d-cfb8acb99ec1",
    "epoch": "yyyy-mm-ddThh:mm:ss.ssssssZ",
    "meanMotion": 12.872373104667524,
    "eccentricity": 0.0005349967465871388,
    "inclination": 62.389226664716325,
    "line1": "1 99999U 00000A   25168.40556060...",
    "line2": "2 99999  62.3892 109.9230 0005350...",
    "grouped_ops": ["idElset", "idElset"],
    "source_data_types": ["ELSET", "ELSET"]
}
```

### 11.3 Key Schema Requirement

From the Feb 19, 2026 meeting:

> "Output field names must match expected schema or evaluation pipeline will fail. Can include extra fields but cannot omit required ones."

The `grouped_ops` (alias: sourcedData) field is critical: it contains the list of observation IDs or TLE IDs that the UCTP has correlated to each determined orbit. This is what enables binary classification metrics.

---

## 12. Evaluation Pipeline

### 12.1 Pipeline Overview

From the Benchmarking Documentation and Evaluation.py:

```
Load Dataset (output_dataset.json)
    |
    v
Load UCTP Output (uctp_output.json)
    |
    v
Frame Conversion (all frames -> J2000/EME2000)
    |
    v
Orbit Association (Hungarian algorithm)
    |
    v
State Metrics (position/velocity errors)
    |
    v
Binary Classification Metrics (TP/TN/FP/FN)
    |
    v
Residual Metrics (observation fit quality)
    |
    v
Evaluation Report (PDF + JSON)
```

### 12.2 Frame Conversion

From the Benchmarking Documentation:

> "Reference frame for each reference state vector is specified as either J2000, EFG/TDR, ECR/ECEF, TEME, ITRF, or GCRF in the UDL. Each candidate state vector frame is specified as one of the above by the UCT processor output. Every state vector (both reference and candidate) that is given in a frame that is not J2000 is converted to the J2000 frame using the getTransformTo method of the orekit Frame class. The J2000 frame all state vectors are converted into is referred to in orekit as EME2000."

### 12.3 Orbit Association

From the Benchmarking Documentation:

> "UCTP Output data is expected to be agnostic with respect to satellite IDs (as they are unknown when dataset provided), and the user is not expected to associate their output with the satellite catalog. As such, the Evaluation framework will associate UCTP Output data with reference orbital data."

**Algorithm:** Modified Jonker-Volgenant algorithm (linear sum assignment) via scipy:

> "This is done by solving an optimal assignment problem between reference and candidate orbits using a modified Jonker-Volgenant algorithm with no initialization implemented using scipy."

**Cost Matrix Construction:**
1. For each reference/candidate orbit pair, propagate reference orbit to candidate's epoch using Orekit
2. Take the 6D vector difference between propagated reference and candidate
3. Assign L2 norm of that difference as cost

**Edge Cases:**
- Equal reference and candidate orbits: 1:1 mapping
- More reference orbits: 1:1 assignment, outstanding references marked as "satellite tracks not correlated"
- More candidate orbits: 1:1 assignment, outstanding candidates marked as "nonassociated/fictitious orbit states"

### 12.4 Calibration Philosophy

From the Feb 19, 2026 meeting (Louis's explanation):

> "Calibration uses physics/engineering principles rather than multiple processor examples. Does not require external processors to calibrate the scoring scale."

The evaluation is self-contained - it doesn't need other UCTP outputs to establish a baseline. The metrics are absolute measures based on orbital mechanics.

### 12.5 Evaluation Report Output

From the Benchmarking Documentation:

> "An evaluation report will be generated and saved as a PDF file at the end of the evaluation algorithm. It contains tables that show Associated Orbits, Binary Metrics, and State results. It also contains graphs showing the residuals of both the Candidate and Reference Orbits. At the top of the PDF, there is the Dataset code so the UCTP can tell exactly what kind of data was used in their testing."

---

## 13. Evaluation Metrics Specification

### 13.1 Binary Classification Metrics

From the Benchmarking Documentation:

**Primary Classifications:**

| Classification | Definition |
|----------------|------------|
| **True Positive (TP)** | Observation belongs to both the Candidate Orbit and the Reference Orbit to which it has been associated |
| **True Negative (TN)** | Observation does not belong to any Candidate Orbit or Reference Orbit |
| **False Positive (FP)** | Observation belongs to a Candidate Orbit but not the Reference Orbit to which it has been associated |
| **False Negative (FN)** | Observation does not belong to a Candidate Orbit but does belong to the Reference Orbit to which it has been associated |

**Derived Metrics:**

| Metric | Formula |
|--------|---------|
| **Accuracy** | (TP + TN) / (TP + FP + TN + FN) |
| **Recall/Sensitivity** | TP / (TP + FN) |
| **Balanced Accuracy** | (1/2) [TP/(TP+FN) + TN/(TN+FP)] |
| **Cohen's Kappa** | Standard kappa coefficient formula |
| **Matthews Correlation Coefficient** | [(TP)(TN)-(FP)(FN)] / sqrt[(TP+FP)(TP+FN)(TN+FP)(TN+FN)] |
| **Precision/PPV** | TP / (TP + FP) |
| **F1 Score** | (2*TP) / (2*TP + FP + FN) |
| **Specificity** | TN / (TN + FP) |

### 13.2 State Metrics

From the Benchmarking Documentation:

> "These metrics are conducted to determine the accuracy of candidate orbits to the reference orbits."

For each reference/candidate pair:
1. **L2 Norm** of position difference (km)
2. **L2 Norm** of velocity difference (km/s)
3. **L2 Norm** of total 6D state difference
4. **Mahalanobis Distance** between reference and candidate using combined covariance
5. **Mahalanobis p-score** using chi-squared distribution (confidence that orbits are the same)
6. **NEES (Normalized Estimation Error Squared)** using candidate covariance
7. **NEES p-score** (p < 0.5 = overconfident processor, p > 0.5 = underconfident processor)

### 13.3 Residual Metrics

From the Benchmarking Documentation:

> "Residual Metrics determine the unit-sphere projected great circle residuals between the actual observations or trackTLEs and the estimated observations or trackTLEs determined by propagating the Candidate Orbit to the epoch of each observation or trackTLE."

**Two categories:**
1. **Accuracy Residuals:** Compare reference observations with candidate orbit (how accurate the candidate is to truth)
2. **Precision Residuals:** Compare candidate's own sourced observations with candidate orbit (how self-consistent the candidate is)

**Output per satellite:**
- Observation IDs, epochs, individual residuals
- RMSE of residuals
- Mean of residuals
- Standard deviation of residuals

### 13.4 What Good Results Look Like

From the Beginner Guide:

| Metric | Good | Excellent |
|--------|------|-----------|
| Precision | >0.8 | >0.95 |
| Recall | >0.8 | >0.95 |
| F1 Score | >0.8 | >0.95 |
| Position Error | <10 km | <1 km |

---

## 14. Web Platform Architecture

### 14.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UCT BENCHMARK SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Web Frontend  │  │   Backend API   │                  │
│  │   (React/TS)    │──│   (FastAPI/Py)  │                  │
│  │   Port 80/443   │  │   Port 8000     │                  │
│  └─────────────────┘  └────────┬────────┘                  │
│                                │                            │
│                       ┌────────┴────────┐                  │
│                       │  Python Core    │                  │
│                       │  Pipeline       │                  │
│                       │  (uct_benchmark)│                  │
│                       └────────┬────────┘                  │
│                                │                            │
│                ┌───────────────┼───────────────┐           │
│                │               │               │           │
│         ┌──────┴──────┐ ┌─────┴─────┐ ┌──────┴──────┐    │
│         │  PostgreSQL │ │  Orekit   │ │  UDL/ESA    │    │
│         │  (Supabase) │ │  (Java17) │ │  APIs       │    │
│         └─────────────┘ └───────────┘ └─────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 14.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18+, TypeScript, Vite | Web UI |
| **UI Framework** | Tailwind CSS, shadcn/ui | Component library |
| **State Management** | Zustand (auth), TanStack React Query (server) | Client state |
| **Charts** | Recharts | Data visualization |
| **Backend** | FastAPI (Python 3.12+) | REST API |
| **Auth** | Supabase (ES256 JWKS) | Authentication/Authorization |
| **Database (Prod)** | PostgreSQL via Supabase | Production persistence |
| **Database (Dev)** | DuckDB | Local development |
| **Orbit Propagation** | Orekit via orekit-jpype (Java 17+) | Orbital mechanics |
| **Deployment** | Railway, Docker, nginx | Hosting |
| **CI/CD** | GitHub Actions | Automated testing/deployment |
| **Error Tracking** | Sentry | Monitoring |

---

## 15. Backend API Design

### 15.1 API Endpoints

From the backend_api/routers/ implementation:

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/api/v1/datasets/` | List and filter datasets | Yes |
| `POST` | `/api/v1/datasets/` | Create/generate a new dataset | Yes |
| `GET` | `/api/v1/datasets/{id}` | Get dataset details | Yes |
| `DELETE` | `/api/v1/datasets/{id}` | Delete a dataset | Yes (admin) |
| `GET` | `/api/v1/datasets/{id}/download` | Download dataset JSON | Yes |
| `POST` | `/api/v1/submissions/` | Submit algorithm output for evaluation | Yes |
| `GET` | `/api/v1/submissions/` | List user's submissions | Yes |
| `GET` | `/api/v1/results/{submission_id}` | View evaluation results | Yes |
| `GET` | `/api/v1/leaderboard/` | Leaderboard rankings | Yes |
| `GET` | `/api/v1/leaderboard/history` | Leaderboard trend data | Yes |
| `GET` | `/api/v1/leaderboard/statistics` | Aggregate statistics | Yes |
| `GET` | `/api/v1/jobs/` | List background jobs | Yes |
| `GET` | `/api/v1/jobs/{id}` | Job status and progress | Yes |
| `POST` | `/api/v1/feedback` | Submit user feedback | Optional |
| `GET` | `/api/v1/feedback/` | List feedback (admin) | Yes (admin) |
| `POST` | `/api/v1/auth/verify` | Verify JWT token | Yes |
| `GET` | `/api/v1/auth/me` | Get user profile | Yes |
| `PATCH` | `/api/v1/auth/me` | Update user profile | Yes |
| `PUT` | `/api/v1/credentials/{service_name}` | Save API credentials | Yes |
| `GET` | `/api/v1/credentials/` | List saved credentials | Yes |
| `DELETE` | `/api/v1/credentials/{service}` | Delete credentials | Yes |
| `POST` | `/api/v1/credentials/{service_name}/test` | Test credential validity | Yes |
| `GET` | `/health` | Health check (no auth) | No |

### 15.2 Background Job System

Dataset generation is async, using in-process job management:

```python
# From start.py:
# JobManager stores job state in-process memory,
# so multiple workers cause job-status 404s. Do NOT raise this default
# until JobManager is migrated to a shared backend (Redis / Celery / ARQ).
workers = int(os.environ.get("WEB_WORKERS", "1"))
```

Progress tracking via SSE (Server-Sent Events) with stages:
- Validating configuration
- Querying UDL API
- Pulling observations
- Running scoring
- Downsampling/Simulation
- Generating report
- Complete

### 15.3 Rate Limiting

From the DEPLOYMENT.md:
- 10/minute on dataset listing
- 5/minute on feedback submission
- 5/minute on report generation
- Per-IP using rightmost X-Forwarded-For

### 15.4 Additional Endpoints

The following endpoints exist in the codebase but are not listed in the primary table above:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/datasets/config` | Get dataset configuration options |
| `GET` | `/api/v1/datasets/{id}/versions` | List dataset versions |
| `GET` | `/api/v1/datasets/{id}/observations` | Get dataset observations |
| `POST` | `/api/v1/datasets/{id}/link-observations` | Link observations to dataset |
| `PATCH` | `/api/v1/datasets/{id}/coverage` | Update dataset coverage |
| `POST` | `/api/v1/datasets/legacy` | Create dataset from legacy 16-char code |
| `GET` | `/api/v1/datasets/code/{legacy_code}` | Lookup dataset by legacy code |
| `GET` | `/api/v1/datasets/validate/{code}` | Validate a dataset code |
| `GET` | `/api/v1/submissions/{id}` | Get submission details |
| `POST` | `/api/v1/submissions/{id}/results` | Attach results to submission |
| `GET` | `/api/v1/results/` | List evaluation results |
| `GET` | `/api/v1/results/{id}/metrics` | Get result metrics |
| `GET` | `/api/v1/results/{id}/visualization` | Get result visualization data |
| `GET` | `/api/v1/results/{id}/export` | Export result data |
| `GET` | `/api/v1/results/{id}/report` | Get evaluation report (PDF) |
| `GET` | `/api/v1/credentials/{service_name}` | Get credentials for a service |
| `GET` | `/api/v1/events/types` | List event types |
| `GET` | `/api/v1/events/` | List events |
| `GET` | `/api/v1/events/{id}` | Get event details |
| `POST` | `/api/v1/events/detect` | Detect events |
| `DELETE` | `/api/v1/events/{id}` | Delete an event |
| `GET` | `/api/v1/feedback/{id}` | Get feedback details |
| `PATCH` | `/api/v1/feedback/{id}` | Update feedback |

---

## 16. Frontend Application Design

### 16.1 Pages Implemented

| Page | Route | Description |
|------|-------|-------------|
| **Landing** | `/welcome` | Public marketing page with hero, capabilities, tiers, CTA |
| **Login** | `/login` | Authentication (login, signup, password reset) via Supabase |
| **Dashboard** | `/` | Authenticated home: stats, quick actions, recent submissions, leaderboard snapshot |
| **Dataset Browser** | `/datasets` | Browse public datasets with regime/tier/sensor filters, grid/list view |
| **Dataset Generator** | `/datasets/generate` | Multi-step wizard for creating custom datasets |
| **My Datasets** | `/datasets/my-datasets` | User's generated datasets with download/delete |
| **Dataset Detail** | `/datasets/:id` | Individual dataset view with observation preview |
| **Submit** | `/submit` | Upload algorithm output with multi-step validation |
| **My Submissions** | `/submit/my-submissions` | Submission history with status tracking |
| **Results** | `/results/:id` | Detailed metrics: binary, state, residual, per-satellite, histograms |
| **Leaderboard** | `/leaderboard` | Rankings with podium, filters, trend charts |
| **Profile** | `/profile` | User account management, API keys, notifications |
| **Settings** | `/settings` | Service credentials (UDL/ESA), application config |
| **Documentation** | `/docs` | Getting started, dataset format, submission format, metrics, pipeline |
| **404** | `*` | Not found page |

### 16.2 Dataset Generator Wizard

The generator is a multi-step wizard (~28K tokens of code) supporting:

1. **Step 1:** Orbital regime selection (LEO, MEO, GEO, HEO, ALL, LMO, LMG, MGH)
2. **Step 2:** Data tier and quality configuration
3. **Step 3:** Observation density, track gap, downsampling parameters
4. **Step 4:** Simulation options (gap filling, sensor model, noise)
5. **Review:** Full configuration summary before submission
6. **Generation:** Real-time progress monitoring

Also supports legacy 16-character dataset code entry.

### 16.3 Submission Validation Pipeline

The submit page implements multi-step validation:
1. File format validation (must be JSON)
2. UCTP schema validation (required fields present)
3. Observation ID reference validation (IDs match dataset)
4. State vector/TLE validation (physical plausibility)
5. Covariance format checking (21 lower-triangular elements)

### 16.4 Results Visualization

- Binary metrics display: TP, TN, FP, FN, Precision, Recall, F1, Accuracy, Specificity
- State metrics: Position RMS, Velocity RMS, Mahalanobis Distance
- Residual analysis: RA/Dec RMS in arcseconds
- Per-satellite breakdown table
- Histograms for residual distribution and position error
- Export to JSON, CSV, PDF

### 16.5 Leaderboard Display

- Top 3 podium with 1st/2nd/3rd styling
- Sortable table: F1-Score (primary), Precision, Recall, Position RMS
- Filters: Regime, Tier, Time period (all/month/week), Dataset
- Trend chart showing F1-score history over time

---

## 17. Database Architecture

### 17.1 Dual Backend Support

The system supports two database backends via the adapter pattern:

| Feature | DuckDB (Dev) | PostgreSQL (Prod) |
|---------|-------------|-------------------|
| Storage | Local file | Supabase cloud |
| Auth | Optional | Required (Supabase JWT) |
| Encryption | Plaintext allowed | Fernet required |
| Migrations | Schema.py auto-init | Alembic + Schema.py fallback |
| Multi-user | Limited | Full support |

### 17.2 Core Tables

From the database_erd.md:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `satellites` | NORAD catalog, physical properties | sat_no, name, object_type, regime, mass, area |
| `observations` | EO/radar/RF observations | id, ob_time, sat_no, sensor_id, ra, declination, type |
| `state_vectors` | Position/velocity vectors | id, epoch, x/y/z pos/vel, covariance (JSON) |
| `element_sets` | TLE lines, orbital elements | id, epoch, mean_motion, eccentricity, inclination, line1, line2 |
| `datasets` | Dataset metadata | id, name, code, tier, regime, user_id, status, generation_params |
| `dataset_observations` | Junction: dataset <-> observations | dataset_id, observation_id |
| `submissions` | Algorithm outputs | id, dataset_id, user_id, algorithm_name, status |
| `submission_results` | Evaluation results | id, submission_id, metrics (JSON) |
| `events` | Detected orbital events | id, norad_id, event_type, epoch, confidence |
| `profiles` | User profiles | id, email, display_name, organization, role |
| `feedback` | User feedback/bug reports | id, user_id, description, screenshot, page_url |
| `credentials` | Encrypted API tokens | id, user_id, service, encrypted_token |

**Additional tables:** `dataset_references`, `jobs`, `event_types`, `event_observations`, `non_reference_observations`, `breakup_events`, `_schema_metadata`

### 17.3 Schema Version

Current schema version: 2.0.0 (matching production Supabase database)

### 17.4 Repository Pattern

Data access is abstracted through repositories:
- `SatelliteRepository`
- `ObservationRepository`
- `StateVectorRepository`
- `ElementSetRepository`
- `DatasetRepository`
- `EventRepository`

---

## 18. Authentication and Security

### 18.1 Authentication Architecture

From DEPLOYMENT.md:

- **Production:** ES256 asymmetric key verification via Supabase JWKS endpoint at `SUPABASE_URL/auth/v1/.well-known/jwks.json`
- **Development:** Auth disabled when `ENVIRONMENT=development`
- **HS256 fallback:** Available in non-production environments only when `ALLOW_HS256_FALLBACK=true`

### 18.2 Roles

| Role | Access |
|------|--------|
| `authenticated` (default) | Standard user access to own data |
| `evaluator` | Can evaluate submissions and view detailed results |
| `admin` | Full access to all data and management endpoints |

Roles managed via Supabase `app_metadata.role` (server-side only, not user-editable).

### 18.3 Security Features

- **Encrypted Token Storage:** Fernet symmetric encryption for all 6 external service tokens (UDL, ESA, Space-Track, SatNOGS, CelesTrak, Orekit)
- **CORS:** Configurable origins (never `*` in production)
- **Rate Limiting:** slowapi with per-IP limits
- **Security Headers:** CSP, HSTS (1-year), X-Frame-Options: DENY, X-Content-Type-Options: nosniff
- **User Scoping:** Data queries scoped to authenticated user unless admin
- **Non-root Docker:** Application runs as `appuser`, not root

---

## 19. Deployment and Infrastructure

### 19.1 Architecture

```
GitHub (master branch) ──> Railway Production Environment
GitHub (dev branch)    ──> Railway Demo Environment
```

### 19.2 Production Stack

- **Backend:** Eclipse Temurin Java 17 + Python 3.12 (Orekit + FastAPI)
- **Database:** Supabase PostgreSQL
- **Frontend:** nginx with reverse proxy to backend
- **Memory:** 2GB recommended (JVM + Orekit)

### 19.3 Demo Stack

- **Backend:** Python 3.12 only (no Java/Orekit)
- **Database:** DuckDB (ephemeral)
- **Auth:** Disabled (DEMO_MODE=true)
- **Memory:** 256MB sufficient

### 19.4 Required Environment Variables

**Production Backend:**

| Variable | Description |
|----------|-------------|
| `DATABASE_BACKEND` | `postgres` |
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_JWT_SECRET` | JWT secret for token verification |
| `ENCRYPTION_KEY` | Fernet key for token encryption |
| `CORS_ORIGINS` | Frontend URL |
| `ENVIRONMENT` | `production` |
| `PORT` | Server port (default: 8000) |
| `WEB_WORKERS` | Number of Uvicorn workers (default: 1) |
| `SENTRY_DSN` | Sentry error tracking DSN |
| `ALLOW_HS256_FALLBACK` | Allow HS256 JWT fallback (non-production only) |

**Production Frontend:**

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | `http://backend.railway.internal:8000` |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `VITE_API_BASE_URL` | Must include `/api/v1` prefix |

### 19.5 CI/CD Pipeline

> **Status:** Implementation in progress. GitHub Actions workflows being created.

On push to `master` or `dev`:
1. **Test** - pytest (backend) + tsc type check (frontend)
2. **Deploy Backend** - `railway up --service backend`
3. **Deploy Frontend** - `npm run build` + `railway up --service frontend`

### 19.6 Database Backups

> **Status:** Implementation in progress. Backup workflow being created.

- Automated daily backups at 2:00 UTC via GitHub Actions
- `pg_dump` with gzip compression, uploaded as GitHub artifacts
- 30-day retention with restore verification

### 19.7 Health Monitoring

- `/health` endpoint checks database connectivity and disk space
- Structured audit logging for sensitive operations
- Request correlation IDs via middleware
- Sentry integration for error tracking (frontend + backend)

---

## 20. Configuration Constants and Thresholds

### 20.1 Orbital Regime Boundaries

From settings.py and the Benchmarking Documentation:

| Regime | Semi-Major Axis | Eccentricity |
|--------|----------------|--------------|
| LEO | a <= 8378 km | - |
| MEO | 8378 < a < 42164 km | - |
| GEO | a >= 42164 km | - |
| HEO | any | e >= 0.7 |

### 20.2 Coverage Thresholds ("Low" Coverage)

| Regime | Low Coverage Threshold |
|--------|----------------------|
| LEO | < 0.0213 (fraction, ~2.13%) |
| MEO | < 0.0449 (fraction, ~4.49%) |
| GEO | < 0.41656 (fraction, ~41.7%) |

### 20.3 Track and Observation Thresholds

| Parameter | Value | Source |
|-----------|-------|--------|
| Long track gap multiplier | 2.0x orbital period | Benchmarking Documentation |
| Low observation count | < 50 per 3-day span | Benchmarking Documentation |
| Standard observation count | 50-150 per 3-day span | Benchmarking Documentation |
| Max observation count | > 150 (downsample or exclude) | Benchmarking Documentation |
| Track binning cutoff | 90 minutes | binTracks() default |
| Min observations per track | 3 | Downsampling preservation |

### 20.4 Object Type Thresholds

| Parameter | Value |
|-----------|-------|
| HAMR threshold | > 1.0 m²/kg |
| Close object distance | < 100 km |
| Close object velocity | < 100 m/s |
| Close apparent angular | < 0.5 degrees |
| Non-reference obs per satellite | 2 (insufficient for IOD) |

### 20.5 Object Count Targets

| Code | Count |
|------|-------|
| H (High) | 80 +/- 2 |
| S (Standard) | 40 +/- 2 |
| L (Low) | 10 +/- 2 |

### 20.6 Quality Level Thresholds

| Level | % with Low Coverage | % with Long Gap | % with Low Obs Count |
|-------|--------------------|-----------------|--------------------|
| A (Sparse/Hard) | >90% | >90% | >90% |
| S (Standard) | 40-60% | 40-60% | 40-60% |
| N (Dense/Easy) | <10% | <10% | <10% |

### 20.7 Propagator Configuration

From the Benchmarking Documentation:

| Parameter | Value |
|-----------|-------|
| Integrator | DormandPrince853 |
| Min step size | 0.0001s |
| Max step size | 1000s |
| Relative tolerance | 10E-14 |
| Absolute tolerance | 10E-12 |
| Earth gravity | Holmes-Featherstone, harmonics to degree/order 120 |
| Third body | Sun + Moon (point masses) |
| Atmosphere | NRLMSISE-00 + CSSI space weather |
| Drag | Isotropic, ESA cross-sectional area + UDL drag coefficient |
| Solar radiation pressure | Isotropic, same area + SRP coefficient, with umbra/penumbra |
| Satellite mass | From ESA database |

### 20.8 Default Noise Parameters

| Parameter | Value |
|-----------|-------|
| Position noise | From config.positionNoise (meters) |
| Angular noise | 1/3600 degree (1 arcsecond) default |
| Simulation step | 10 seconds |

### 20.9 API Rate Limits

| Parameter | Value |
|-----------|-------|
| UDL base delay | 0.1 seconds |
| Max concurrent UDL requests | 10 |
| UDL cache TTL | 900 seconds |
| UDL cache max entries | 1000 |
| JVM memory limit | 256MB + 128MB metaspace |

---

## 21. Key Design Decisions from Stakeholder Meetings

### 21.1 From Louis's Initial Presentation (Jan 22, 2026)

**Decision 1: Common Task Framework Approach**

> "What we need to do is we need to bring elements of common task framework to the world of space domain awareness."

The project follows Donoho's CTF methodology rather than building a custom evaluation framework.

**Decision 2: Standardized Input/Output**

> "We need benchmark data sets that a standardized input such that when you feed it into your processor, you can get a standardized output that can then be evaluated."

All datasets and outputs must conform to defined JSON schemas.

**Decision 3: Dataset Characteristics Encoding**

> "All of those characters that represented something, all of those configurations that we had to begin with, we need all those same configurations in the user interface."

The 16-character dataset code system must be fully represented in the web UI.

### 21.2 From Louis's Data Storage Guidance (transcript.md)

**Decision 4: Distinct Datasets**

> "We want to make sure that our datasets are distinct, that our datasets have proper labeling conventions."

Each generated dataset must be a separate, uniquely identified entry - not stacked on top of previous datasets.

**Decision 5: Dataset Versioning**

> "If you did have a change, you want to have the ability to go back and look at the old data sets, but at the same time, look at the newer data sets."

The system must support viewing historical versions of datasets.

### 21.3 From Feb 19, 2026 Meeting (2-19Transcript.md)

**Decision 6: No Custom UCTP**

Louis explicitly stated the team should NOT build its own UCTP. The processors are "black boxes" - the benchmark system evaluates their output, not their internals.

**Decision 7: Self-Contained Calibration**

The evaluation pipeline calibrates using physics/engineering principles, not by running multiple processors. No external processor is needed to establish a scoring baseline.

**Decision 8: UDL Query by Time Window**

James fixed the dashboard dataset generation by querying UDL by observation time instead of satellite number. Louis confirmed this is the correct approach for user-specified time windows.

**Decision 9: Required Schema Fields**

From the Feb 19, 2026 meeting:
- Observations need: ID, op time, sensor ID, azimuth, elevation, range, RA, declination
- UCTP output must include: state vector fields (X/Y/Z position/velocity), source data IDs, epoch
- Extra fields are allowed but required fields cannot be omitted

**Decision 10: MVP over Polish**

Louis classified AI chatbot and 3D globe visualization as "icing on the cake." The team should focus on:
1. Complete dataset generation pipeline
2. Time window selection and tier scoring
3. Downsampling vs. simulation logic

**Decision 11: GitLab Migration**

The project should eventually move to TapLab GitLab (currently private repository). Students work on GitHub while waiting for GitLab access.

**Decision 12: Data Missingness Analysis**

The data ingestion team should analyze missingness patterns (random vs correlated) to determine optimal imputation/simulation methods.

### 21.4 From Transcript Alignment Analysis

**Decision 13: TIER_5 Impossible Detection**

When window selection determines that the requested criteria are physically impossible (e.g., 2-period track gap for GEO with 1-day fitspan), the system flags this as TIER_5 rather than failing silently.

**Decision 14: Regime-Specific Coverage Thresholds**

The UI coverage slider must use regime-specific thresholds (LEO: 0.0213, MEO: 0.0449, GEO: 0.41656 -- fractions, not percentages) rather than a single value.

---

## 22. Implementation Status and Gaps

### 22.1 Current Status (as of April 2, 2026)

From PROJECT_STATUS.md and audit reports:

**Overall Progress: ~95% code complete**

> "Important Note: Progress percentages reflect code completion, not validation status. The evaluation report 'looks sporadic because it's just random data to validate that the algorithm works. This is not actually representative of a UCT processor.' - Lewis"

### 22.2 Component Status

| Component | Status | Progress |
|-----------|--------|----------|
| API Integrations (UDL, ESA) | Complete | 95% |
| Window Selection | Complete | 95% |
| Basic Scoring (Tier Classification) | Complete | 90% |
| Propagators (Orekit) | Complete | 95% |
| Evaluation Metrics (Binary/State/Residual) | Complete | 90% |
| Orbit Association (Hungarian Algorithm) | Complete | 95% |
| Observation Simulation (T3) | Complete | 95% |
| Downsampling Pipeline (T1/T2) | Complete | 100% |
| TIER_5 Detection | Complete | 100% |
| TrackTLE Pipeline (IOD + BatchLSEstimator) | Complete | 90% |
| Object Type Filters (HAMR, Close, Proximity) | Complete | 90% |
| Event Labelling | Partial (ML Fallback) | 40% |
| T4 Processing (Fully Synthetic) | Not Started | 0% |
| Web UI (React) | Complete | 90% |
| Backend API (FastAPI) | Complete | 90% |
| Database (PostgreSQL/DuckDB) | Complete | 95% |
| Authentication (Supabase JWT) | Complete | 90% |
| Leaderboard | Complete | 90% |
| Algorithm Submission | Complete | 90% |
| PDF Report Generation | Complete | 80% |
| CI/CD Pipeline | Complete | 85% |
| Centralized Database | Complete | 95% |

### 22.3 Known Gaps

**Missing Features (from Vision Alignment Audit):**

1. **Event-Based Dataset Filtering** - ML event model not operational; fallback to TLE discontinuity detection
2. **Close Object Implementation** - Distance/velocity thresholds defined but full implementation incomplete
3. **Target Percentage Enforcement** - 50%/10%/1% targets may not be enforced across all generation paths
4. **Non-Optical Sensor Support** - Radar and RF observation pipelines not fully tested
5. **3D Globe Visualization** - Cesium integration started but not complete
6. **End-to-End Without Orekit** - No fallback for environments without Java/Orekit

**Technical Debt (from Production Audit):**

1. Single-worker limitation (JobManager uses in-memory state)
2. Dual migration systems (Alembic + schema.py)
3. Token refresh potential memory leak
4. Some IDOR vulnerabilities on endpoints
5. Missing integration tests for full pipeline
6. Real-world UCTP validation pending (need Aerospace Corp output from Patrick Ramsey)

### 22.4 Validation Status

> "The pipeline still needs validation with actual UCT processor output. Current testing uses random/simulated data to validate algorithms work, but real-world validation with Aerospace Corp's UCTP (via Patrick Ramsey) is pending." - Lewis

---

## 23. Reference Code Lineage

### 23.1 Branch History

From reference-code/README.md:

| Branch | Author | Key Features | Status |
|--------|--------|--------------|--------|
| `master` | Original team | Initial implementation, basic API integrations | Legacy - superseded |
| `jovan-linuxTesting` | Jovan | DuckDB integration, Polars data processing, Linux setup automation | Features to merge |
| `uct-benchmark-refactor-joncline` | Dr. Jon Cline | **Reference architecture**, clean module structure, Solara UI | Architecture template |

### 23.2 Active Codebase

The active development codebase at `UCT-Benchmark-DMR/combined/` is based on Dr. Cline's refactored architecture with:
- Clean module separation (api/, data/, database/, evaluation/, simulation/, uctp/, utils/)
- Repository pattern for database access
- Adapter pattern for dual database support
- Full web platform (FastAPI + React) built on top

### 23.3 Key Architectural Decisions from Reference Code

**From joncline's refactor:**
- Separated monolithic `src/libraries/` into domain-specific packages
- Added proper `__init__.py` exports
- Created `uct_benchmark/` package with clean namespace
- Added environment-based configuration via `.env` files

**From Jovan's branch:**
- Proved DuckDB viability for local development
- Demonstrated Polars for high-performance data processing
- Created Linux setup automation scripts

---

## 24. Glossary of Terms

| Term | Definition |
|------|------------|
| **UCT** | Uncorrelated Track - a track of observations that cannot be matched to any known satellite |
| **UCTP** | Uncorrelated Track Processor - an algorithm that processes UCTs |
| **CTF** | Common Task Framework - methodology for standardized benchmarking |
| **SDA** | Space Domain Awareness - understanding the space operational environment |
| **TAP Lab** | Tools, Applications, & Processing Lab (USSF) |
| **SpOC** | Space Operations Command (USSF) |
| **UDL** | Unified Data Library - primary data source for observations and state vectors |
| **TLE** | Two-Line Element set - standard format for describing satellite orbits |
| **TrackTLE** | TLE generated by performing IOD on a single track of observations |
| **IOD** | Initial Orbit Determination - computing an orbit from observations |
| **Reference Object** | Satellite with known NORAD ID, state vector, TLE, and observations |
| **Reference Orbit** | Complete orbital data (SV, TLE, obs, trackTLEs) for a reference object |
| **Candidate Orbit** | Output from a UCTP: determined SV/TLE + correlated observation IDs |
| **Common Epoch** | The epoch at which the candidate orbit SV/TLE is valid |
| **Propagated Reference** | Reference orbit propagated to the common epoch for comparison |
| **Decorrelation** | Stripping NORAD IDs from observations to make them "uncorrelated" |
| **Downsampling** | Strategically removing observations to simulate specific scenarios |
| **Orbit Association** | Matching candidate orbits to reference orbits (Hungarian algorithm) |
| **LEO** | Low Earth Orbit (a <= 8378 km) |
| **MEO** | Medium Earth Orbit (8378 < a < 42164 km) |
| **GEO** | Geosynchronous Orbit (a >= 42164 km) |
| **HEO** | Highly Elliptical Orbit (e >= 0.7) |
| **HAMR** | High Area-to-Mass Ratio (> 1.0 m²/kg) |
| **Fitspan** | Duration of time a dataset spans (1-14 days) |
| **Mahalanobis Distance** | Statistical distance accounting for covariance |
| **NEES** | Normalized Estimation Error Squared |
| **F1 Score** | Harmonic mean of precision and recall |
| **MCC** | Matthews Correlation Coefficient |
| **Orekit** | Open-source Java library for orbital mechanics |
| **DormandPrince853** | Numerical integrator used for orbit propagation |
| **NRLMSISE-00** | Atmospheric density model |
| **Supabase** | Open-source Firebase alternative (auth + PostgreSQL) |
| **Railway** | Cloud deployment platform |
| **DuckDB** | Embedded analytical database (development backend) |

---

## 25. Document Sources and Traceability

This document synthesizes information from the following sources:

### 25.1 Provided Materials (Reference Only - Not Modified)

| Document | Type | Key Content |
|----------|------|-------------|
| `ProjectProposal.pdf` / `SDA-Project.pdf` | PDF | Official SDA TAP Lab project brief |
| `SpOC-Project.pdf` | PDF | Official SpOC project brief |
| `SpOC-SDA-Description.pdf` | PDF | Combined project description with space domain statistics |
| `SDATap (BenchmarkDataset) X The Data Mine Lab.pdf` | PDF | Data Mine collaboration document |
| `Benchmarking Documentation.docx.md` | Markdown | **Authoritative system documentation** by 2025 AFRL Scholars |
| `Lewis_Transcript-1-22.md` | Transcript | Louis's initial presentation on UCT benchmarking vision |
| `2-19Transcript.md` | Transcript | Feb 19, 2026 full team meeting with design decisions |
| `transcript.md` | Transcript | Louis's data storage and UI requirements |
| `UCT Benchmarking/_readMe.txt` | Text | Directory structure guide |
| `UCT Benchmarking/Documentation/_readMe.txt` | Text | Documentation priority guide |
| `Need for UCT Benchmarking.pdf` | PDF | Motivation document |
| `UCT Papers/` | Papers | Academic papers on UCT processing |
| `Learning Docs/` | Mixed | CTF methodology, acronym guide, space background |
| `Measurement Simulation/` | Mixed | Sensor noise and measurement uncertainty references |

### 25.2 Reference Code

| Directory | Author | Purpose |
|-----------|--------|---------|
| `reference-code/master/` | Original team | Legacy implementation baseline |
| `reference-code/jovan-linuxTesting/` | Jovan | DuckDB/Polars features |
| `reference-code/uct-benchmark-refactor-joncline/` | Dr. Jon Cline | Reference architecture (adopted) |

### 25.3 Active Codebase

| Directory | Type | Content |
|-----------|------|---------|
| `UCT-Benchmark-DMR/combined/uct_benchmark/` | Python | Core pipeline (55+ modules, ~33,500 LOC) |
| `UCT-Benchmark-DMR/combined/backend_api/` | Python | FastAPI REST API |
| `UCT-Benchmark-DMR/combined/frontend/src/` | TypeScript/React | Web UI (15 pages, 45+ components) |
| `UCT-Benchmark-DMR/combined/docs/` | Markdown | Technical documentation |

### 25.4 Generated Documentation

| Directory | Content |
|-----------|---------|
| `generated-docs/docs/technical/` | Architecture, Pipeline, API, Database, Frontend, Auth |
| `generated-docs/docs/planning/` | Project Status, Roadmap, Team Plans, Dependencies |
| `generated-docs/docs/guides/` | Beginner, Dataset Generation, Evaluation, Orekit, Deployment, UI |
| `generated-docs/docs/reports/` | Team Split Readiness, Consistency Audit, Issues Backlog |
| `generated-docs/docs/reference/` | Glossary, FAQ, Provided Materials Index |

### 25.5 Audit Reports

| Document | Date | Key Finding |
|----------|------|-------------|
| `COMPREHENSIVE_AUDIT_REPORT.md` | 2026-04-01 | 195+ issues across 8 domains |
| `VISION_ALIGNMENT_AUDIT.md` | 2026-04-02 | ~78% aligned with Louis's specifications |
| `PRODUCTION_READINESS_AUDIT_2026-04-01.md` | 2026-04-01 | ~60% production ready |
| `COMPREHENSIVE_PRODUCTION_AUDIT_2026-04-02.md` | 2026-04-02 | ~45% production ready (detailed) |
| `PRODUCTION_BEST_PRACTICES_AUDIT_CHECKLIST.md` | 2026-04-02 | 159-item best practices checklist |
| `QA_DEEP_TEST_REPORT.md` | Undated | 33 endpoints tested, 79% pass rate |
| `TRANSCRIPT_ALIGNMENT_PLAN.md` | 2026-01-31 | 100% alignment achieved (both gaps fixed) |
| `DOCUMENTATION_UPDATE_PLAN.md` | Undated | 14 documentation gaps identified |

---

## Appendix A: Complete Dataset Generation Workflow (from Benchmarking Documentation)

```
1. User specifies dataset code (16-char) or UI configuration
2. Time Window Selection:
   a. Query UDL for satellite counts in candidate windows
   b. Score windows against quality criteria (coverage, gap, obs count)
   c. Use bisection to find optimal window
   d. If no valid window exists -> TIER_5 (impossible)
3. Data Acquisition:
   a. Pull observations from UDL (EO, radar, RF services)
   b. Pull state vectors from UDL
   c. Pull TLEs from UDL
   d. Query ESA Discosweb for physical properties (mass, area)
4. Basic Scoring:
   a. Calculate orbital coverage per satellite
   b. Calculate track gaps per satellite
   c. Count observations per satellite per 3-day span
   d. Classify tier: T1 (all criteria met) / T2 (needs downsampling) /
      T3 (needs simulation) / T4 (fully synthetic)
5. Object Type Filtering (if specified):
   a. HAMR: Filter by area-to-mass ratio > 1.0 m²/kg
   b. Close: Filter by distance < 100km AND velocity < 100 m/s
   c. Calibration: Use well-tracked satellite list
   d. Enforce target percentage (50%/10%/1%)
6. Downsampling (if T2):
   a. Stage 1: Reduce orbital coverage to target
   b. Stage 2: Widen track gaps to target
   c. Stage 3: Reduce observation count to target
7. Simulation (if T3):
   a. Identify gap epochs with epochsToSim()
   b. Generate synthetic observations with Orekit propagation
   c. Apply sensor noise models
8. Track Binning:
   a. Group observations into tracks (90-min cutoff)
   b. Validate minimum 3 obs per track
9. TrackTLE Generation:
   a. Modified Gauss IOD on each track
   b. BatchLSEstimator refinement
   c. Convert to TLE format
10. True Negative Addition:
    a. Add 2 non-reference observations per satellite
    b. Insufficient for IOD (prevents correct association)
11. Decorrelation:
    a. Strip NORAD IDs from all observations
    b. Strip satellite associations
    c. Set uct=true on all observations
12. Output:
    a. Save decorrelated dataset (JSON)
    b. Save reference truth (grouped by satellite)
    c. Record dataset code and configuration
    d. Store in database with unique ID
```

## Appendix B: Complete Evaluation Workflow (from Benchmarking Documentation)

```
1. Load benchmark dataset (output_dataset.json)
2. Load UCTP output (uctp_output.json)
3. Frame Conversion:
   a. Convert all state vectors to J2000/EME2000
   b. Convert covariance matrices to J2000 frame
   c. Supported input frames: J2000, TEME, GCRF, ITRF, ECEF, TDR
4. Orbit Association (orbitAssociation):
   a. Build cost matrix: propagate each reference to each candidate's epoch
   b. Compute 6D L2 norm for each pair
   c. Solve assignment with modified Jonker-Volgenant (scipy)
   d. Output: associated pairs, non-associated candidates, non-associated references
5. State Metrics (stateMetrics):
   a. For each associated pair, propagate reference to candidate epoch
   b. Compute position L2 norm error (km)
   c. Compute velocity L2 norm error (km/s)
   d. Compute 6D state L2 norm error
   e. Compute Mahalanobis distance + p-score
   f. Compute NEES + p-score
6. Binary Classification (binaryMetrics):
   a. For each observation in dataset:
      - If in candidate's grouped_ops AND matches reference satellite -> TP
      - If in candidate's grouped_ops but wrong reference satellite -> FP
      - If not in any candidate's grouped_ops but is a reference obs -> FN
      - If not in any candidate's grouped_ops and not a reference obs -> TN
   b. Compute: Accuracy, Balanced Accuracy, Precision, Recall, F1, Specificity,
      Cohen's Kappa, MCC
7. Residual Metrics (residualMetrics):
   a. Accuracy mode: Propagate candidate to reference observation epochs,
      compute great circle residuals
   b. Precision mode: Propagate candidate to its own sourced observation epochs,
      compute great circle residuals
   c. For each: RMSE, Mean, Standard Deviation
8. Report Generation:
   a. Combine all metrics into evaluation dictionary
   b. Generate PDF report with tables and residual graphs
   c. Save JSON results file
   d. Display dataset code at top of report
```

## Appendix C: Frontend User Flow

```
UNAUTHENTICATED:
  /welcome (Landing Page)
    -> Features, capabilities, tier descriptions
    -> CTA buttons -> /login

  /login (Authentication)
    -> Email/password login
    -> Sign up
    -> Password reset
    -> OAuth support

AUTHENTICATED:
  / (Dashboard)
    -> Stat cards: Top Rank, Submissions, Best F1, vs Average
    -> Quick actions: Generate Dataset, Submit Algorithm
    -> Recent Submissions list
    -> Leaderboard Snapshot
    -> Announcements

  /datasets (Dataset Browser)
    -> Filter by regime, tier, sensor type
    -> Grid/list view toggle
    -> Preview dialog with download
    -> Navigate to detail page

  /datasets/generate (Dataset Generator - Multi-step Wizard)
    -> Step 1: Orbital regime selection
    -> Step 2: Data tier and quality config
    -> Step 3: Observation density/downsampling params
    -> Step 4: Simulation options
    -> Review: Full config summary
    -> Submit: Real-time progress monitoring
    -> OR: Legacy 16-char code entry

  /datasets/my-datasets (My Datasets)
    -> Table of user's datasets
    -> Download, delete, copy ID
    -> Version history
    -> Status tracking

  /submit (Submit Algorithm Output)
    -> Select dataset
    -> Upload JSON file (drag-and-drop)
    -> Algorithm metadata (name, version, description, org)
    -> Multi-step validation pipeline
    -> Submit for evaluation

  /submit/my-submissions (My Submissions)
    -> Summary cards: Total, Completed, Queued, Failed
    -> Table with status, F1-Score, rank
    -> Export results
    -> Navigate to results

  /results/:id (Detailed Results)
    -> Binary metrics display
    -> State metrics (position/velocity RMS)
    -> Residual analysis (RA/Dec arcsec)
    -> Per-satellite breakdown
    -> Histograms
    -> Export to JSON/CSV/PDF

  /leaderboard (Leaderboard)
    -> Top 3 podium
    -> Sortable table (F1, Precision, Recall, Position RMS)
    -> Filters: Regime, Tier, Time period, Dataset
    -> Trend chart

  /profile (Profile)
    -> Edit display name, organization
    -> API key management
    -> Notification preferences
    -> Security settings

  /settings (Settings)
    -> Service credentials (UDL, ESA tokens)
    -> Application configuration

  /docs (Documentation)
    -> Getting Started (5 steps)
    -> Dataset Format
    -> Submission Format
    -> Evaluation Metrics
    -> Pipeline Overview
```

---

*This document was compiled on 2026-04-02 by analyzing every file in the provided-materials/, reference-code/, UCT-Benchmark-DMR/combined/, and generated-docs/ directories, plus all top-level project documents. Direct quotes are attributed to their source documents. All specifications, thresholds, and design decisions are traceable to their original source materials.*
