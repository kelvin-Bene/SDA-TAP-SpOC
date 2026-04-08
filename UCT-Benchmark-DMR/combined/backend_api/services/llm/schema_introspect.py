"""
Runtime DuckDB schema introspection for LLM prompts.

We don't hardcode the schema in prompts.py because (a) it would go stale, and
(b) it would couple the LLM prompt to a specific schema version. Instead, we
query `information_schema.columns` at request time, format as DDL-ish text,
and cache for 60s so we're not slamming DuckDB on every LLM call.

Only tables in prompts.ALLOWED_TABLES make it into the output.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from loguru import logger

from .prompts import ALLOWED_TABLES

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager


_CACHE_TTL_SECONDS = 60.0
_cache: dict[str, tuple[float, str]] = {}


def get_schema_ddl(db: "DatabaseManager", *, cache_key: str = "default") -> str:
    """
    Return a DDL-ish text representation of the allowlisted DuckDB tables for
    inclusion in an LLM system prompt.

    Output looks like:

        -- UCT Benchmark schema (DuckDB)
        CREATE TABLE satellites (
            sat_no INTEGER,
            name VARCHAR,
            ...
        );

        CREATE TABLE observations (
            ...
        );

    The DatabaseManager passed in should be the read-only LLM handle from
    backend_api.database.get_llm_db().
    """
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        ddl = _build_ddl(db)
    except Exception as exc:
        logger.warning(f"schema_introspect: failed to build DDL ({exc}); returning fallback")
        # Fallback: return a tiny stub so the LLM can still answer trivial
        # questions even if introspection breaks.
        ddl = "-- Schema introspection failed; only standard SDA tables are available.\n"

    _cache[cache_key] = (now, ddl)
    return ddl


def invalidate_cache(cache_key: Optional[str] = None) -> None:
    """Drop the cached DDL — call after a schema migration."""
    if cache_key is None:
        _cache.clear()
    else:
        _cache.pop(cache_key, None)


def _build_ddl(db: "DatabaseManager") -> str:
    """Query information_schema and format as DDL text."""
    # Get all column rows for allowlisted tables. DuckDB exposes
    # information_schema.columns with table_name + column_name + data_type.
    placeholders = ", ".join(["?"] * len(ALLOWED_TABLES))
    sql = f"""
        SELECT table_name, column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_name IN ({placeholders})
        ORDER BY table_name, ordinal_position
    """
    rows = db.execute(sql, tuple(ALLOWED_TABLES)).fetchall()

    if not rows:
        return "-- No allowlisted tables found in this database.\n"

    # Group columns by table
    by_table: dict[str, list[tuple[str, str, str]]] = {}
    for row in rows:
        table_name, column_name, data_type, is_nullable, _ord = row
        by_table.setdefault(table_name, []).append(
            (column_name, data_type, is_nullable)
        )

    # Format
    lines = ["-- UCT Benchmark schema (DuckDB) — read-only access"]
    for table in sorted(by_table.keys()):
        lines.append("")
        lines.append(f"CREATE TABLE {table} (")
        col_lines = []
        for col_name, col_type, nullable in by_table[table]:
            null_str = "" if nullable == "YES" else " NOT NULL"
            col_lines.append(f"    {col_name} {col_type}{null_str}")
        lines.append(",\n".join(col_lines))
        lines.append(");")

    return "\n".join(lines) + "\n"
