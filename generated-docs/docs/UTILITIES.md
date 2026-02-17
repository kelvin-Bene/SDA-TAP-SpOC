# Utility Modules

This document describes the utility modules in `uct_benchmark/utils/`.

## Overview

The utils package provides shared helper functions used across the codebase. These modules consolidate duplicate implementations to ensure consistency and reduce maintenance burden.

## Modules

### `orbital.py` - Orbital Regime Utilities

Provides orbital mechanics helper functions.

#### `determine_orbital_regime(semi_major_axis_km, eccentricity=0.0)`

Determines the orbital regime (LEO, MEO, GEO, or HEO) based on orbital parameters.

**Parameters:**
- `semi_major_axis_km` (float): Semi-major axis in kilometers
- `eccentricity` (float, optional): Orbital eccentricity. Default: 0.0

**Returns:**
- `str`: One of `'LEO'`, `'MEO'`, `'GEO'`, or `'HEO'`

**Classification Rules:**
1. If eccentricity >= 0.7: **HEO** (Highly Eccentric Orbit)
2. If SMA < 8,378 km: **LEO** (Low Earth Orbit)
3. If SMA >= 42,164 km: **GEO** (Geosynchronous Orbit)
4. Otherwise: **MEO** (Medium Earth Orbit)

**Example:**
```python
from uct_benchmark.utils import determine_orbital_regime

# LEO satellite (ISS)
regime = determine_orbital_regime(6778, 0.001)  # Returns 'LEO'

# GEO satellite
regime = determine_orbital_regime(42164, 0.0)   # Returns 'GEO'

# Molniya orbit (HEO)
regime = determine_orbital_regime(26554, 0.74)  # Returns 'HEO'
```

---

### `datetime_utils.py` - Datetime Parsing Utilities

Provides robust datetime parsing for the various formats used across the codebase.

#### `parse_datetime(dt_value)`

Parses a datetime from various formats into a Python `datetime` object.

**Parameters:**
- `dt_value`: Can be:
  - `datetime` object (returned as-is)
  - `pd.Timestamp` (converted to datetime)
  - String in various ISO formats

**Returns:**
- `datetime`: Parsed datetime object (naive, without timezone)

**Supported Formats:**
- `2025-01-15T12:30:45.123456Z` (ISO with microseconds and Z)
- `2025-01-15T12:30:45Z` (ISO with Z)
- `2025-01-15T12:30:45.123456` (ISO with microseconds, no Z)
- `2025-01-15T12:30:45` (ISO without microseconds or Z)
- `2025-01-15T12:30:45+00:00Z` (malformed with both +00:00 and Z)

**Example:**
```python
from uct_benchmark.utils import parse_datetime
from datetime import datetime

# Parse ISO string
dt = parse_datetime("2025-01-15T12:30:45.123456Z")
print(dt)  # datetime(2025, 1, 15, 12, 30, 45, 123456)

# Handle malformed timestamps (common in some APIs)
dt = parse_datetime("2025-01-15T12:30:45+00:00Z")
print(dt)  # datetime(2025, 1, 15, 12, 30, 45)

# Pass through existing datetime
existing = datetime(2025, 1, 15, 12, 30, 45)
result = parse_datetime(existing)
assert result is existing  # Same object
```

#### `ensure_datetime_column(df, column)`

Ensures a DataFrame column contains datetime objects.

**Parameters:**
- `df` (pd.DataFrame): DataFrame to process
- `column` (str): Name of column to convert

**Returns:**
- `pd.DataFrame`: Copy of DataFrame with converted column

**Note:** This function returns a copy and does not modify the original DataFrame.

**Example:**
```python
from uct_benchmark.utils import ensure_datetime_column
import pandas as pd

df = pd.DataFrame({
    'id': [1, 2, 3],
    'obTime': [
        '2025-01-15T12:30:45Z',
        '2025-01-16T13:45:00Z',
        '2025-01-17T14:00:30Z'
    ]
})

# Convert obTime column
df_converted = ensure_datetime_column(df, 'obTime')

# Original is unchanged
print(df['obTime'].dtype)  # object

# Converted has datetime
print(type(df_converted['obTime'].iloc[0]))  # <class 'datetime.datetime'>
```

---

### `generateCov.py` - Covariance Matrix Generation

Generates 6x6 Cartesian covariance matrices from UDL data.

#### `generateCov(vectors)`

Generates Cartesian covariance matrices from state vectors.

**Parameters:**
- `vectors` (pd.DataFrame): DataFrame of state vectors from UDL with covariance data

**Returns:**
- `pd.DataFrame`: Input DataFrame with added `cov_matrix` column

**Note:** This function handles both Cartesian and Equinoctial covariance formats from UDL.

---

### `generatePDF.py` - PDF Report Generation

Generates PDF evaluation reports.

#### `generatePDF(evals, output_path)`

Generates a PDF report from evaluation results.

**Parameters:**
- `evals`: Evaluation results dictionary
- `output_path` (str): Path to save the PDF

**Returns:**
- Path to the generated PDF file

---

## Importing Utilities

All public functions are exported from the `uct_benchmark.utils` package:

```python
# Import from package
from uct_benchmark.utils import (
    determine_orbital_regime,
    parse_datetime,
    ensure_datetime_column,
)

# Or import from specific modules
from uct_benchmark.utils.orbital import determine_orbital_regime
from uct_benchmark.utils.datetime_utils import parse_datetime
```

## Testing

Tests for utility modules are in `tests/`:

```bash
# Run all utility tests
pytest tests/test_orbital_utils.py tests/test_datetime_utils.py -v

# Run with coverage
pytest tests/test_orbital_utils.py tests/test_datetime_utils.py --cov=uct_benchmark/utils
```
