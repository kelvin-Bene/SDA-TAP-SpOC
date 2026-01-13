# Installation Guide

This guide provides step-by-step instructions for setting up the UCT (Uncorrelated Track) Benchmark framework for satellite tracking system evaluation.

## System Requirements

### Operating System
- **macOS**: 10.15+ (recommended for development)
- **Linux**: Ubuntu 18.04+ or equivalent
- **Windows**: 10+ (with WSL2 recommended)

### Software Prerequisites
- **Python**: 3.9-3.12 (3.12 recommended)
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
   cd uct-benchmark
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
   cd uct-benchmark
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

Orekit requires Java Runtime Environment:

```bash
# Check Java installation
java -version

# If not installed, install Java:
# macOS (using Homebrew):
brew install openjdk

# Ubuntu/Debian:
sudo apt update && sudo apt install default-jre

# Windows: Download from https://adoptium.net/
```

### 2. Orekit Data Files

Download and place Orekit ephemeris data:

```bash
# The project includes orekit-data in multiple locations:
# - src/orekit-data-main/
# - data/external/orekit-data-main/

# Verify data exists:
ls src/orekit-data-main/
ls data/external/orekit-data-main/
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
from uct_benchmark import config
from uct_benchmark.Create_Dataset import launch_gui, create_datasets_from_codes
print('✓ Core imports successful')
"
```

### 2. Test Orekit Integration

```bash
# Test orbital mechanics
python -c "
import orekit
from org.orekit.python import PythonUtils
PythonUtils.initializeJVM()
print('✓ Orekit integration successful')
"
```

### 3. Test GUI Components

```bash
# Test Solara web GUI (optional - requires display)
python -c "
import solara
print('✓ Solara GUI available')
"

# Test legacy tkinter GUI (optional - requires display)
python -c "
import customtkinter
print('✓ CustomTkinter GUI available')
"
```

### 4. Run Demo Pipeline

```bash
# Test full pipeline (demo mode - no network required)
python -m uct_benchmark.MainMVP
```

## GUI Setup

### Web-based GUI (Solara)

1. **Launch Solara server**
   ```bash
   solara run uct_benchmark.data.window_main:App --host localhost --port 8766
   ```

2. **Access GUI**
   - Open browser to: http://localhost:8766
   - Use demo mode if UDL token not available

### Desktop GUI (Legacy)

```bash
# Launch parameter editor GUI
python uct_benchmark/scripts/run_create_dataset_gui.py

# OR programmatically
python -c "
from uct_benchmark.Create_Dataset import launch_gui
df = launch_gui()
print(f'Generated {len(df)} configurations')
"
```

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
# Check Java path
which java
echo $JAVA_HOME

# Reinstall orekit-jpype
pip uninstall orekit-jpype
pip install orekit-jpype
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
# Build documentation (if available)
cd docs/
mkdocs serve
```

## Docker Setup (Alternative)

For containerized deployment:

```dockerfile
# Example Dockerfile (create as needed)
FROM python:3.12-slim

RUN apt-update && apt-get install -y default-jre git
WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8766
CMD ["solara", "run", "uct_benchmark.data.window_main:App", "--host", "0.0.0.0"]
```

```bash
# Build and run
docker build -t uct-benchmark .
docker run -p 8766:8766 -e UDL_TOKEN="your_token" uct-benchmark
```

## Next Steps

After successful installation:

1. **Read the documentation**: Check `README.md` and `docs/` directory
2. **Run tutorials**: Explore notebooks in `notebooks/`
3. **Configure parameters**: Edit dataset parameters in GUI or programmatically
4. **Run evaluations**: Execute full pipeline with your data

## Support

- **Issues**: Report problems via GitHub Issues
- **Documentation**: Check `docs/` directory and inline docstrings
- **Examples**: See `notebooks/` for usage examples
- **Configuration**: Review `uct_benchmark/config.py` for paths and settings

---

**Installation complete!** You're ready to generate satellite tracking benchmarks and evaluate UCTP algorithms.