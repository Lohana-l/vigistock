"""Helpers Postgres / Timescale utilisés par tous les extracteurs."""
from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any

import psycopg
from loguru import logger
from psycopg import sql as pgsql

from ingestion.config import settings

# Liste blanche des tables bronze : un nom de table ne se paramètre pas en SQL,
# on refuse donc tout identifiant inattendu plutôt que d'interpoler à l'aveugle.
_BRONZE_TABLES = frozenset({
    "fda_shortages",
    "openfda_labels",
    "ansm_signalements",
    "openprescribing_usage",
})


@contextmanager
def pg_conn():
    """Connexion psycopg gérée par contexte, avec autocommit."""
    with psycopg.connect(settings().pg_dsn, autocommit=True) as conn:
        yield conn


def upsert_bronze(table: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert des lignes dans bronze.<table> avec (source_row_id, payload).

    Idempotent : relancer l'extracteur ne crée jamais de doublon.
    Retourne le nombre de lignes effectivement écrites (insertion OU mise à jour).
    Le nom de table est validé contre la liste blanche puis composé via
    psycopg.sql.Identifier : aucune interpolation brute dans le SQL.
    """
    table = table.removeprefix("bronze.")
    if table not in _BRONZE_TABLES:
        raise ValueError(
            f"table bronze inconnue : {table!r} (attendu : {sorted(_BRONZE_TABLES)})"
        )

    rows = list(rows)
    if not rows:
        logger.info(f"{table}: nothing to write")
        return 0

    query = pgsql.SQL("""
        INSERT INTO {} (source_row_id, payload)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (source_row_id) DO UPDATE
            SET payload      = EXCLUDED.payload,
                ingested_at  = NOW()
    """).format(pgsql.Identifier("bronze", table))
    with pg_conn() as conn, conn.cursor() as cur:
        cur.executemany(query, [(r["source_row_id"], json.dumps(r["payload"])) for r in rows])
    logger.success(f"{table}: upserted {len(rows)} rows")
    return len(rows)
