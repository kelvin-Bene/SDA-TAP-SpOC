# Code Architecture and Logic

## Module Structure

The main codebase is located in `uct-benchmark-refactor-joncline/uct_benchmark/`:

```
uct_benchmark/
├── __init__.py              # Package initialization
├── config.py                # Configuration and constants
├── dataset.py               # Dataset utilities
├── Create_Dataset.py        # Dataset creation driver
├── Evaluation.py            # Evaluation driver
├── MainMVP.py               # Main pipeline driver
├── batchPull.py             # Batch data retrieval
│
├── api/                     # External API integrations
│   ├── __init__.py
│   └── apiIntegration.py    # UDL, Space-Track, CelesTrak, ESA APIs
│
├── data/                    # Data manipulation and processing
│   ├── __init__.py
│   ├── basicScoringFunction.py  # Data quality scoring
│   ├── dataManipulation.py      # Data transformation utilities
│   ├── readData.py              # Data loading utilities
│   ├── windowCheck.py           # Window selection algorithm
│   └── windowTools.py           # GUI and window utilities
│
├── evaluation/              # Evaluation metrics and analysis
│   ├── __init__.py
│   ├── binaryMetrics.py         # Classification metrics
│   ├── evaluationReport.py      # Report data structures
│   ├── orbitAssociation.py      # Orbit matching algorithm
│   ├── residualMetrics.py       # Residual analysis
│   └── stateMetrics.py          # State comparison metrics
│
├── simulation/              # Orbit propagation and simulation
│   ├── __init__.py
│   ├── gauss.py                 # Gauss method for IOD
│   ├── orbitCoverage.py         # Orbital coverage calculation
│   ├── propagator.py            # Orbit propagators
│   ├── simulateObservations.py  # Observation simulation
│   └── TLEGeneration.py         # TLE generation utilities
│
├── uctp/                    # UCTP algorithm implementations
│   ├── __init__.py
│   └── dummyUCTP.py             # Test UCTP implementation
│
└── utils/                   # Utility functions
    ├── __init__.py
    ├── generateCov.py           # Covariance generation
    ├── generatePDF.py           # PDF report generation
    ├── scrape_satellite_data.py # Satellite data scraping
    ├── timeSort.py              # Time sorting utilities
    ├── timerClass.py            # Performance timing
    └── unitConversion.py        # Unit conversion utilities
```

---

## Core Modules

### 1. API Integration (`api/apiIntegration.py`)

Central module for all external data source integrations.

#### UDL (Unified Data Library) Functions

```python
def UDLTokenGen(username, password) -> str:
    """Generate Base64 authentication token for UDL."""

def UDLQuery(token, service, params, count=False, history=False) -> DataFrame:
    """
    Perform synchronous UDL query.

    Services: eoobservation, statevector, elset, elset/current
    """

async def _asyncUDLQuery(token, service, params, count=False, history=False):
    """Async version for batch queries."""

def asyncUDLBatchQuery(token, service, params_list, dt=0.1) -> DataFrame:
    """Execute multiple UDL queries with rate limiting."""
```

#### Other Data Sources

```python
def spacetrackQuery(token, params, request="satcat") -> DataFrame:
    """Query Space-Track.org for TLE and catalog data."""

def discoswebQuery(token, params, data="objects") -> DataFrame:
    """Query ESA DiscoWeb for satellite physical properties."""

def celestrakQuery(params, table="gp") -> DataFrame:
    """Query CelesTrak for TLE and catalog data."""

def celestrakSatcat() -> DataFrame:
    """Retrieve complete CelesTrak satellite catalog."""
```

#### TLE Utilities

```python
def parseTLE(line1, line2) -> dict:
    """Parse TLE into orbital elements dictionary."""

def TLEToSV(line1, line2) -> np.array:
    """Convert TLE to state vector using Orekit."""
```

#### Dataset Management

```python
def generateDataset(UDL_token, ESA_token, satIDs, timeframe, timeunit, ...) -> tuple:
    """Generate complete benchmark dataset from APIs."""

def pullStates(UDL_token, satIDs, timeframe, timeunit, ...) -> tuple:
    """Pull state vectors and TLEs for specified satellites."""

def saveDataset(ref_obs, ref_track, ref_sv, ref_elset, output_path) -> dict:
    """Save dataset to JSON format."""

def loadDataset(input_path) -> tuple:
    """Load dataset from JSON format."""
```

---

### 2. Window Selection (`data/windowCheck.py`)

Implements intelligent window selection for finding high-quality data windows.

#### Main Functions

```python
def windowMain(codes, UDL_token) -> list:
    """
    Main driver for window selection.

    Returns: List of tuples (code, threshold, bin_best, orbElems, metadata)
    """

def windowCheck(window_size, batch_size, code, start_epoch, end_epoch, UDL_token) -> tuple:
    """
    Sub-driver for finding best window for a single dataset code.

    Iterates through threshold levels with exponential batch decay.
    """

def bisect(batch, window_size, thresh_des, code) -> tuple:
    """
    Recursively bisect data to find minimum-size valid sub-batch.

    Uses overlapping bisection to avoid missing valid regions.
    """

def slide(sub_batch, window_size, code) -> tuple:
    """
    Slide window through sub-batch to find optimal position.

    Returns highest-scoring window of specified size.
    """
```

#### Helper Functions

```python
def batchPull(code, start_epoch, end_epoch, UDL_token) -> DataFrame:
    """Pull batch of observation data from UDL."""

def normalizeTime(data) -> Series:
    """Normalize epochs relative to most recent time."""

def expFunc(window_size, batch_size, iteration, decay_rate) -> float:
    """Exponential decay function for batch sizing."""

def thresholdConvert(thresholds_strs) -> list:
    """Convert tier strings (T1-T5) to numeric values."""

def thresholdCheck(batch_temp, thresh_des, code) -> bool:
    """Check if batch meets desired threshold."""
```

---

### 3. Scoring Function (`data/basicScoringFunction.py`)

Evaluates data quality for window selection.

```python
def basicScoring(code, data, satData) -> tuple:
    """
    Score data quality based on multiple criteria.

    Returns: (score, orbitalElements, metadata)

    Scoring Factors:
    - Orbital coverage (percentage of orbit observed)
    - Observation count (obs per time period)
    - Track gap (longest gap between observations)
    - Object count (satellites meeting criteria)
    """
```

---

### 4. Propagators (`simulation/propagator.py`)

High-fidelity orbit propagation using Orekit.

#### Monte Carlo Propagator

```python
def monteCarloPropagator(stateVector, covariance, initialEpoch, finalEpoch,
                         N=0, satelliteParameters=[...]) -> tuple:
    """
    Propagate state with covariance using Monte Carlo simulation.

    Force Model:
    - Earth gravity (120x120 harmonics)
    - Third body (Sun, Moon)
    - Atmospheric drag (NRLMSISE00)
    - Solar radiation pressure

    Returns: (finalState, finalCovariance) if N>1, else finalState
    """
```

#### Ephemeris Propagator

```python
def ephemerisPropagator(stateVector, initialEpoch, finalEpoch,
                        satelliteParameters=[...]) -> list:
    """
    Propagate state to multiple epochs efficiently.

    Uses Orekit ephemeris generator for single propagation pass.
    Handles both forward and backward propagation.

    Returns: List of state vectors at each epoch
    """
```

#### TLE Propagator

```python
def TLEpropagator(input1, input2, finalEpoch) -> tuple:
    """
    Propagate TLE using SGP4/SDP4.

    Accepts either:
    - TLE lines (str, str)
    - State vector + epoch (array, datetime)

    Returns: (TLE_lines1, TLE_lines2, state_vectors)
    """
```

#### Utilities

```python
def orbit2OE(input1, input2) -> dict:
    """
    Convert state or TLE to Keplerian orbital elements.

    Returns: {
        'Semi-Major Axis': km,
        'Eccentricity': unitless,
        'Inclination': degrees,
        'RAAN': degrees,
        'Argument of Perigee': degrees,
        'Mean Anomaly': degrees,
        'Period': seconds
    }
    """

def datetime2AbsDate(datetime_obj, utc) -> AbsoluteDate:
    """Convert Python datetime to Orekit AbsoluteDate."""
```

---

### 5. Orbit Association (`evaluation/orbitAssociation.py`)

Associates UCTP output with reference orbits.

```python
def orbitAssociation(truth, est, propagator, elset_mode=False) -> tuple:
    """
    Globally optimal orbit association using Hungarian algorithm.

    Process:
    1. Build cost matrix (n_est x n_truth)
    2. Propagate truth states to estimated epochs
    3. Compute position error for each pair
    4. Solve linear sum assignment
    5. Return associated and non-associated orbits

    Returns: (associated_orbits, results_dict, nonassociated_orbits)
    """
```

---

### 6. Evaluation Metrics

#### Binary Metrics (`evaluation/binaryMetrics.py`)

```python
def binaryMetrics(ref_obs, associated_orbits) -> dict:
    """
    Compute classification metrics.

    Returns: {
        'True Positives': int,
        'False Positives': int,
        'False Negatives': int,
        'Precision': float,
        'Recall': float,
        'F1-Score': float
    }
    """
```

#### State Metrics (`evaluation/stateMetrics.py`)

```python
def stateMetrics(ref_sv, associated_orbits, propagator) -> dict:
    """
    Compute orbital state comparison metrics.

    Returns: {
        'Position Error Mean': km,
        'Position Error Std': km,
        'Velocity Error Mean': km/s,
        'Velocity Error Std': km/s,
        'Mahalanobis Distance': unitless
    }
    """
```

#### Residual Metrics (`evaluation/residualMetrics.py`)

```python
def residualMetrics(ref_obs, orbits, propagator, is_reference) -> dict:
    """
    Compute observation residual statistics.

    Returns: {
        'RA Residual RMS': arcsec,
        'Dec Residual RMS': arcsec,
        'Range Residual RMS': km (if available)
    }
    """
```

---

### 7. Configuration (`config.py`)

Centralized configuration parameters.

```python
# Path Configuration
PROJ_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

# Orbital Regime Thresholds
semiMajorAxis_LEO = 8378    # km (altitude < 2000km)
semiMajorAxis_GEO = 42164   # km
eccentricity_HEO = 0.7

# Quality Thresholds
highPercentage = (0.9, 0.95, 1.0)
standardPercentage = (0.4, 0.5, 0.6)
lowPercentage = (0.0, 0.05, 0.1)

# Observation Thresholds
lowObsCount = 50
highObsCount = 150
longTrackGap = 2  # orbital periods

# Object Count Targets
highObjectCount = 80
standardObjectCount = 40
lowObjectCount = 10

# Window Selection Parameters
batchSizeMultiplier = 5
batchSizeDecayRate = 0.01
slide_resolution = 0.1
thresholds = ["T1", "T2", "T2", "T3", "T3", "T3", "T4", "T4", "T4", "T4"]

# Propagator Parameters
solarRadPresCoef = 1.5
dragCoef = 2.5
monteCarloPoints = 100

# Simulation Parameters
positionNoise = 0.01  # km
angularNoise = 1 * 3600  # arcseconds to radians
```

### Noise Modeling: Current vs Desired

Per tech lead Lewis, the current simulation uses a simplified noise model:

**Current Implementation:**
- Constant Gaussian blur added to simulated observations
- Basic noise term added to position

**Desired Improvements (Future Work):**
- **Atmospheric refraction** - Light bending through Earth's atmosphere
- **Stellar aberration** - Apparent shift due to observer motion
- More realistic sensor-specific noise characteristics

> "We want to be able to more accurately represent sources of uncertainty and noise in the telescope systems. Right now we just added a constant Gaussian blur... there's also other sources of uncertainty, such as atmospheric refraction or stellar aberration that were not accounted for in the simulation." - Lewis

Research and papers on more accurate optical noise characteristics are available in the project documentation.

---

## Data Structures

### Dataset JSON Format

```json
{
  "dataset_obs": [
    {
      "id": "observation_uuid",
      "obTime": "2025-01-01T00:00:00.000000Z",
      "ra": 123.456,
      "declination": 45.678,
      "trackId": 0,
      "origObjectId": 0,
      "uct": true
      // ... other observation fields
    }
  ],
  "dataset_elset": [
    // Similar structure for TLE-based data
  ],
  "reference": [
    {
      "satNo": 12345,
      "xpos": -7365.971,
      "ypos": -1331.400,
      "zpos": 1514.249,
      "xvel": 1.977,
      "yvel": -5.225,
      "zvel": 4.473,
      "epoch": "2025-01-01T00:00:00.000000",
      "cov": "[...]",
      "mass": 1000.0,
      "crossSection": 10.0,
      "dragCoeff": 2.5,
      "solarRadPressCoeff": 1.5,
      "line1": "1 12345U ...",
      "line2": "2 12345 ...",
      "groupedObsIds": ["id1", "id2", ...],
      "groupedElsetIds": ["id3", "id4", ...]
    }
  ]
}
```

### UCTP Output Format

```json
[
  {
    "idStateVector": 0,
    "sourcedData": ["obs_id1", "obs_id2"],
    "epoch": "2025-01-01T00:00:00.000000",
    "uct": true,
    "xpos": -7365.971,
    "ypos": -1331.400,
    "zpos": 1514.249,
    "xvel": 1.977,
    "yvel": -5.225,
    "zvel": 4.473,
    "referenceFrame": "J2000",
    "cov": [/* 21 elements */],
    "rms": 1.234
  }
]
```

---

## Dependencies

### Core Dependencies
- `numpy` - Numerical operations
- `pandas` - Data manipulation
- `scipy` - Optimization (Hungarian algorithm)
- `aiohttp` - Async HTTP requests
- `requests` - Sync HTTP requests

### Orekit (Orbit Mechanics)
- `orekit_jpype` - Python wrapper for Orekit
- Requires Java runtime (JDK 11+)
- Orekit data files for atmospheric/gravitational models

### GUI
- `customtkinter` - Modern tkinter GUI

### Utilities
- `loguru` - Logging
- `python-dotenv` - Environment variables
- `duckdb` - Session data storage
- `reportlab` - PDF generation
