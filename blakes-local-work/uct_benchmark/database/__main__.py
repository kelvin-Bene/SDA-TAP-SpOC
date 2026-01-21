"""
Entry point for running the database CLI as a module.

Usage:
    uv run python -m uct_benchmark.database <command> [options]
"""

from .cli import main

if __name__ == "__main__":
    main()
