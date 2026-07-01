"""Smoke test d'intégration : le chemin d'écriture du consumer contre un vrai
TimescaleDB.

On ne monte pas Kafka ici (ça c'est dans le Docker Compose pour le e2e complet).
On exerce directement write_telemetry / upsert_alert avec des événements de la
MÊME forme que ceux produits par le simulateur et le détecteur d'anomalies :
si le schéma SQL ou le contrat d'événement dérive, ce test casse en premier.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

pytestmark = pytest.mark.integration


def _insert_fridge(cur, site_id: str, fridge_id: str) -> None:
    # Colonnes alignées sur sql/timescale/03_silver.sql : c'est le schéma réel
    # qui fait foi, pas une variante locale au test.
    cur.execute(
        "INSERT INTO silver.dim_sites (site_id, site_name, country, region) "
        "VALUES (%s, 'Site de test', 'FR', 'Île-de-France') "
        "ON CONFLICT (site_id) DO NOTHING",
        (site_id,),
    )
    cur.execute(
        "INSERT INTO silver.dim_fridges "
        "  (fridge_id, site_id, model, target_low_c, target_high_c) "
        "VALUES (%s, %s, 'Liebherr MKv 3910', 2.0, 8.0) "
        "ON CONFLICT (fridge_id) DO NOTHING",
        (fridge_id, site_id),
    )


def test_write_telemetry_and_alert_roundtrip(pg_dsn):
    from streaming.consumer import _alert_id, upsert_alert, write_telemetry

    ts = datetime.now(tz=UTC)
    site_id, fridge_id = "SITE-90", "SITE-90-F00"

    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        _insert_fridge(cur, site_id, fridge_id)
        conn.commit()

    # Événements de la même forme que simulator.fleet.tick().
    telemetry = [
        {
            "event_ts":      (ts - timedelta(seconds=i * 10)).isoformat(),
            "fridge_id":     fridge_id,
            "site_id":       site_id,
            "temperature_c": 9.5 + i * 0.01,
            "humidity_pct":  55.0,
            "door_open":     False,
        }
        for i in range(60)
    ]
    write_telemetry(telemetry)

    # Alerte de la même forme que celle émise par streaming.anomaly.
    alert = {
        "opened_at":    ts,
        "closed_at":    None,
        "site_id":      site_id,
        "fridge_id":    fridge_id,
        "severity":     "BREAKAGE_RISK",
        "peak_temp_c":  9.8,
        "duration_sec": 720,
    }
    upsert_alert(alert)
    # Deuxième appel avec sévérité escaladée : doit faire un UPDATE,
    # pas un INSERT dupliqué (clé fonctionnelle fridge_id + opened_at).
    alert["severity"] = "CRITICAL"
    alert["peak_temp_c"] = 11.2
    upsert_alert(alert)

    expected_id = _alert_id(alert)
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM silver.telemetry_raw WHERE fridge_id = %s",
            (fridge_id,),
        )
        (n_t,) = cur.fetchone()
        cur.execute(
            "SELECT severity, peak_temp_c::float FROM silver.alerts "
            "WHERE alert_id = %s",
            (expected_id,),
        )
        rows = cur.fetchall()

    assert n_t >= 60
    assert len(rows) == 1, "l'upsert doit converger vers une seule ligne d'alerte"
    severity, peak = rows[0]
    assert severity == "CRITICAL"
    assert peak == pytest.approx(11.2), "peak_temp_c doit garder le maximum observé"


def test_alert_visible_in_gold_view(pg_dsn):
    """La vue gold.v_alerts_active doit exposer l'alerte jointe à ses dimensions :
    c'est elle que lit le dashboard (live_data.recent_alerts)."""
    with psycopg.connect(pg_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT site_name, fridge_id, severity FROM gold.v_alerts_active "
            "WHERE fridge_id = 'SITE-90-F00'"
        )
        rows = cur.fetchall()
    assert rows, "l'alerte doit être visible via la vue gold (JOIN dims inclus)"
    assert rows[0][0] == "Site de test"
