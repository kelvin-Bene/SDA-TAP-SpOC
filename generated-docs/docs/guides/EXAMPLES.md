# Code Examples Gallery

Practical code examples for common UCT Benchmark tasks.

---

## Dataset Generation

### Generate a Basic Dataset

```python
from uct_benchmark.database import DatabaseManager
from uct_benchmark.api.apiIntegration import generateDataset, saveDataset
import os

# Initialize database
db = DatabaseManager()
db.initialize()

# Set your UDL token
UDL_TOKEN = os.getenv("UDL_TOKEN")

# Define parameters
sat_ids = [25544, 43013, 41866]  # ISS, Starlink, GPS satellite
timeframe = 7  # days
tier = "T1"

# Generate dataset
dataset, obs_truth, state_truth, elset_truth = generateDataset(
    UDL_token=UDL_TOKEN,
    ESA_token=None,  # Optional
    satIDs=sat_ids,
    timeframe=timeframe,
    timeunit="days"
)

# Save to file
output_path = "data/processed/my_dataset.json"
saveDataset(obs_truth, dataset, state_truth, elset_truth, output_path)
print(f"Dataset saved to {output_path}")
```

### Generate Dataset with Downsampling (T2)

```python
from uct_benchmark.data.dataManipulation import downsample_observations
from uct_benchmark import settings

# Load existing T1 dataset
obs_data = load_observations("data/processed/t1_dataset.json")

# Apply T2 downsampling
downsampled = downsample_observations(
    obs_data,
    coverage_target=settings.downsample_coverage_target,
    gap_target=settings.downsample_gap_target,
    obs_max=settings.downsample_obs_max
)

print(f"Original: {len(obs_data)} observations")
print(f"Downsampled: {len(downsampled)} observations")
```

---

## Orbit Propagation

### Propagate a State Vector

```python
import orekit_jpype as orekit
orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)

from uct_benchmark.simulation.propagator import monteCarloPropagator, ephemerisPropagator
from datetime import datetime, timedelta

# Initial state (position in km, velocity in km/s)
state_vector = [-7365.971, -1331.400, 1514.249, 1.977, -5.225, 4.473]
covariance = None  # Optional 6x6 covariance matrix

initial_epoch = datetime(2025, 1, 1, 0, 0, 0)
final_epoch = initial_epoch + timedelta(hours=2)

# High-fidelity propagation
final_state, final_cov = monteCarloPropagator(
    stateVector=state_vector,
    covariance=covariance,
    initialEpoch=initial_epoch,
    finalEpoch=final_epoch,
    N=100  # Monte Carlo samples
)

print(f"Final position: {final_state[:3]} km")
print(f"Final velocity: {final_state[3:]} km/s")
```

### Propagate TLE

```python
from uct_benchmark.simulation.propagator import TLEpropagator
from datetime import datetime

# TLE lines (example: ISS)
line1 = "1 25544U 98067A   21275.52063657  .00001878  00000-0  42796-4 0  9992"
line2 = "2 25544  51.6442 208.4112 0003570 325.6334 175.6578 15.48867999305169"

# Propagate to future epoch
target_epoch = datetime(2025, 1, 15, 12, 0, 0)

position, velocity = TLEpropagator(line1, line2, target_epoch)
print(f"Position at {target_epoch}: {position} km")
```

---

## Evaluation

### Evaluate Algorithm Output

```python
from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
from uct_benchmark.evaluation.stateMetrics import stateMetrics
import json

# Load truth and algorithm output
with open("data/processed/truth.json") as f:
    truth = json.load(f)

with open("data/processed/algorithm_output.json") as f:
    algorithm_results = json.load(f)

# Associate orbits
associations, non_associated_truth, non_associated_est = orbitAssociation(
    truth=truth["reference"],
    est=algorithm_results,
    propagator="ephemeris",
    elset_mode=False
)

# Calculate metrics
binary = binaryMetrics(
    ref_obs=truth["observations"],
    associated_orbits=associations
)

state = stateMetrics(
    ref_sv=truth["reference"],
    associated_orbits=associations,
    propagator="ephemeris"
)

# Print results
print("=== Evaluation Results ===")
print(f"Precision: {binary['Precision']:.3f}")
print(f"Recall: {binary['Recall']:.3f}")
print(f"F1 Score: {binary['F1-Score']:.3f}")
print(f"Position Error (mean): {state['Position Error Mean']:.2f} km")
```

### Custom Evaluation Pipeline

```python
from uct_benchmark.evaluation.evaluationReport import EvaluationReport
import pandas as pd

def evaluate_algorithm(truth_file: str, output_file: str) -> dict:
    """Run complete evaluation pipeline."""

    # Load data
    truth_data = pd.read_json(truth_file)
    algorithm_output = pd.read_json(output_file)

    # Create evaluation report
    report = EvaluationReport()

    # Run evaluation
    results = report.evaluate(
        truth=truth_data,
        predictions=algorithm_output,
        metrics=["binary", "state", "residual"]
    )

    return results

# Usage
results = evaluate_algorithm(
    truth_file="truth.json",
    output_file="my_algorithm_output.json"
)
```

---

## Database Operations

### Query Datasets

```python
from uct_benchmark.database import DatabaseManager

db = DatabaseManager()

# List all datasets
datasets = db.datasets.list_datasets()
print(f"Found {len(datasets)} datasets")

# Filter by tier and regime
leo_t1 = db.datasets.list_datasets(tier="T1", regime="LEO")
print(f"LEO T1 datasets: {len(leo_t1)}")

# Get specific dataset
dataset = db.datasets.get_dataset(name="my_leo_dataset")
print(f"Dataset has {dataset['observation_count']} observations")
```

### Export Data

```python
from uct_benchmark.database import DatabaseManager

db = DatabaseManager()

# Export dataset to JSON
db.datasets.export_dataset(
    dataset_id=1,
    output_path="exports/dataset_1.json",
    format="json"
)

# Export observations to Parquet
db.observations.export(
    output_path="exports/all_observations.parquet",
    format="parquet"
)
```

### Bulk Insert

```python
from uct_benchmark.database import DatabaseManager
import pandas as pd

db = DatabaseManager()

# Prepare observation data
observations = pd.DataFrame({
    "id": ["obs_001", "obs_002", "obs_003"],
    "sat_no": [25544, 25544, 25544],
    "ob_time": pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:01:00", "2025-01-01 00:02:00"]),
    "ra": [120.5, 121.3, 122.1],
    "declination": [45.2, 45.5, 45.8],
    "sensor_name": "SENSOR_A",
    "is_uct": True
})

# Bulk insert
count = db.observations.bulk_insert(observations)
print(f"Inserted {count} observations")
```

---

## API Integration

### Query UDL

```python
from uct_benchmark.api.apiIntegration import UDLQuery, UDLTokenGen
import os

# Generate token (first time)
# token = UDLTokenGen("username", "password")
# Or use environment variable
token = os.getenv("UDL_TOKEN")

# Query observations for a satellite
params = {
    "satNo": 25544,  # ISS
    "startTime": "2025-01-01T00:00:00Z",
    "endTime": "2025-01-07T00:00:00Z"
}

observations = UDLQuery(
    token=token,
    service="eoobservation",
    params=params
)

print(f"Found {len(observations)} observations")
```

### Query CelesTrak (No Auth Required)

```python
from uct_benchmark.api.apiIntegration import celestrakQuery

# Get active satellites
active = celestrakQuery(
    params={"GROUP": "active"},
    table="gp"
)
print(f"Active satellites: {len(active)}")

# Get specific satellite
iss = celestrakQuery(
    params={"CATNR": 25544},
    table="gp"
)
print(f"ISS TLE epoch: {iss['EPOCH'].iloc[0]}")
```

---

## Web API (FastAPI)

### Submit Algorithm Results via API

```python
import requests
import json

API_URL = "http://localhost:8000"

# Prepare submission
submission_data = {
    "algorithm_name": "MyUCTP",
    "version": "1.0.0",
    "dataset_id": 1,
    "results": [
        {
            "idStateVector": 0,
            "epoch": "2025-01-01T00:00:00.000000",
            "xpos": -7365.971,
            "ypos": -1331.400,
            "zpos": 1514.249,
            "xvel": 1.977,
            "yvel": -5.225,
            "zvel": 4.473
        }
    ]
}

# Submit
response = requests.post(
    f"{API_URL}/api/submissions",
    json=submission_data
)

if response.status_code == 201:
    result = response.json()
    print(f"Submission ID: {result['id']}")
    print(f"Status: {result['status']}")
else:
    print(f"Error: {response.text}")
```

### Check Leaderboard

```python
import requests

API_URL = "http://localhost:8000"

# Get leaderboard for specific dataset
response = requests.get(
    f"{API_URL}/api/leaderboard",
    params={"dataset_id": 1, "metric": "f1_score"}
)

leaderboard = response.json()
for i, entry in enumerate(leaderboard[:10], 1):
    print(f"{i}. {entry['algorithm_name']}: {entry['f1_score']:.3f}")
```

---

## Visualization

### Plot Orbit Ground Track

```python
import matplotlib.pyplot as plt
import numpy as np
from uct_benchmark.simulation.propagator import ephemerisPropagator
from datetime import datetime, timedelta

# Propagate for one orbit
state = [-7000, 0, 0, 0, 7.5, 0]  # Example circular orbit
epochs = [datetime(2025, 1, 1) + timedelta(minutes=i) for i in range(100)]

positions = ephemerisPropagator(
    stateVector=state,
    initialEpoch=epochs[0],
    finalEpoch=epochs[-1],
    output_epochs=epochs
)

# Convert to lat/lon (simplified)
lats = [np.degrees(np.arcsin(p[2] / np.linalg.norm(p[:3]))) for p in positions]
lons = [np.degrees(np.arctan2(p[1], p[0])) for p in positions]

# Plot
plt.figure(figsize=(12, 6))
plt.scatter(lons, lats, c=range(len(lons)), cmap='viridis', s=5)
plt.xlabel('Longitude (deg)')
plt.ylabel('Latitude (deg)')
plt.title('Orbit Ground Track')
plt.colorbar(label='Time step')
plt.savefig('ground_track.png')
```

---

## More Resources

- [Getting Started](../getting-started.md) - Full setup instructions
- [API Reference](../technical/BACKEND_API.md) - REST API documentation
- [Evaluation Metrics](../technical/EVALUATION_METRICS.md) - Metric definitions
- [Pipeline Documentation](../technical/PIPELINE.md) - Data flow details
