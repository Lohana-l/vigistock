"""Test d'intégration : applique le schéma et vérifie les invariants clés."""
from __future__ import annotations

import psycopg
import pytest

pytestmark = pytest.mark.integration


def test_extensions_enabled(pg_dsn):
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname='timescaledb'")
        assert cur.fetchone() is not None


def test_schemas_exist(pg_dsn):
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name IN ('bronze','silver','gold')"
        )
        names = {r[0] for r in cur.fetchall()}
    assert names == {"bronze", "silver", "gold"}


def test_telemetry_is_hypertable(pg_dsn):
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT hypertable_name FROM timescaledb_information.hypertables "
            "WHERE hypertable_schema='silver'"
        )
        names = {r[0] for r in cur.fetchall()}
    assert "telemetry_raw" in names
    assert "alerts" in names


def test_gold_views_compile(pg_dsn):
    """Les trois vues gold doivent être interrogeables, même sur des tables vides."""
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        for view in ("v_stock_current", "v_alerts_active", "v_forecast_latest"):
            cur.execute(f"SELECT * FROM gold.{view} LIMIT 1")
            cur.fetchall()  # pas encore de lignes, mais la vue doit être du SQL valide
