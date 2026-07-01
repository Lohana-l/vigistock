"""Test d'intégration : l'upsert bronze est idempotent et de forme stable."""
from __future__ import annotations

import psycopg
import pytest

pytestmark = pytest.mark.integration


def test_upsert_bronze_idempotent(pg_dsn, monkeypatch):
    monkeypatch.setenv("TIMESCALE_HOST", pg_dsn.split("host=", 1)[1].split(" ", 1)[0])
    from ingestion.utils.db import upsert_bronze

    rows = [
        {"source_row_id": "abc", "payload": {"generic_name": "insulin"}},
        {"source_row_id": "def", "payload": {"generic_name": "oseltamivir"}},
    ]
    upsert_bronze("fda_shortages", rows)
    upsert_bronze("fda_shortages", rows)  # le deuxième appel doit être un no-op

    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bronze.fda_shortages")
        (n,) = cur.fetchone()
    assert n == 2


def test_upsert_bronze_updates_payload_on_conflict(pg_dsn, monkeypatch):
    monkeypatch.setenv("TIMESCALE_HOST", pg_dsn.split("host=", 1)[1].split(" ", 1)[0])
    from ingestion.utils.db import upsert_bronze

    upsert_bronze("fda_shortages",
                  [{"source_row_id": "ghi", "payload": {"status": "current"}}])
    upsert_bronze("fda_shortages",
                  [{"source_row_id": "ghi", "payload": {"status": "resolved"}}])

    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT payload->>'status' FROM bronze.fda_shortages WHERE source_row_id='ghi'"
        )
        (status,) = cur.fetchone()
    assert status == "resolved"
