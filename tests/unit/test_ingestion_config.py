"""Tests unitaires pour la config d'ingestion et le helper DSN."""
from __future__ import annotations

import importlib


def test_pg_dsn_is_a_postgres_url(monkeypatch):
    monkeypatch.setenv("TIMESCALE_HOST", "timescaledb")
    monkeypatch.setenv("TIMESCALE_PORT", "5432")
    monkeypatch.setenv("TIMESCALE_DB", "vigistock")
    monkeypatch.setenv("TIMESCALE_USER", "vigistock")
    monkeypatch.setenv("TIMESCALE_PASSWORD", "secret")

    import ingestion.config as config
    config.settings.cache_clear()
    importlib.reload(config)

    s = config.settings()
    dsn = s.pg_dsn
    assert dsn.startswith("postgresql://")
    assert "vigistock:secret@timescaledb:5432/vigistock" in dsn


def test_settings_is_cached():
    import ingestion.config as config
    config.settings.cache_clear()
    a = config.settings()
    b = config.settings()
    assert a is b


def test_all_urls_have_sensible_defaults():
    import ingestion.config as config
    config.settings.cache_clear()
    s = config.settings()
    assert s.fda_shortages_url.startswith("https://")
    assert s.openfda_url.startswith("https://")
    assert s.openprescribing_url.startswith("https://")
    assert s.ansm_rss_url          # http ou https, au minimum non vide


def test_topic_names_are_namespaced():
    """Les topics Kafka doivent tous vivre sous le préfixe ``coldchain.``."""
    import ingestion.config as config
    config.settings.cache_clear()
    s = config.settings()
    assert s.redpanda_topic_telemetry.startswith("coldchain.")
    assert s.redpanda_topic_alerts.startswith("coldchain.")
