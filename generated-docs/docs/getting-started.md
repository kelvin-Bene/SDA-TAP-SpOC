# Getting Started

This guide provides step-by-step instructions for setting up the UCT (Uncorrelated Track) Benchmark framework for satellite tracking system evaluation.

## System Requirements

### Operating System
- **macOS**: 10.15+ (recommended for development)
- **Linux**: Ubuntu 18.04+ or equivalent
- **Windows**: 10+ (with WSL2 recommended)

### Software Prerequisites
- **Python**: 3.12+ (required)
- **Java Runtime Environment (JRE)**: Required for Orekit orbital mechanics library
- **Git**: For version control and repository cloning

### Hardware Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB free space for dependencies and data
- **Network**: Internet connection required for API access and package installation

## Installation Methods

### Method 1: Quick Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/uct-benchmark.git
   cd uct-benchmark/UCT-Benchmark-DMR/combined
   ```

2. **Set up Python environment**
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # Install using uv (fastest)
   pip install uv
   uv pip install -e .

   # OR install using pip
   pip install -e .
   ```

4. **Install development dependencies** (optional)
   ```bash
   make requirements  # Installs via uv
   # OR
   pip install -e ".[dev]"
   ```

### Method 2: Manual Setup

1. **Clone and navigate**
   ```bash
   git clone https://github.com/your-org/uct-benchmark.git
   cd uct-benchmark/UCT-Benchmark-DMR/combined
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install core dependencies**
   ```bash
   pip install pandas numpy loguru requests
   pip install orekit-jpype  # Orbital mechanics
   pip install solara ipywidgets  # GUI components
   pip install customtkinter  # Legacy GUI support
   ```

4. **Install in development mode**
   ```bash
   pip install -e .
   ```

## Post-Installation Setup

### 1. Java Environment for Orekit

Orekit-jpype requires **Java 17 or higher** (JDK, not just JRE):

```bash
# Check Java installation (must be version 17+)
java -version

# If not installed or wrong version, install Java 17:

# macOS (using Homebrew):
brew install openjdk@17

# Ubuntu/Debian:
sudo apt update && sudo apt install openjdk-17-jdk

# Windows (using winget - recommended):
winget install EclipseAdoptium.Temurin.17.JDK

# Windows (manual): Download from https://adoptium.net/
```

**Windows Users:** After installing Java, set the `JAVA_HOME` environment variable:
```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
```

For detailed Windows Orekit setup, see the [Orekit Setup Guide](guides/OREKIT_SETUP.md).

### 2. Orekit Data Files

Orekit requires ephemeris data for orbit propagation. The recommended approach is to install via pip:

```bash
# Install orekitdata package (recommended)
pip install orekitdata

# This automatically provides required ephemeris data when using:
# setup_orekit_curdir(from_pip_library=True)
```

Alternatively, the project includes orekit-data in multiple locations:
```bash
# Verify data exists (if using local data):
ls orekit-data-main/
```

### 3. API Token Configuration

Set up UDL API access (required for satellite data):

```bash
# Create environment file
echo "UDL_TOKEN=your_base64_encoded_token_here" > .env

# OR set environment variable
export UDL_TOKEN="your_base64_encoded_token_here"
```

**Getting UDL Token:**
1. Contact your data provider for UDL API credentials
2. Encode credentials as Base64: `echo -n "username:password" | base64`
3. Set the resulting string as `UDL_TOKEN`

### 4. Directory Structure Setup

Ensure required directories exist:

```bash
mkdir -p data/{raw,interim,processed,external}
mkdir -p models
mkdir -p reports/figures
```

## Verification

### 1. Test Core Installation

```bash
# Test Python imports
python -c "
from uct_benchmark import settings
from uct_benchmark.database import DatabaseManager
print('Core imports successful')
"
```

### 2. Test Orekit Integration

```bash
# Test orbital mechanics (requires Java 17+)
python -c "
import orekit_jpype as orekit
orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)
print('Orekit integration successful')
"
```

**Note:** The initialization order is critical - `orekit.initVM()` must be called BEFORE importing from `orekit_jpype.pyhelpers`.

### 3. Test GUI Components

The primary UI is the React web frontend (see "Running the Web Application" below).

```bash
# Test legacy tkinter GUI (optional CLI tool - requires display)
python -c "
import customtkinter
print('CustomTkinter GUI available')
"
```

### 4. Run Demo Pipeline

```bash
# Test full pipeline (demo mode - no network required)
python -m uct_benchmark.MainMVP
```

## Running the Web Application

### Start Backend API

```bash
# Navigate to combined directory
cd UCT-Benchmark-DMR/combined

# Start FastAPI backend
uvicorn backend_api.main:app --reload --port 8000
```

### Start Frontend

```bash
# Navigate to frontend directory
cd UCT-Benchmark-DMR/combined/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Access the application at http://localhost:5173

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip list | grep uct-benchmark
```

**2. Java/Orekit Issues**
```bash
# Check Java version (must be 17+)
java -version

# Check JAVA_HOME is set correctly
echo $JAVA_HOME  # Linux/macOS
# OR in PowerShell: $env:JAVA_HOME

# Common fix: Ensure initialization order is correct
# WRONG: from orekit_jpype.pyhelpers import setup_orekit_curdir
# RIGHT: Must call orekit.initVM() FIRST

# Reinstall orekit packages
pip uninstall orekit-jpype orekitdata
pip install orekit-jpype orekitdata
```

**3. GUI Display Issues**
```bash
# For SSH/remote sessions, enable X11 forwarding:
ssh -X user@hostname

# For WSL, install X server (e.g., VcXsrv)
export DISPLAY=:0
```

**4. Network/API Issues**
```bash
# Test network connectivity
python -c "import requests; print(requests.get('https://httpbin.org/status/200').status_code)"

# Verify UDL token format
python -c "import os; print('Token set:', bool(os.getenv('UDL_TOKEN')))"
```

**5. Package Version Conflicts**
```bash
# Known compatibility: uvicorn must be <0.25.0 for Solara
pip install "uvicorn==0.24.0.post1"

# Check for conflicts
pip check
```

### Development Environment

**Code Formatting and Linting**
```bash
make format  # Run ruff formatting
make test    # Run pytest suite
```

**Documentation**
```bash
# Build documentation
cd generated-docs/
mkdocs serve
```

## Next Steps

After successful installation:

1. **Read the documentation**: Check the [Architecture](technical/ARCHITECTURE.md) overview
2. **Run tutorials**: Explore notebooks in `notebooks/`
3. **Configure parameters**: Edit dataset parameters in GUI or programmatically
4. **Run evaluations**: Execute full pipeline with your data
5. **Explore the UI**: Access the web interface for dataset generation

## Support

- **Issues**: Report problems via GitHub Issues
- **Documentation**: Check the technical reference section
- **Examples**: See `notebooks/` for usage examples
- **Configuration**: Review `uct_benchmark/settings.py` for paths and settings

---

**Installation complete!** You're ready to generate satellite tracking benchmarks and evaluate UCTP algorithms.
