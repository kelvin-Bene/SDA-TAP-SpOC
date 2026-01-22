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
- Node.js 18+ (for frontend)
- Orekit data files (see [WINDOWS_OREKIT_SETUP.md](docs/WINDOWS_OREKIT_SETUP.md))

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

# Create a dataset
python Create_Dataset.py

# Run evaluation
python Evaluation.py
```

### Running the Demo UI

```bash
# Terminal 1: Start backend API
uvicorn backend_api.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

Then navigate to http://localhost:5173 (or http://localhost:3000).

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
├── docs/                       # Documentation
├── MainMVP.py                  # Main entry point
├── Create_Dataset.py           # Dataset creation script
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

Create a `.env` file:

```env
# UDL Credentials
UDL_USERNAME=your_username
UDL_PASSWORD=your_password

# ESA Discosweb Token
ESA_TOKEN=your_token

# Orekit Data Path
OREKIT_DATA_PATH=/path/to/orekit-data

# Database (optional)
DATABASE_PATH=./data/benchmark.duckdb
```

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

See the `docs/` directory for detailed documentation:

- [INSTALLATION.md](docs/INSTALLATION.md) - Detailed setup instructions
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [API_INTEGRATION.md](docs/API_INTEGRATION.md) - API usage patterns
- [DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md) - Database design
- [WINDOWS_OREKIT_SETUP.md](docs/WINDOWS_OREKIT_SETUP.md) - Orekit setup on Windows
- [COMPONENTS.md](docs/COMPONENTS.md) - UI component reference
- [CHANGELOG.md](docs/CHANGELOG.md) - Version history

## Contributing

1. Create a feature branch
2. Make changes and add tests
3. Run the test suite
4. Submit a pull request

## License

[License details here]
