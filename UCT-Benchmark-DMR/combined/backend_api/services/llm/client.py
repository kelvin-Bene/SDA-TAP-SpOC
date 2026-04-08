"""
Hand-rolled async client for an in-cluster Ollama service.

Why not the `ollama` Python package? It pulls in extra deps and we only need
~5 functions. This module is ~80 lines and depends only on `httpx`, which is
already in the local-dgx extras group.

Configuration via env:
    OLLAMA_URL    — base URL of the Ollama HTTP API. Defaults to
                    http://ollama:11434 (the docker compose service name).
    OLLAMA_MODEL  — model tag to use, e.g. "qwen3.5:35b". Defaults to
                    "qwen3.5:35b" (the Phase 2 default).
    OLLAMA_TIMEOUT — request timeout in seconds. Defaults to 120.

Usage:
    from backend_api.services.llm import complete
    text = await complete([
        {"role": "system", "content": "You are a SQL expert."},
        {"role": "user", "content": "Count the satellites."},
    ])
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3.5:35b")


def _ollama_timeout() -> float:
    try:
        return float(os.getenv("OLLAMA_TIMEOUT", "120"))
    except ValueError:
        return 120.0


class OllamaClient:
    """Stateless client. Construct per-request or share a singleton."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or _ollama_url()).rstrip("/")
        self.model = model or _ollama_model()
        self.timeout = timeout if timeout is not None else _ollama_timeout()

    async def health(self) -> bool:
        """Return True if the Ollama service answers GET /api/tags within 5s."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as ac:
                r = await ac.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception as exc:
            logger.debug(f"Ollama health check failed: {exc}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        max_tokens: Optional[int] = None,
        temperature: float = 0.1,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        Call the Ollama /api/chat endpoint and return the assistant message
        text. Non-streaming — full response is buffered before returning.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = int(max_tokens)
        if stop:
            payload["options"]["stop"] = stop

        async with httpx.AsyncClient(timeout=self.timeout) as ac:
            r = await ac.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        # Ollama returns {message: {role, content}, done: true, ...}
        message = data.get("message", {}) or {}
        content = message.get("content", "") or ""
        return content


async def complete(
    messages: List[Dict[str, str]],
    *,
    max_tokens: Optional[int] = None,
    temperature: float = 0.1,
    stop: Optional[List[str]] = None,
) -> str:
    """Module-level helper that constructs a default client per call.

    Acceptable because httpx clients are cheap and we don't need pooling for
    the demo workload (~1 req/sec sustained at most).
    """
    client = OllamaClient()
    return await client.chat(
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=stop,
    )
