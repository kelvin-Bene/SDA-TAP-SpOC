> **Note:** This documentation has moved to `generated-docs/docs/`.
> Please see [generated-docs/docs/guides/OREKIT_SETUP.md](../../../generated-docs/docs/guides/OREKIT_SETUP.md) for the latest version.

# Windows Orekit Setup Guide

This guide provides step-by-step instructions for setting up Orekit on Windows for the UCT Benchmark simulation module.

## Prerequisites Checklist

Before starting, ensure you have:
- [ ] Windows 10 or later
- [ ] Python 3.12 installed
- [ ] Administrator access (for Java installation)
- [ ] Internet connection

---

## Step 1: Install Java JDK 17

Orekit requires Java to run. The recommended version is Java 17 (LTS).

### Option A: Using Adoptium Installer (Recommended)

1. Visit https://adoptium.net/temurin/releases/
2. Select:
   - Operating System: **Windows**
   - Architecture: **x64**
   - Package Type: **JDK**
   - Version: **17 - LTS**
3. Download the `.msi` installer
4. Run the installer and follow the prompts
   - **Important**: Check "Set JAVA_HOME variable" during installation

### Option B: Using winget (Command Line)

```powershell
# Run in PowerShell as Administrator
winget install EclipseAdoptium.Temurin.17.JDK
```

### Verify Java Installation

```powershell
# Check Java version
java -version

# Expected output:
# openjdk version "17.x.x" ...

# Check JAVA_HOME
echo $env:JAVA_HOME

# Expected output:
# C:\Program Files\Eclipse Adoptium\jdk-17.x.x-hotspot
```

If JAVA_HOME is not set, add it manually:
1. Open System Properties > Advanced > Environment Variables
2. Under System Variables, click New
3. Variable name: `JAVA_HOME`
4. Variable value: `C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot` (your actual path)
5. Click OK and restart PowerShell

---

## Step 2: Set Up Python Environment

### Navigate to Project Directory

```powershell
cd C:\Users\kelvi\Documents\SDAxSpOCUCTProcessing\kelvin-local-work
```

### Create/Activate Virtual Environment

```powershell
# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Verify activation (should show (.venv) in prompt)
```

---

## Step 3: Install Python Dependencies

### Install orekit-jpype Package

```powershell
# Install orekit-jpype (the Python-Java bridge for Orekit)
pip install orekit-jpype

# Install orekitdata (bundled ephemeris data files)
pip install orekitdata
```

### Install Full Project Dependencies

```powershell
# Install all project dependencies
pip install -e .
```

---

## Step 4: Verify Installation

### Run the Test Script

```powershell
# Run the Orekit installation test
python tests/test_orekit_installation.py
```

Expected output:
```
============================================================
    OREKIT INSTALLATION TEST SUITE
============================================================
============================================================
Test 1: Checking Java installation...
  [PASS] Java is installed
============================================================
Test 2: Testing orekit-jpype import...
  [PASS] orekit_jpype imported successfully
...
============================================================
    TEST SUMMARY
============================================================
  [PASS] Java Installation
  [PASS] orekit-jpype Import
  [PASS] JVM Initialization
  [PASS] Orekit Data Loading
  [PASS] Basic Functionality
  [PASS] TLE Propagation
  [PASS] Simulation Module Import
  [PASS] Propagator Module
------------------------------------------------------------
  Results: 8/8 tests passed

  SUCCESS! Orekit is properly installed and configured.
```

---

## Step 5: Test Simulation Module

### Quick Test

```python
# In Python interpreter
import orekit_jpype as orekit
from orekit_jpype.pyhelpers import setup_orekit_curdir

# Initialize Orekit
orekit.initVM()
setup_orekit_curdir(from_pip_library=True)

# Import simulation module
from uct_benchmark.simulation.simulateObservations import simulateObs, epochsToSim
print("Simulation module ready!")
```

---

## Troubleshooting

### Issue: "java not found" or JVM initialization fails

**Solution**: Ensure Java is in PATH
```powershell
# Check PATH
$env:PATH -split ';' | Where-Object { $_ -like '*java*' }

# If empty, add Java to PATH manually
$env:PATH += ";C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot\bin"
```

### Issue: "No module named 'orekit_jpype'"

**Solution**: Install the package
```powershell
pip install orekit-jpype
```

### Issue: "No orekit-data folder found"

**Solution**: Use the bundled data from pip
```python
# In your code, use:
setup_orekit_curdir(from_pip_library=True)

# Or set environment variable:
# OREKIT_DATA_PATH=path/to/orekit-data
```

### Issue: "OutOfMemoryError" or JVM crashes

**Solution**: Increase JVM memory
```python
import orekit_jpype
orekit_jpype.initVM(vmargs='-Xmx2g')  # 2GB heap
```

### Issue: ImportError for org.orekit modules

**Solution**: Ensure JVM is initialized BEFORE importing Orekit classes
```python
# CORRECT order:
import orekit_jpype as orekit
orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)

# NOW import Orekit classes
from org.orekit.time import TimeScalesFactory
```

### Issue: Tests pass but simulation still fails

**Solution**: Check for old 'orekit' package
```powershell
# Check if old package is installed
pip list | Select-String "orekit"

# If you see 'orekit' (not 'orekit-jpype'), uninstall it
pip uninstall orekit
```

---

## Package Version Reference

| Package | Version | Purpose |
|---------|---------|---------|
| orekit-jpype | >=13.1.2.1 | Python-Java bridge for Orekit |
| orekitdata | latest | Bundled ephemeris/data files |
| jpype1 | (auto-installed) | Python-Java interop |

---

## Architecture Overview

```
+---------------+     +-----------+     +------------+
|   Python      |     |   JPype   |     |    Java    |
|   Code        | --> | (Bridge)  | --> |   JVM      |
+---------------+     +-----------+     +------------+
       |                                      |
       v                                      v
+-----------------+               +------------------+
| orekit_jpype    |               |  Orekit Library  |
| (Python API)    |               |  (Java Classes)  |
+-----------------+               +------------------+
                                          |
                                          v
                               +--------------------+
                               |  orekit-data       |
                               |  (Ephemeris, EOP)  |
                               +--------------------+
```

---

## For Team Members

### Quick Start (After Initial Setup)

```powershell
# 1. Navigate to project
cd C:\Users\kelvi\Documents\SDAxSpOCUCTProcessing\kelvin-local-work

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Verify setup (run once)
python tests/test_orekit_installation.py

# 4. Ready to use!
```

### Important Notes

1. **Always activate the virtual environment** before running Python code
2. **Initialize Orekit first** in any script that uses orbital mechanics
3. **Use `orekit_jpype`** not the old `orekit` package
4. The bundled data (`from_pip_library=True`) is sufficient for most use cases

---

## Contact

If you encounter issues not covered here:
1. Check the error message carefully
2. Run `python tests/test_orekit_installation.py` to identify the failing component
3. Search the error in the Orekit forum: https://forum.orekit.org/
