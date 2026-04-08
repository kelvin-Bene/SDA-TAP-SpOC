"""
DGX Spark Phase 2 — LLM-powered API endpoints.

This router is mounted by backend_api/main.py ONLY when LOCAL_DGX_MODE=true.
The cloud (Railway) builds never import this module — see the env-guarded
include_router block in main.py.

Endpoints:
    POST /api/v1/llm/sql              — A1: NL → SQL → DuckDB → result table
    POST /api/v1/llm/explain-results  — A2: explain a submission's metrics in plain English
    POST /api/v1/llm/chat             — A3: multi-turn chat with optional SQL tool use
    POST /api/v1/llm/suggest-fix      — A4: explain a UCTP validation error and suggest a fix

Auth: every endpoint uses Depends(get_current_user) which honors DEMO_MODE.
"""

from __future__ import annotations

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from backend_api.auth import CurrentUser, get_current_user
from backend_api.database import get_db, get_llm_db
from backend_api.services.llm import complete
from backend_api.services.llm.client import OllamaClient
from backend_api.services.llm.prompts import A1_SYSTEM, A2_SYSTEM, A3_SYSTEM, A4_SYSTEM
from backend_api.services.llm.schema_introspect import get_schema_ddl
from backend_api.services.llm.sql_safety import (
    SqlSafetyError,
    extract_sql_from_response,
    validate_and_rewrite,
)
from uct_benchmark.database.connection import DatabaseManager


router = APIRouter()


# Single executor used to enforce wall-clock timeouts on DuckDB queries.
# DuckDB has no statement_timeout setting, so we run the query in a worker
# thread and call .result(timeout=N) which raises TimeoutError after N
# seconds. The future keeps running in the background — DuckDB will finish
# eventually — but we return to the client immediately.
_QUERY_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-sql-")
_DEFAULT_QUERY_TIMEOUT_S = 5.0


# ─────────────────────────────────────────────────────────────────────────────
# Health helper — every route uses this to surface a friendly error when
# the Ollama sidecar is unreachable.
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_ollama_up() -> None:
    client = OllamaClient()
    if not await client.health():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI features unavailable — the Ollama service is not reachable. "
                "Check that the GPU compose profile is up: "
                "`docker compose --profile gpu up -d`"
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# A1 — Natural-language SQL
# ─────────────────────────────────────────────────────────────────────────────

class SqlQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class SqlQueryResponse(BaseModel):
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    truncated: bool


@router.post("/sql", response_model=SqlQueryResponse)
async def nl_to_sql(
    body: SqlQueryRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_llm_db),
):
    """A1 — Translate a natural-language question to SQL, validate, execute."""
    await _ensure_ollama_up()

    schema = get_schema_ddl(db)
    user_msg = f"Schema:\n{schema}\n\nQuestion: {body.question}\n\nReturn ONLY the SQL query."
    try:
        raw = await complete(
            messages=[
                {"role": "system", "content": A1_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=400,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error(f"A1: Ollama call failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM call failed: {exc}",
        )

    # Extract SQL — the model may have ignored the "ONLY SQL" instruction
    candidate = extract_sql_from_response(raw) or raw

    try:
        safe_sql = validate_and_rewrite(candidate)
    except SqlSafetyError as exc:
        logger.info(f"A1: rejected unsafe SQL: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Query rejected by safety validator",
                "reason": str(exc),
                "raw_sql": candidate.strip()[:500],
            },
        )

    # Execute under wall-clock timeout
    try:
        rows, columns = await asyncio.get_event_loop().run_in_executor(
            None, _run_query_with_timeout, db, safe_sql
        )
    except FutureTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Query exceeded {_DEFAULT_QUERY_TIMEOUT_S}s execution limit",
        )
    except Exception as exc:
        logger.warning(f"A1: query execution failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Query execution failed",
                "reason": str(exc),
                "sql": safe_sql,
            },
        )

    truncated = len(rows) >= 500
    return SqlQueryResponse(
        sql=safe_sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
    )


def _run_query_with_timeout(db: DatabaseManager, sql: str):
    """Runs in a worker thread; raises FutureTimeoutError if it doesn't finish in time."""
    future = _QUERY_EXECUTOR.submit(_execute_and_materialize, db, sql)
    return future.result(timeout=_DEFAULT_QUERY_TIMEOUT_S)


def _execute_and_materialize(db: DatabaseManager, sql: str):
    """Inside the worker thread: execute, materialize to list-of-dicts."""
    result = db.execute(sql)
    columns = [desc[0] for desc in result.description]
    raw_rows = result.fetchall()
    rows = [dict(zip(columns, _coerce_row(row))) for row in raw_rows[:500]]
    return rows, columns


def _coerce_row(row):
    """Convert any non-JSON-serializable values to plain Python types."""
    out = []
    for v in row:
        if hasattr(v, "isoformat"):  # datetime/date
            out.append(v.isoformat())
        elif hasattr(v, "__float__") and not isinstance(v, (int, float, bool)):
            try:
                out.append(float(v))
            except Exception:
                out.append(str(v))
        else:
            out.append(v)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# A2 — Explain my results
# ─────────────────────────────────────────────────────────────────────────────

class ExplainResultsRequest(BaseModel):
    submission_id: int


class ExplainResultsResponse(BaseModel):
    text: str


@router.post("/explain-results", response_model=ExplainResultsResponse)
async def explain_results(
    body: ExplainResultsRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """A2 — Plain-English interpretation of a submission's metrics."""
    await _ensure_ollama_up()

    # Fetch the submission + results blob via direct SQL (avoid importing
    # the results router to keep this module decoupled).
    row = db.execute(
        """
        SELECT s.id, s.algorithm_name, s.version, s.dataset_id,
               sr.true_positives, sr.false_positives, sr.false_negatives,
               sr.precision, sr.recall, sr.f1_score, sr.accuracy, sr.specificity,
               sr.position_rms_km, sr.velocity_rms_km_s,
               sr.ra_residual_rms_arcsec, sr.dec_residual_rms_arcsec,
               sr.mahalanobis_distance, sr.composite_score
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.id = ?
        """,
        (body.submission_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    metrics = {
        "submission_id": row[0],
        "algorithm_name": row[1],
        "version": row[2],
        "dataset_id": row[3],
        "true_positives": row[4],
        "false_positives": row[5],
        "false_negatives": row[6],
        "precision": float(row[7]) if row[7] is not None else None,
        "recall": float(row[8]) if row[8] is not None else None,
        "f1_score": float(row[9]) if row[9] is not None else None,
        "accuracy": float(row[10]) if row[10] is not None else None,
        "specificity": float(row[11]) if row[11] is not None else None,
        "position_rms_km": float(row[12]) if row[12] is not None else None,
        "velocity_rms_km_s": float(row[13]) if row[13] is not None else None,
        "ra_residual_rms_arcsec": float(row[14]) if row[14] is not None else None,
        "dec_residual_rms_arcsec": float(row[15]) if row[15] is not None else None,
        "mahalanobis_distance": float(row[16]) if row[16] is not None else None,
        "composite_score": float(row[17]) if row[17] is not None else None,
    }

    user_msg = f"Submission metrics:\n{_format_metrics(metrics)}"

    try:
        text = await complete(
            messages=[
                {"role": "system", "content": A2_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.4,
        )
    except Exception as exc:
        logger.error(f"A2: Ollama call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    return ExplainResultsResponse(text=text.strip())


def _format_metrics(metrics: Dict[str, Any]) -> str:
    """Tiny key: value pretty-printer for the LLM context."""
    lines = []
    for k, v in metrics.items():
        if v is None:
            continue
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.6g}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# A3 — Chat with the leaderboard
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    include_sql: bool = True


class ChatResponse(BaseModel):
    text: str
    sql: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_llm_db),
):
    """A3 — Multi-turn chat with optional <sql>...</sql> tool use."""
    await _ensure_ollama_up()

    schema = get_schema_ddl(db)
    system = A3_SYSTEM + "\n\nSchema:\n" + schema

    # Build the message list. Drop any client-provided system messages —
    # the system prompt always wins.
    msgs: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for m in body.messages:
        if m.role in ("user", "assistant"):
            msgs.append({"role": m.role, "content": m.content})

    if not msgs[-1]["role"] == "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    # First LLM call
    try:
        first = await complete(messages=msgs, max_tokens=600, temperature=0.4)
    except Exception as exc:
        logger.error(f"A3: first Ollama call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    # Look for a <sql>...</sql> tool-use tag
    sql_match = re.search(r"<sql>(.*?)</sql>", first, re.DOTALL | re.IGNORECASE)
    if not sql_match or not body.include_sql:
        # No tool use — return the response as-is.
        return ChatResponse(text=first.strip())

    candidate = sql_match.group(1).strip()
    try:
        safe_sql = validate_and_rewrite(candidate)
    except SqlSafetyError as exc:
        # Send a follow-up turn telling the model the validator rejected it.
        # The A3 system prompt instructs the model to NOT retry — just
        # explain to the user what it was trying.
        msgs.append({"role": "assistant", "content": first})
        msgs.append({
            "role": "user",
            "content": (
                f"<rejection>The SQL was rejected by the safety validator: {exc}. "
                f"Please explain to me what you were trying to look up.</rejection>"
            ),
        })
        try:
            recovery = await complete(messages=msgs, max_tokens=400, temperature=0.4)
        except Exception:
            recovery = (
                "I tried to look that up but the safety validator rejected my query. "
                "Could you rephrase the question?"
            )
        return ChatResponse(text=recovery.strip())

    # Execute the safe SQL with the same timeout pipeline as A1
    try:
        rows, columns = await asyncio.get_event_loop().run_in_executor(
            None, _run_query_with_timeout, db, safe_sql
        )
    except FutureTimeoutError:
        rows, columns = [], []
        result_text = "Query timed out (>5s)"
    except Exception as exc:
        rows, columns = [], []
        result_text = f"Query failed: {exc}"
    else:
        result_text = _format_rows_for_llm(columns, rows)

    # Second LLM call: ask the model to summarize the result for the user
    msgs.append({"role": "assistant", "content": first})
    msgs.append({
        "role": "user",
        "content": f"<result>\n{result_text}\n</result>\n\nSummarize the result for the user in plain English.",
    })

    try:
        summary = await complete(messages=msgs, max_tokens=500, temperature=0.4)
    except Exception as exc:
        logger.error(f"A3: second Ollama call failed: {exc}")
        summary = result_text  # fallback: just show the raw result

    return ChatResponse(
        text=summary.strip(),
        sql=safe_sql,
        rows=rows[:50],  # cap chat-displayed rows
        columns=columns,
    )


def _format_rows_for_llm(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    """Compact textual table for inclusion in the LLM prompt."""
    if not rows:
        return "(empty result set)"
    head = " | ".join(columns)
    sep = " | ".join("-" * len(c) for c in columns)
    body_lines = []
    for r in rows[:30]:
        body_lines.append(" | ".join(str(r.get(c, "")) for c in columns))
    if len(rows) > 30:
        body_lines.append(f"... ({len(rows) - 30} more rows)")
    return "\n".join([head, sep] + body_lines)


# ─────────────────────────────────────────────────────────────────────────────
# A4 — Submission validator assistant
# ─────────────────────────────────────────────────────────────────────────────

class SuggestFixRequest(BaseModel):
    parsed_json: Any
    errors: List[str]
    hint: Optional[str] = None


class SuggestFixResponse(BaseModel):
    text: str


@router.post("/suggest-fix", response_model=SuggestFixResponse)
async def suggest_fix(
    body: SuggestFixRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """A4 — Given a parsed UCTP file + validation errors, suggest a fix."""
    await _ensure_ollama_up()

    # Truncate the JSON to keep the prompt small
    import json as json_module
    try:
        full = json_module.dumps(body.parsed_json, indent=2, default=str)
    except Exception:
        full = str(body.parsed_json)
    truncated_lines = full.splitlines()[:200]
    truncated = "\n".join(truncated_lines)
    if len(full.splitlines()) > 200:
        truncated += "\n... (file truncated to first 200 lines for context)"

    user_msg = (
        f"Uploaded file (first 200 lines):\n```json\n{truncated}\n```\n\n"
        f"Validation errors:\n"
        + "\n".join(f"  - {e}" for e in body.errors)
        + (f"\n\nValidator hint: {body.hint}" if body.hint else "")
    )

    try:
        text = await complete(
            messages=[
                {"role": "system", "content": A4_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error(f"A4: Ollama call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    return SuggestFixResponse(text=text.strip())
