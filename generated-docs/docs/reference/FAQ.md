# Frequently Asked Questions

Common questions and answers about the UCT Benchmark system.

---

## Installation & Setup

### Q: What Python version do I need?

**A:** Python 3.12 or later is recommended. Python 3.9-3.11 may work but are not officially tested.

```bash
python --version  # Check your version
```

### Q: Why do I need Java for a Python project?

**A:** The Orekit library (used for orbit propagation) is written in Java. We use `orekit-jpype` to bridge Python and Java. You need **JDK 17+** (not just JRE).

```bash
java -version  # Must show 17.x or higher
```

### Q: How do I set JAVA_HOME on Windows?

**A:** Set the environment variable to point to your JDK installation:

```powershell
# Temporary (current session)
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot"

# Permanent: System Properties > Environment Variables > New
# Variable: JAVA_HOME
# Value: C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot
```

### Q: I get "No module named 'uct_benchmark'" - what's wrong?

**A:** Ensure you've installed the package in development mode:

```bash
# Activate virtual environment first!
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode
pip install -e .
```

---

## API & Authentication

### Q: How do I get a UDL API token?

**A:** UDL (Unified Data Library) access requires authorization. Contact your data provider or project lead for credentials. Once you have username/password:

```bash
# Generate Base64 token
echo -n "username:password" | base64

# Set as environment variable
export UDL_TOKEN="your_base64_token_here"
```

### Q: Can I use the system without a UDL token?

**A:** Yes, with limitations:
- **Web interface**: Use "Demo Mode" for testing with sample data
- **CLI**: Use pre-generated datasets from the database
- **CelesTrak**: Public TLE data is available without authentication

### Q: My API requests are failing with 401 errors

**A:** This indicates authentication problems:

1. Check token is set: `echo $UDL_TOKEN`
2. Verify token format (should be Base64 encoded)
3. Check token hasn't expired
4. Ensure you're using the correct API endpoint

---

## Orekit & Propagation

### Q: I get "JVM not found" or Java errors

**A:** Common fixes:

```bash
# 1. Verify Java installation
java -version

# 2. Check JAVA_HOME is set
echo $JAVA_HOME  # Linux/macOS
echo $env:JAVA_HOME  # Windows PowerShell

# 3. Ensure correct initialization order in your code
import orekit_jpype as orekit
orekit.initVM()  # MUST be called first!
from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)
```

### Q: What's the difference between `orekit` and `orekit-jpype`?

**A:** Use `orekit-jpype` (the newer package). If you have the old `orekit` package installed, remove it:

```bash
pip uninstall orekit
pip install orekit-jpype orekitdata
```

### Q: My propagation is very slow

**A:** Consider these optimizations:

1. Use `ephemerisPropagator` for multiple epochs (faster than multiple single propagations)
2. Reduce force model complexity for initial testing
3. Use TLE propagation (SGP4) for quick estimates

---

## Dataset Generation

### Q: What do the tier levels (T1-T4) mean?

**A:**

| Tier | Description | Use Case |
|------|-------------|----------|
| T1 | Full real observations | Easy testing |
| T2 | Downsampled (fewer obs) | Test with sparse data |
| T3 | Simulated observations | Fill gaps in real data |
| T4 | Fully synthetic objects | Test with unknown objects |

### Q: How long does dataset generation take?

**A:** It depends on:
- Number of satellites (10 objects: ~1 min, 100 objects: ~10 min)
- Time window (longer = more data to pull)
- Network speed (API calls)
- Tier level (T3 simulation adds time)

### Q: My dataset generation failed midway

**A:** The system creates partial datasets. Check:

1. Network connectivity
2. API rate limits (wait and retry)
3. Log files for specific errors
4. Database status: `python -m uct_benchmark.database status`

---

## Web Interface

### Q: The frontend won't start

**A:** Common issues:

```bash
# Check Node.js version (need 18+)
node --version

# Reinstall dependencies
cd frontend
rm -rf node_modules
npm install

# Start development server
npm run dev
```

### Q: Port 5173 is already in use

**A:** Either stop the other process or use a different port:

```bash
# Linux/macOS - find process
lsof -i :5173

# Windows - find process
netstat -ano | findstr :5173

# Or use different port
npm run dev -- --port 3001
```

### Q: The frontend can't connect to the backend

**A:** Ensure:

1. Backend is running on port 8000: `uvicorn backend_api.main:app --port 8000`
2. No CORS issues (backend allows localhost:5173)
3. Check browser console for specific errors

---

## Evaluation & Metrics

### Q: What format should my algorithm output be in?

**A:** Submit results as JSON with this structure:

```json
[
  {
    "idStateVector": 0,
    "sourcedData": ["obs_id1", "obs_id2"],
    "epoch": "2025-01-01T00:00:00.000000",
    "xpos": -7365.971,
    "ypos": -1331.400,
    "zpos": 1514.249,
    "xvel": 1.977,
    "yvel": -5.225,
    "zvel": 4.473,
    "referenceFrame": "J2000"
  }
]
```

### Q: How is F1 score calculated?

**A:** F1 is the harmonic mean of precision and recall:

```
Precision = True Positives / (True Positives + False Positives)
Recall = True Positives / (True Positives + False Negatives)
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

### Q: My position error is very high - what's wrong?

**A:** Check:

1. **Reference frame**: Ensure you're using J2000 ECI
2. **Units**: Positions in km, velocities in km/s
3. **Epoch alignment**: Compare at the same epoch
4. **Association**: Verify orbit-to-truth matching is correct

---

## Database

### Q: How do I reset the database?

**A:** Reinitialize with the force flag:

```bash
python -m uct_benchmark.database init --force
```

### Q: Can I export data to use elsewhere?

**A:** Yes, multiple formats are supported:

```bash
# Export dataset to JSON
python -m uct_benchmark.database export --dataset-id 1 -o dataset.json

# Export observations to Parquet
python -m uct_benchmark.database export --observations -o observations.parquet
```

### Q: How do I back up my data?

**A:**

```bash
# Create backup
python -m uct_benchmark.database backup -o backup.duckdb

# Restore from backup
python -m uct_benchmark.database restore backup.duckdb
```

---

## Contributing

### Q: How do I report a bug?

**A:** Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Environment details (OS, Python version, etc.)

### Q: Can I contribute code?

**A:** Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Still Need Help?

- Check the [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)
- Read the [Getting Started](../getting-started.md) guide
- Review the [Glossary](GLOSSARY.md) for terminology
- Contact the project maintainers
