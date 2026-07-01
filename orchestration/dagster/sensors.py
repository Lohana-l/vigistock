"""Capteurs : rematérialisation pilotée par événements."""
from dagster import (
    AssetSelection,
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    define_asset_job,
    sensor,
)

from ingestion.utils.db import pg_conn

alert_cascade_job = define_asset_job(
    name="alert_cascade_forecast",
    selection=AssetSelection.keys("shortage_forecasts"),
)


@sensor(
    job=alert_cascade_job,
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Surveille silver.alerts pour les nouvelles lignes BREAKAGE_RISK / CRITICAL. "
        "À chaque apparition, déclenche une rematérialisation de shortage_forecasts "
        "pour que le dashboard reflète l'impact en moins d'une minute."
    ),
)
def alert_to_forecast_sensor(context: SensorEvaluationContext):
    last = context.cursor or "1970-01-01"
    sql = """
        SELECT MAX(opened_at)::TEXT
        FROM silver.alerts
        WHERE severity IN ('BREAKAGE_RISK', 'CRITICAL')
          AND opened_at > %s::timestamptz
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (last,))
        row = cur.fetchone()
    latest = row[0] if row and row[0] else None

    if latest and latest > last:
        context.update_cursor(latest)
        yield RunRequest(run_key=f"alert-{latest}", tags={"trigger": "cold-chain-alert"})
