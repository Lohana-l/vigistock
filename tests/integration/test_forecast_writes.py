"""Test d'intégration : la prévision Prophet écrit au moins une ligne par paire amorcée.

Le seed reproduit en miniature ce que fait scripts/seed_dimensions.py :
dimensions, un lot d'inventaire actif (c'est lui qui inscrit la paire dans le
plan de prévision) et 180 jours d'historique dans silver.dispensing_daily,
la table réellement lue par ml/features.load_history.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import psycopg
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_SITE = "SITE-91"
_DRUG = "J05AH02"


def _seed(cur) -> None:
    cur.execute(
        "INSERT INTO silver.dim_sites (site_id, site_name, country, region) "
        "VALUES (%s, 'Site de test prévision', 'FR', 'Île-de-France') "
        "ON CONFLICT (site_id) DO NOTHING",
        (_SITE,),
    )
    cur.execute(
        "INSERT INTO silver.dim_drugs (drug_id, generic_name, therapeutic_cat, cold_chain) "
        "VALUES (%s, 'Oseltamivir 75mg', 'Antiviral', TRUE) "
        "ON CONFLICT (drug_id) DO NOTHING",
        (_DRUG,),
    )
    # Le plan de prévision (_pairs_to_forecast) part des lots actifs :
    # sans lot, la paire n'est jamais visitée.
    now = datetime.now(UTC)
    cur.execute(
        "INSERT INTO silver.inventory_lots "
        "  (lot_id, drug_id, site_id, doses, received_at, expires_at) "
        "VALUES ('LOT-TEST-FCST', %s, %s, 400, %s, %s) "
        "ON CONFLICT (lot_id) DO NOTHING",
        (_DRUG, _SITE, now - timedelta(days=10), now + timedelta(days=365)),
    )
    # 180 jours de dispensation quotidienne synthétique avec cycle hebdomadaire.
    start = date.today() - timedelta(days=180)
    for i in range(180):
        d = start + timedelta(days=i)
        cur.execute(
            "INSERT INTO silver.dispensing_daily "
            "  (observed_at, site_id, drug_id, dispensed_doses) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (site_id, drug_id, observed_at) DO NOTHING",
            (datetime.combine(d, time(12, 0), tzinfo=UTC),
             _SITE, _DRUG, 12 + (i % 7)),
        )


def test_run_forecast_writes_rows(pg_dsn):
    with psycopg.connect(pg_dsn, autocommit=True) as conn, conn.cursor() as cur:
        _seed(cur)

    from ml.shortage_forecast import run as run_forecast
    n = run_forecast()
    assert n > 0, "Prophet doit écrire au moins une ligne de prévision"

    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        # 1 ligne résumé par run dans silver.forecasts
        cur.execute(
            "SELECT COUNT(*) FROM silver.forecasts "
            "WHERE drug_id = %s AND site_id = %s "
            "  AND forecast_ts > NOW() - INTERVAL '5 minutes'",
            (_DRUG, _SITE),
        )
        (n_summary,) = cur.fetchone()
        # 1 point par jour d'horizon dans gold.forecast_points (la vraie courbe)
        cur.execute(
            "SELECT COUNT(*) FROM gold.forecast_points "
            "WHERE drug_id = %s AND site_id = %s "
            "  AND forecast_ts > NOW() - INTERVAL '5 minutes'",
            (_DRUG, _SITE),
        )
        (n_points,) = cur.fetchone()
    assert n_summary >= 1, "une ligne résumé par run"
    assert n_points >= 30, "un point par jour d'horizon (30 j)"
