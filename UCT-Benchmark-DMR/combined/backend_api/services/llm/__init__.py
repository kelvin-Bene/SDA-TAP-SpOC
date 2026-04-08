"""
DGX Spark Phase 2 — LLM-powered features.

This package only loads when the backend is running in DGX local edition mode
(LOCAL_DGX_MODE=true). The cloud builds on Railway never import anything from
here because backend_api.main mounts the llm router inside an env-guarded
block at startup.

Modules:
    client          — thin async httpx wrapper around the in-cluster Ollama service
    prompts         — system prompts + ALLOWED_TABLES / DENIED_TABLES constants
    sql_safety      — sqlglot-based AST validator for LLM-generated SELECT queries
    schema_introspect — runtime DuckDB schema dump for inclusion in LLM prompts

Routes that consume this package live in backend_api/routers/llm.py.
"""

from .client import OllamaClient, complete

__all__ = ["OllamaClient", "complete"]
