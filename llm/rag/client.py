"""Wrapper Ollama minimaliste : complétion en mode JSON."""
from __future__ import annotations

import json
from typing import Any

import ollama
from loguru import logger

from ingestion.config import settings


def _client() -> ollama.Client:
    return ollama.Client(host=settings().ollama_host)


def generate_json(prompt: str, *, model: str | None = None) -> dict[str, Any]:
    """Appelle Ollama en mode JSON et retourne l'objet parsé."""
    cfg = settings()
    model = model or cfg.ollama_model
    resp = _client().chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": cfg.ollama_temperature, "num_ctx": 8192},
    )
    raw = resp["message"]["content"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(f"LLM returned invalid JSON: {exc}; raw={raw[:300]!r}")
        return {"insufficient_context": True, "raw": raw}
