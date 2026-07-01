"""Fixtures pour les tests d'intégration : vrai TimescaleDB dans un conteneur.

Ces tests sont marqués ``@pytest.mark.integration`` et ne tournent qu'en CI
ou quand on les demande explicitement :

    pytest -m integration
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

try:
    from testcontainers.postgres import PostgresContainer
except ImportError:                       # pragma: no cover
    PostgresContainer = None               # type: ignore[assignment]

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "sql" / "timescale"


@pytest.fixture(scope="session")
def timescale_container():
    if PostgresContainer is None:
        pytest.skip("testcontainers not installed")
    # timescale/timescaledb-ha embarque Postgres + l'extension Timescale.
    with PostgresContainer("timescale/timescaledb:2.17.2-pg16",
                           username="vigistock",
                           password="vigistock",
                           dbname="vigistock") as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_dsn(timescale_container) -> str:
    host = timescale_container.get_container_host_ip()
    port = timescale_container.get_exposed_port(5432)
    return f"host={host} port={port} dbname=vigistock user=vigistock password=vigistock"


@pytest.fixture(scope="session", autouse=True)
def _apply_schema(pg_dsn, timescale_container):
    """Applique les fichiers SQL par ordre alphabétique. Le schéma est partagé entre les tests.

    Les statements sont exécutés un par un via le même découpage que
    scripts/apply_schema.py : exécuter un fichier entier en un seul execute()
    enveloppe le tout dans une transaction implicite, ce que la création
    d'un agrégat continu TimescaleDB refuse. C'était la cause de l'échec
    en bloc de la suite d'intégration.
    """
    from scripts.apply_schema import _statements

    os.environ["TIMESCALE_HOST"] = timescale_container.get_container_host_ip()
    os.environ["TIMESCALE_PORT"] = str(timescale_container.get_exposed_port(5432))
    os.environ["TIMESCALE_DB"] = "vigistock"
    os.environ["TIMESCALE_USER"] = "vigistock"
    os.environ["TIMESCALE_PASSWORD"] = "vigistock"

    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
            for stmt in _statements(sql_file.read_text()):
                conn.execute(stmt)
    yield
