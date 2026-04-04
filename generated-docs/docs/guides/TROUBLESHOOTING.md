# Troubleshooting Guide

Solutions to common problems when using the UCT Benchmark system.

---

## Installation Issues

### Python Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'uct_benchmark'`

**Solutions:**

1. **Activate virtual environment**
   ```bash
   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

2. **Install package in development mode**
   ```bash
   pip install -e .
   ```

3. **Verify installation**
   ```bash
   pip list | grep uct-benchmark
   ```

---

### Java/JVM Errors

**Symptom:** "JVM not found", "Access violation", or Orekit initialization fails

**Solutions:**

1. **Check Java version** (must be JDK 17+)
   ```bash
   java -version
   ```

2. **Set JAVA_HOME correctly**
   ```bash
   # Windows PowerShell
   $env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot"

   # Linux/macOS
   export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
   ```

3. **Ensure correct initialization order**
   ```python
   # CORRECT ORDER - JVM first!
   import orekit_jpype as orekit
   orekit.initVM()  # MUST be first
   from orekit_jpype.pyhelpers import setup_orekit_curdir
   setup_orekit_curdir(from_pip_library=True)
   ```

4. **Clear conflicting packages**
   ```bash
   pip uninstall orekit  # Remove old package
   pip install orekit-jpype orekitdata
   ```

---

### Orekit Data Errors

**Symptom:** "No orekit-data folder found" or "Cannot find leap seconds file"

**Solutions:**

1. **Use pip library data** (recommended)
   ```python
   setup_orekit_curdir(from_pip_library=True)
   ```

2. **Install orekitdata package**
   ```bash
   pip install orekitdata
   ```

3. **Set environment variable** (alternative)
   ```bash
   export OREKIT_DATA_PATH=/path/to/orekit-data
   ```

---

## Runtime Errors

### TLE Parsing Failures

**Symptom:** "Invalid TLE format" or parsing exceptions

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Line length wrong | TLE lines must be exactly 69 characters |
| Invalid checksum | Verify TLE source data integrity |
| Epoch in future | Some systems reject TLEs with future dates |
| Missing line | Ensure both line1 and line2 are present |

**Verification:**
```python
# Check TLE format
line1 = "1 25544U 98067A   21275.52063657..."  # 69 chars
line2 = "2 25544  51.6442 208.4112 ..."         # 69 chars
print(f"Line 1 length: {len(line1)}")  # Should be 69
print(f"Line 2 length: {len(line2)}")  # Should be 69
```

---

### Database Locked Errors

**Symptom:** "Cannot write to database" or "database is locked"

**Solutions:**

1. **Close other connections**
   - Exit other Python sessions using the database
   - Close database browser tools (DBeaver, etc.)

2. **Check for zombie processes**
   ```bash
   # Find Python processes
   ps aux | grep python  # Linux/macOS
   tasklist | findstr python  # Windows
   ```

3. **Force unlock** (use carefully)
   ```bash
   python -m uct_benchmark.database verify
   ```

---

### Memory Errors

**Symptom:** `OutOfMemoryError` or system becomes unresponsive

**Solutions:**

1. **Increase JVM heap size**
   ```python
   import orekit_jpype
   orekit_jpype.initVM(vmargs='-Xmx4g')  # 4GB heap
   ```

2. **Process data in batches**
   ```python
   # Instead of loading all at once
   for batch in dataset.iter_batches(size=1000):
       process(batch)
   ```

3. **Close resources**
   ```python
   # Explicitly close database connections
   db.close()
   ```

---

## Web Application Issues

### Frontend Won't Start

**Symptom:** `npm run dev` fails or shows errors

**Solutions:**

1. **Check Node.js version** (need 18+)
   ```bash
   node --version
   ```

2. **Clean install dependencies**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Check for port conflicts**
   ```bash
   # Find process using port 5173
   lsof -i :5173  # macOS/Linux
   netstat -ano | findstr :5173  # Windows
   ```

---

### Backend API Errors

**Symptom:** API returns 500 errors or won't start

**Solutions:**

1. **Check Python environment**
   ```bash
   which python  # Should point to .venv
   pip list | grep fastapi
   ```

2. **Verify database access**
   ```bash
   python -m uct_benchmark.database status
   ```

3. **Check logs**
   ```bash
   uvicorn backend_api.main:app --reload --log-level debug
   ```

---

### CORS Errors

**Symptom:** Browser console shows "CORS policy" errors

**Solutions:**

1. **Verify backend is running** on expected port
2. **Check frontend is using correct API URL**
3. **Backend should allow localhost origins** (check `main.py` CORS settings)

---

## API & Network Issues

### Rate Limiting

**Symptom:** API calls fail after working initially

**Solutions:**

1. **Add delays between requests**
   ```python
   import time
   for item in items:
       result = api_call(item)
       time.sleep(0.5)  # 500ms delay
   ```

2. **Use batch API calls** when available

3. **Cache results** to avoid repeated calls

---

### Authentication Failures

**Symptom:** 401 Unauthorized errors

**Solutions:**

1. **Verify token is set**
   ```bash
   echo $UDL_TOKEN  # Should show your token
   ```

2. **Check token format** (should be Base64)
   ```bash
   echo -n "username:password" | base64
   ```

3. **Test token manually**
   ```python
   import requests
   headers = {"Authorization": f"Basic {token}"}
   response = requests.get(url, headers=headers)
   print(response.status_code)
   ```

---

## Platform-Specific Issues

### Windows

**Path issues with spaces:**
```powershell
# Use quotes around paths
cd "C:\Users\My Name\project"
```

**PowerShell execution policy:**
```powershell
# If .venv\Scripts\Activate.ps1 fails
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Line endings:**
```bash
# If scripts fail with "bad interpreter"
git config --global core.autocrlf input
```

---

### macOS

**Xcode command line tools:**
```bash
# If build tools are missing
xcode-select --install
```

**Homebrew Java:**
```bash
# Add to ~/.zshrc or ~/.bash_profile
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

---

### Linux

**Missing system packages:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-dev build-essential openjdk-17-jdk

# Fedora/RHEL
sudo dnf install python3-devel java-17-openjdk-devel
```

**Display issues (headless servers):**
```bash
# For GUI components
export DISPLAY=:0
# Or use Xvfb for virtual display
```

---

## Getting Help

If these solutions don't resolve your issue:

1. **Check the [FAQ](../reference/FAQ.md)** for more answers
2. **Search existing GitHub issues** for similar problems
3. **Create a new issue** with:
   - Steps to reproduce
   - Full error message/traceback
   - Environment details (OS, Python version, etc.)
   - What you've already tried

---

## Diagnostic Commands

Collect this information when reporting issues:

```bash
# System info
python --version
java -version
node --version  # If using frontend
npm --version   # If using frontend

# Package versions
pip list | grep -E "(uct|orekit|fastapi|duckdb)"

# Environment
echo $JAVA_HOME
echo $UDL_TOKEN | head -c 10  # First 10 chars only (don't share full token)

# Database status
python -m uct_benchmark.database status

# Test imports
python -c "from uct_benchmark import settings; print('OK')"
```
