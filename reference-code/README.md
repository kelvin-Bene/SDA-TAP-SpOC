# Reference Code

This folder contains **code from other team members and branches** - preserved for reference. This is NOT the active development codebase.

## Structure

```
reference-code/
├── master/                      # Original master branch code
│   ├── uctbenchmark/            # Original Python package
│   ├── notebooks/               # Jupyter notebooks
│   ├── tests/                   # Test files
│   └── ...
│
├── jovan-linuxTesting/          # Jovan's Linux testing branch
│   ├── uctbenchmark/            # Modified package with DuckDB, Polars
│   ├── notebooks/               # Updated notebooks
│   └── ...
│
└── uct-benchmark-refactor-joncline/  # Dr. Cline's refactored version
    ├── uct_benchmark/           # Refactored package structure
    ├── src/                     # Source code
    ├── notebooks/               # Updated notebooks
    └── ...
```

## Branch Descriptions

| Branch | Key Features | Status |
|--------|--------------|--------|
| `master` | Original implementation | Legacy - superseded |
| `jovan-linuxTesting` | DuckDB integration, Polars, Linux setup automation | Features to merge |
| `uct-benchmark-refactor-joncline` | Best architecture, Solara UI, clean module structure | **Reference architecture** |

## Recommended Usage

The `kelvin-local-work/` folder is based on the refactored architecture from `uct-benchmark-refactor-joncline`. Use these folders for:

1. **Reference** - Understanding how features were originally implemented
2. **Feature Porting** - Identifying useful features to port to the active codebase
3. **Debugging** - Comparing implementations when troubleshooting

## Key Features by Branch

### master/
- Original API integrations
- Basic window selection
- Initial evaluation metrics

### jovan-linuxTesting/
- DuckDB session management
- Polars dataframe operations
- Linux setup automation scripts
- Improved batch processing

### uct-benchmark-refactor-joncline/
- Clean module separation (api/, data/, evaluation/, simulation/, uctp/)
- Solara-based GUI
- Better configuration management
- Improved propagator implementations

## Important Notes

- **Do not develop in this folder** - use `kelvin-local-work/` for active development
- Code here is preserved for reference and feature porting
- If you need functionality from these branches, port it to `kelvin-local-work/`
