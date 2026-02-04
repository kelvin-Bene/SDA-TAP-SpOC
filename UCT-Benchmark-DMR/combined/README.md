# UCT Benchmark - Combined Pipeline and Demo UI

A unified codebase merging Kelvin's working benchmark pipeline with Blake's demo UI and backend enhancements.

## Overview

The UCT (Uncorrelated Track) Benchmark is a comprehensive framework for evaluating orbit determination and track correlation algorithms. This combined version includes:

- **Core Pipeline**: Data acquisition, downsampling, simulation, and evaluation
- **Demo Frontend**: React-based UI for dataset management and visualization
- **Backend API**: FastAPI server connecting frontend to pipeline
- **Database Layer**: DuckDB-based persistence for datasets and results

## Quick Start

### Prerequisites

- Python 3.12+
- Java JDK 17+ (required for Orekit)
- Node.js 18+ (for frontend)
- Orekit data files (install via: `pip install git+https://gitlab.orekit.org/orekit/orekit-data.git`)

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -e .

# For development
pip install -e ".[dev]"

# Set Orekit data path
export OREKIT_DATA_PATH="/path/to/orekit-data"  # Or set in .env file
```

### Running the Pipeline

```bash
# Run validation suite
python validation/run_validation.py --target-obs 10000 --days 7

# Run evaluation on existing dataset
python Evaluation.py
```

> **Note**: Dataset creation is done through the web UI or programmatically via `uct_benchmark.api.apiIntegration.generateDataset()`

### Running the Demo UI

```bash
# Terminal 1: Start backend API
uvicorn backend_api.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

Then navigate to http://localhost:5173

## Project Structure

```
combined/
├── uct_benchmark/              # Python backend package
│   ├── api/                    # API integration (UDL, Space-Track, etc.)
│   ├── data/                   # Data manipulation and downsampling
│   ├── database/               # DuckDB persistence layer
│   ├── simulation/             # Observation simulation (Orekit)
│   ├── evaluation/             # Scoring and metrics
│   ├── uctp/                   # UCT Processing algorithms
│   └── utils/                  # Utilities
├── frontend/                   # React demo UI
├── backend_api/                # FastAPI server
├── validation/                 # Validation test suite
├── tests/                      # Unit and integration tests
├── docs/                       # Additional documentation
├── Evaluation.py               # Evaluation script
└── pyproject.toml              # Project configuration
```

## Key Components

### API Integration (`uct_benchmark/api/`)

- UDL (Unified Data Library) queries with caching and metrics
- Space-Track and CelesTrak integration
- ESA Discosweb queries
- Smart batch querying with adaptive sizing

### Data Processing (`uct_benchmark/data/`)

- Regime-aware downsampling (LEO, MEO, GEO, HEO)
- Track-preserving observation thinning
- Orbital coverage calculation
- Gap analysis

### Simulation (`uct_benchmark/simulation/`)

- Orekit-based orbit propagation
- Observation generation with noise models
- Atmospheric effects modeling

### Database (`uct_benchmark/database/`)

- DuckDB-based storage
- Dataset and result persistence
- Export/import functionality

## Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Key variables:

```env
# UDL API Token (base64 encoded)
UDL_TOKEN=your_base64_encoded_udl_token

# ESA Discosweb Token
ESA_TOKEN=your_esa_token

# Orekit Data Path
OREKIT_DATA_PATH=./orekit-data-main

# Database Backend: 'duckdb' (default) or 'postgres'
DATABASE_BACKEND=duckdb
```

See `.env.example` for all available options including PostgreSQL/Supabase configuration.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=uct_benchmark --cov-report=html

# Run specific test file
pytest tests/test_api_enhancements.py -v
```

## Documentation

### Local Documentation (`docs/`)

- [database_erd.md](docs/database_erd.md) - Database schema ERD
- [DATASET_GENERATION.md](docs/DATASET_GENERATION.md) - Dataset generation details
- [EVALUATION_METRICS.md](docs/EVALUATION_METRICS.md) - Evaluation metrics reference
- [LIMITATIONS.md](docs/LIMITATIONS.md) - Known limitations

### Full Documentation

For comprehensive guides, see the `generated-docs/docs/` directory at the repository root:

- **Getting Started**: `generated-docs/docs/QUICK_START.md`
- **Orekit Setup**: `generated-docs/docs/guides/OREKIT_SETUP.md`
- **Supabase Setup**: `generated-docs/docs/SUPABASE_SETUP.md`
- **Troubleshooting**: `generated-docs/docs/guides/TROUBLESHOOTING.md`

## Contributing

1. Create a feature branch
2. Make changes and add tests
3. Run the test suite
4. Submit a pull request

## License

[License details here]
