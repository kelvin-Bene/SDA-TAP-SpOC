# Dataset Generation Guide

This guide explains how to generate benchmark datasets for UCTP algorithm evaluation.

## Overview

The UCT Benchmark system generates datasets at different tiers (T1-T4), each with varying levels of data processing:

| Tier | Description | Processing |
|------|-------------|------------|
| T1 | Light Downsampling | Real data with optional thinning |
| T2 | Heavy Downsampling | Real data with significant gaps |
| T3 | Observation Simulation | Gaps filled with simulated observations |
| T4 | Object Simulation | Synthetic satellites added |

## Prerequisites

Before generating datasets:

1. **API Token**: Ensure `UDL_TOKEN` is set in your environment
2. **Java 17+**: Required for Orekit simulation
3. **Dependencies**: Run `pip install -e .` in the project directory

## Method 1: Web Interface (Recommended)

### Step 1: Start the Application

```bash
# Start backend
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000

# Start frontend (in another terminal)
cd UCT-Benchmark-DMR/combined/frontend
npm run dev
```

### Step 2: Navigate to Dataset Generator

1. Open http://localhost:5173
2. Click **Datasets** in the navigation
3. Click **Generate New Dataset**

### Step 3: Configure Dataset Parameters

| Parameter | Description | Options |
|-----------|-------------|---------|
| Orbital Regime | Target orbit type | LEO, MEO, GEO, HEO |
| Tier | Processing level | T1, T2, T3, T4 |
| Object Count | Number of satellites | 10-100 |
| Coverage | Observation coverage | High, Standard, Low |
| Time Window | Date range | Up to 90 days |

### Step 4: Generate and Download

1. Click **Generate Dataset**
2. Wait for processing (may take several minutes)
3. Click **Download** when complete

## Method 2: Python API

### Basic Usage

```python
from uct_benchmark.Create_Dataset import create_datasets_from_codes

# Define dataset code
# Format: {REGIME}_{OBJ}_{COVERAGE}_{GAPS}_{OBS}
codes = ["LEO_H_H_H_H"]  # LEO, High objects, High coverage, High gaps, High obs

# Set API token
import os
os.environ["UDL_TOKEN"] = "your_base64_token_here"

# Generate dataset
results = create_datasets_from_codes(codes)

# Results contain dataset paths
for code, dataset_path in results:
    print(f"Generated: {code} -> {dataset_path}")
```

### Dataset Code Format

The code format encodes dataset parameters:

```
{REGIME}_{OBJECT_COUNT}_{COVERAGE}_{GAPS}_{OBS_DENSITY}
```

| Component | Options | Description |
|-----------|---------|-------------|
| REGIME | LEO, MEO, GEO, HEO | Orbital regime |
| OBJECT_COUNT | H, S, L | High (80), Standard (40), Low (10) |
| COVERAGE | H, S, L | Orbital coverage percentage |
| GAPS | H, S, L | Track gap characteristics |
| OBS_DENSITY | H, S, L | Observation density |

### Advanced Usage

```python
from uct_benchmark.api.apiIntegration import generateDataset

# Direct API call with full control
dataset, obs_truth, state_truth, elset_truth = generateDataset(
    UDL_token="your_token",
    ESA_token="your_esa_token",  # Optional
    satIDs=[25544, 25545, 25546],  # Specific satellites
    timeframe=7,  # Days
    timeunit="d",
    tier="T2",
    verbose=True
)
```

## Method 3: GUI Application

### Launch Desktop GUI

```bash
cd UCT-Benchmark-DMR/combined
python -m uct_benchmark.Create_Dataset
```

### Configure Parameters

The GUI provides sliders and dropdowns for:
- Orbital regime selection
- Time window configuration
- Quality thresholds
- Object count targets

### Save Configuration

Configurations can be saved and reloaded using the Session Manager.

## Dataset Output Format

Generated datasets are saved as JSON:

```json
{
  "metadata": {
    "name": "LEO_H_H_H_H_20260122",
    "code": "LEO_H_H_H_H",
    "tier": "T2",
    "generated_at": "2026-01-22T10:30:00Z",
    "observation_count": 5000,
    "object_count": 80
  },
  "dataset_obs": [
    {
      "id": "obs-uuid-001",
      "obTime": "2026-01-15T12:00:00.000000Z",
      "ra": 123.456,
      "declination": 45.678,
      "trackId": 1,
      "uct": true
    }
  ],
  "reference": [
    {
      "satNo": 25544,
      "epoch": "2026-01-15T12:00:00.000000",
      "xpos": -7365.971,
      "ypos": -1331.400,
      "zpos": 1514.249,
      "line1": "1 25544U ...",
      "line2": "2 25544 ..."
    }
  ]
}
```

## Tier-Specific Processing

### T1 - Light Downsampling

```python
from uct_benchmark.data.dataManipulation import downsample_observations

# Apply light downsampling (retain 80% of observations)
downsampled_df = downsample_observations(
    observations_df,
    retention_rate=0.8,
    preserve_tracks=True
)
```

### T2 - Heavy Downsampling

```python
# Apply heavy downsampling (retain 30-50% of observations)
downsampled_df = downsample_observations(
    observations_df,
    retention_rate=0.4,
    target_gap=2.0,  # Target 2 orbital periods between obs
    preserve_tracks=True
)
```

### T3 - Observation Simulation

```python
from uct_benchmark.simulation.simulateObservations import simulateObs, epochsToSim

# Find gaps to fill
epochs_to_simulate = epochsToSim(
    observations_df,
    orbital_period_seconds=5400,
    bins_per_period=10
)

# Generate synthetic observations
simulated_obs = simulateObs(
    tle_line1, tle_line2,
    epochs_to_simulate,
    sensor_name="GEODSS"
)
```

## Validation

After generation, validate your dataset:

```bash
# Run validation suite
cd UCT-Benchmark-DMR/combined
python validation/run_validation.py --dataset-path data/my_dataset.json
```

## Common Issues

### "UDL token not set"

```bash
# Set environment variable
export UDL_TOKEN="your_base64_token"

# Or in Python
import os
os.environ["UDL_TOKEN"] = "your_token"
```

### "Orekit initialization failed"

See [Orekit Setup Guide](OREKIT_SETUP.md) for Java configuration.

### "Not enough observations"

- Increase time window
- Select different orbital regime
- Lower quality thresholds

---

## Related Documentation

- [Orekit Setup](OREKIT_SETUP.md)
- [Pipeline Documentation](../technical/PIPELINE.md)
- [Data Sources](../technical/DATA_SOURCES.md)
- [Configuration](../technical/CONFIGURATION.md)
