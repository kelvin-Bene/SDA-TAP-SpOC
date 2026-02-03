# UCT Benchmark Test Suite

This document describes how to run the comprehensive test suite for the UCT Benchmark project.

## Test Files Created

### Python Tests

| File | Description |
|------|-------------|
| `test_comprehensive_unit.py` | Unit tests for all new functions and changes |
| `test_comprehensive_integration.py` | Integration tests for cross-component functionality |
| `test_full_pipeline_integration.py` | End-to-end pipeline tests |
| `test_regression.py` | Backward compatibility tests |

### Playwright E2E Tests

| File | Description |
|------|-------------|
| `e2e/test_comprehensive_e2e.spec.ts` | Comprehensive UI/E2E tests |
| `e2e/test_dataset_generator_ui.spec.ts` | Dataset generator page tests |

## Running Python Tests

### Run All Tests
```bash
cd UCT-Benchmark-DMR/combined
pytest tests/ -v
```

### Run Specific Test Files
```bash
# Unit tests
pytest tests/test_comprehensive_unit.py -v

# Integration tests
pytest tests/test_comprehensive_integration.py -v

# Full pipeline tests
pytest tests/test_full_pipeline_integration.py -v

# Regression tests
pytest tests/test_regression.py -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=uct_benchmark --cov-report=html -v
```

### Run Tests by Category
```bash
# Test target percentage enforcement
pytest tests/ -k "target_percentage" -v

# Test window selection
pytest tests/ -k "window" -v

# Test TrackTLE
pytest tests/ -k "tracktle" -v

# Test legacy codes
pytest tests/ -k "legacy" -v

# Test backward compatibility
pytest tests/ -k "backward" -v
```

## Running Playwright E2E Tests

### Prerequisites
```bash
cd UCT-Benchmark-DMR/combined/tests/e2e
npm install
npx playwright install chromium
```

### Start the Application
Before running E2E tests, start the backend and frontend:

```bash
# Terminal 1: Start backend
cd UCT-Benchmark-DMR/combined
python -m backend_api.main

# Terminal 2: Start frontend
cd UCT-Benchmark-DMR/combined/frontend
npm run dev
```

### Run All E2E Tests
```bash
cd UCT-Benchmark-DMR/combined/tests/e2e
npx playwright test
```

### Run Specific E2E Test Files
```bash
# Comprehensive E2E tests
npx playwright test test_comprehensive_e2e.spec.ts

# Dataset generator tests
npx playwright test test_dataset_generator_ui.spec.ts
```

### Run E2E Tests with UI
```bash
npx playwright test --ui
```

### Run E2E Tests in Debug Mode
```bash
npx playwright test --debug
```

### Generate E2E Test Report
```bash
npx playwright test --reporter=html
npx playwright show-report
```

## Test Categories Covered

### 1. Target Percentage Enforcement
- 50%, 10%, 1% enforcement
- UN (unspecified) bypass
- Metadata structure

### 2. Window Selection
- Tier enum values (T1-T5)
- Default enabled behavior
- Criteria creation

### 3. TrackTLE Integration
- Observation dataclass
- TrackTLEResult dataclass
- IOD requirements (min 3 obs)

### 4. Legacy Code Parsing
- 16-character code parsing
- All object types (H, C, A, U, N)
- All event types (MB, BU, LL, NE)
- Target percentages (50, 10, 01, UN)
- Code roundtrip

### 5. Backend API Models
- DatasetCreate new fields
- Default values
- JSON serialization

### 6. Decorrelation
- satNo removal
- Data preservation
- Answer key generation

### 7. True Negatives
- Exactly 2 obs per satellite
- Non-reference flagging

### 8. Backward Compatibility
- Existing parameters unchanged
- Legacy mappings preserved
- Settings constants unchanged

## Expected Test Results

All tests should pass. If any tests fail, it indicates:

1. **Unit test failures**: Core function logic issues
2. **Integration test failures**: Cross-component communication issues
3. **Regression test failures**: Breaking changes to existing functionality
4. **E2E test failures**: UI or API endpoint issues

## Troubleshooting

### Module Import Errors
```bash
# Ensure you're in the right directory with proper PYTHONPATH
cd UCT-Benchmark-DMR/combined
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v
```

### Orekit/JPype Errors
Some tests may require Orekit. Skip those with:
```bash
pytest tests/ -v --ignore=tests/test_simulation_full.py
```

### E2E Tests Timeout
Increase timeout in playwright.config.ts or use:
```bash
npx playwright test --timeout=60000
```
