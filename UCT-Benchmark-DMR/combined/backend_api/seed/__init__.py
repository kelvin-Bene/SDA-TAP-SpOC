"""
DGX Spark seed-data loader.

This package is only invoked when LOCAL_DGX_MODE=true is set in the environment
(see backend_api/main.py lifespan). It populates an empty DuckDB with bundled
sample observations and satellites so the app is usable out-of-the-box on a
freshly delivered DGX Spark — no UDL/ESA token required.

Cloud builds (Railway master/dev) never call into this package.
"""

from .seed_database import maybe_seed_database

__all__ = ["maybe_seed_database"]
