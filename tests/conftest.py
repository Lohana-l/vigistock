"""Fixtures pytest partagées.

On garde les fixtures des tests unitaires légères (pas de Docker). Les tests
d'intégration ont leur propre conteneur TimescaleDB à portée module via
testcontainers.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Garantit que settings() se résout même quand l'hôte n'a pas de fichier .env."""
    monkeypatch.setenv("TIMESCALE_HOST", os.getenv("TIMESCALE_HOST", "localhost"))
    monkeypatch.setenv("TIMESCALE_PORT", os.getenv("TIMESCALE_PORT", "5432"))
    monkeypatch.setenv("TIMESCALE_DB", os.getenv("TIMESCALE_DB", "vigistock"))
    monkeypatch.setenv("TIMESCALE_USER", os.getenv("TIMESCALE_USER", "vigistock"))
    monkeypatch.setenv("TIMESCALE_PASSWORD", os.getenv("TIMESCALE_PASSWORD", "vigistock"))
    monkeypatch.setenv("REDPANDA_BROKERS", os.getenv("REDPANDA_BROKERS", "localhost:9092"))
    monkeypatch.setenv("OLLAMA_HOST", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    monkeypatch.setenv("OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "phi3:mini"))
    monkeypatch.setenv("CHROMA_HOST", os.getenv("CHROMA_HOST", "localhost"))
    monkeypatch.setenv("CHROMA_PORT", os.getenv("CHROMA_PORT", "8000"))
    yield
