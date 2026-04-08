"""
SQL safety validator for LLM-generated queries.

5-layer defense (this module covers layers 2-4; the read-only DuckDB handle
covers layer 1, the wall-clock timeout covers layer 5):

  L2: parse the query with sqlglot. Reject if it's not a single statement
      OR if the top-level statement isn't a SELECT.
  L3: walk the AST. Reject if it references any table NOT in ALLOWED_TABLES,
      OR if it touches any table in DENIED_TABLES (redundant — should never
      happen if L2 passed and the schema introspection is honest, but cheap
      and explicit).
  L4: inject `LIMIT 500` if the query has no LIMIT.

Returns a sanitized SQL string ready to execute, or raises SqlSafetyError
with a user-friendly message.
"""

from __future__ import annotations

import re
from typing import Optional

import sqlglot
from sqlglot import exp

from .prompts import ALLOWED_TABLES, DENIED_TABLES


MAX_DEFAULT_LIMIT = 500


class SqlSafetyError(ValueError):
    """Raised when LLM-generated SQL is rejected by the safety validator."""


def validate_and_rewrite(sql: str) -> str:
    """
    Validate the given SQL string and return a sanitized version safe to
    execute against the read-only DuckDB handle.

    Raises SqlSafetyError on any violation. The error message is safe to
    surface to the user.
    """
    if not sql or not sql.strip():
        raise SqlSafetyError("Empty query")

    cleaned = _strip_markdown_fences(sql).strip().rstrip(";").strip()
    if not cleaned:
        raise SqlSafetyError("Empty query after stripping markdown fences")

    # If the LLM emitted a "cannot answer" comment per the A1 prompt, surface
    # that as a friendly error.
    if cleaned.startswith("--"):
        first_line = cleaned.splitlines()[0]
        raise SqlSafetyError(first_line.lstrip("- ").strip())

    try:
        parsed = sqlglot.parse(cleaned, read="duckdb")
    except Exception as exc:
        raise SqlSafetyError(f"Could not parse SQL: {exc}") from exc

    # Reject anything that isn't exactly one statement
    statements = [s for s in parsed if s is not None]
    if len(statements) != 1:
        raise SqlSafetyError(
            f"Expected a single SELECT statement, got {len(statements)} statements"
        )

    statement = statements[0]

    # The top-level node must be a SELECT
    if not isinstance(statement, exp.Select):
        kind = type(statement).__name__
        raise SqlSafetyError(
            f"Only SELECT queries are allowed (got {kind})"
        )

    # Walk the AST and check for any nested forbidden node types.
    # The set of node types we don't allow at any depth.
    forbidden_node_types: tuple[type, ...] = (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
        exp.AlterTable if hasattr(exp, "AlterTable") else exp.Alter,
        exp.Command,  # generic catch-all for things sqlglot doesn't model
    )
    for node in statement.walk():
        if isinstance(node, forbidden_node_types):
            kind = type(node).__name__
            raise SqlSafetyError(f"Disallowed SQL operation: {kind}")

    # Walk again for table references; reject any not in the allowlist.
    referenced_tables: set[str] = set()
    for table_node in statement.find_all(exp.Table):
        # exp.Table.name returns the bare table name (no schema/db prefix)
        name = (table_node.name or "").lower()
        if name:
            referenced_tables.add(name)

    if not referenced_tables:
        # A SELECT with no tables (e.g. SELECT 1) is harmless but probably not
        # what the user wanted. Allow it.
        pass

    denied = referenced_tables & {t.lower() for t in DENIED_TABLES}
    if denied:
        raise SqlSafetyError(
            f"Query references protected table(s): {', '.join(sorted(denied))}"
        )

    bad = referenced_tables - {t.lower() for t in ALLOWED_TABLES}
    if bad:
        raise SqlSafetyError(
            f"Query references unknown table(s): {', '.join(sorted(bad))}. "
            f"Available tables: {', '.join(sorted(ALLOWED_TABLES))}"
        )

    # Inject LIMIT if missing.
    if statement.args.get("limit") is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(MAX_DEFAULT_LIMIT)))

    # Re-emit as DuckDB SQL.
    return statement.sql(dialect="duckdb")


_FENCE_RE = re.compile(r"^```(?:sql|duckdb)?\s*\n?|\n?```\s*$", re.IGNORECASE | re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    """Remove ```sql ... ``` style fences if the LLM emitted them despite the prompt instruction."""
    return _FENCE_RE.sub("", text)


def extract_sql_from_response(text: str) -> Optional[str]:
    """
    Extract a SQL query from a model response that may contain prose around it.

    Used by:
      - A1 endpoint when the LLM violates the "ONLY SQL" instruction
      - A3 chat tool-use loop when scanning for `<sql>...</sql>` tags

    Returns None if no plausible SQL can be found.
    """
    if not text:
        return None

    # First try the <sql>...</sql> tag form (A3 protocol)
    tag_match = re.search(r"<sql>(.*?)</sql>", text, re.DOTALL | re.IGNORECASE)
    if tag_match:
        return tag_match.group(1).strip()

    # Then try a markdown fence
    fence_match = re.search(r"```(?:sql|duckdb)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # Then look for the first SELECT ... ; or SELECT ... <end>
    select_match = re.search(
        r"(SELECT\b.*?)(?:;|\Z)", text, re.DOTALL | re.IGNORECASE
    )
    if select_match:
        return select_match.group(1).strip()

    return None
