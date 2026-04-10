# Quick Start Guide

Get the UCT Benchmark system running in 5 minutes.

## Prerequisites

- **Python 3.12+** installed
- **Java JDK 17+** installed (not just JRE)
- **Git** for cloning
- **Node.js 18+** (for web frontend)

## 1. Clone and Install (2 minutes)

```bash
# Clone the repository
git clone https://github.com/your-org/uct-benchmark.git
cd uct-benchmark/UCT-Benchmark-DMR/combined

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install Python package
pip install -e .
```

## 2. Verify Installation (30 seconds)

```bash
# Test core imports
python -c "from uct_benchmark import settings; print('Core OK')"

# Test Orekit (requires Java)
python -c "
import orekit_jpype as orekit
orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)
print('Orekit OK')
"
```

## 3. Start the Web Application (2 minutes)

### Terminal 1: Backend API

```bash
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload --port 8000
```

### Terminal 2: Frontend

```bash
cd UCT-Benchmark-DMR/combined/frontend
npm install  # First time only
npm run dev
```

### Open in Browser

Navigate to: **http://localhost:5173**

## 4. Configure Your UDL API Key

1. Go to **Settings** (gear icon in the navigation)
2. Paste your UDL API token in the API Key field
3. Click **Save** — the connection indicator should turn green

> **Demo mode:** If you don't have a UDL token, the demo site generates synthetic data. You can skip this step for demo/testing.

## 5. Generate Your First Dataset

1. Click **Generate Dataset** in the navigation
2. **Select orbital regime:** LEO (Low Earth Orbit) is recommended for quick tests
3. **Choose object type:** Unspecified is a safe default
4. **Set observation parameters:**
   - Sensor type (optical recommended)
   - Event type (normal for first test)
   - Date range (1 week is a good starting range)
   - Search strategy (Hybrid is the default)
5. **Enable optional features** (if desired):
   - Downsampling (T2+): reduces observation density
   - Simulation (T3+): fills coverage gaps with synthetic observations
6. **Name your dataset** — this is how you'll find it later
7. Click **Generate** — progress will display as the system queries UDL

Once generation completes, you'll see a summary: number of objects, observation count, and tier.

## 6. Download Your Dataset

1. Go to **My Datasets** to find your generated dataset
2. Click the dataset to view its details and preview
3. Click **Download** to save the JSON file

The downloaded file contains only the essential observation fields:
- `obTime` — observation timestamp
- `ra`, `declination` — angular position (optical)
- `azimuth`, `elevation` — angular position (radar)
- `senlat`, `senlon`, `senalt` — sensor location
- `idSensor` — which telescope/sensor
- `range`, `rangeRate` — distance measurements (radar)
- `trackId` — track association
- `split` — train or validation label

> **Important:** No satellite identification numbers are included. This is by design — participants must determine which observations belong to which objects using their UCT processor.

## 7. Submit Your Results for Evaluation

After running the downloaded dataset through your UCT processor:

1. Click **Submit** in the navigation
2. **Select the dataset** you evaluated against
3. **Upload your UCTP output file** (JSON format) — supports both state-vector and TLE formats
4. **Fill in metadata:**
   - Algorithm name (required)
   - Version (required)
   - Description (optional)
5. Click **Submit for Evaluation**

The system will validate your file format, then queue evaluation. Results include:
- **F1 Score** — observation-to-satellite correlation accuracy
- **Position/Velocity RMS** — orbit determination accuracy
- **Residual RMS** — predicted vs. actual observation fit
- **Composite Score** — weighted combination (40% binary + 30% state + 30% residual)

## 8. View Results & Leaderboard

- **My Submissions** — view your evaluation results and per-satellite breakdowns
- **Leaderboard** — see how your processor ranks against others, filterable by regime and tier

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Web interface |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger documentation |

## Troubleshooting

### Java Not Found

```bash
# Windows - Set JAVA_HOME
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot"

# macOS
brew install openjdk@17

# Ubuntu
sudo apt install openjdk-17-jdk
```

### Port Already in Use

```bash
# Change backend port
uvicorn backend_api.main:app --port 8001

# Or kill the process using the port
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
```

### Import Errors

```bash
# Ensure virtual environment is activated
# Reinstall in development mode
pip install -e .
```

## Next Steps

1. **[Beginner's Guide](guides/BEGINNER_GUIDE.md)** - Understand the concepts
2. **[Getting Started](getting-started.md)** - Detailed installation
3. **[Dataset Generation Guide](guides/DATASET_GENERATION.md)** - Create custom datasets
4. **[UI Guide](guides/UI_GUIDE.md)** - Learn the web interface

---

**Need help?** Check the [Troubleshooting Guide](guides/TROUBLESHOOTING.md) or [FAQ](reference/FAQ.md).
