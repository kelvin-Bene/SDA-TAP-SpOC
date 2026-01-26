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

## 4. Generate Your First Dataset

### Option A: Web Interface

1. Open http://localhost:5173
2. Click "Datasets" in the navigation
3. Click "Generate New Dataset"
4. Select orbital regime (LEO recommended for quick tests)
5. Click "Generate"

### Option B: Command Line

```python
from uct_benchmark.database import DatabaseManager
from uct_benchmark.api.apiIntegration import generateDataset

# Initialize database
db = DatabaseManager()
db.initialize()

# Generate a test dataset (requires UDL token for real data)
# For demo/testing, use the web interface with demo mode
```

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
