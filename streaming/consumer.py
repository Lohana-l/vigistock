"""
Consumer streaming Redpanda vers TimescaleDB.

Responsabilités :
  • consommer les messages `coldchain.telemetry` (sémantique at-least-once)
  • écrire chaque échantillon dans silver.telemetry_raw (upsert idempotent)
  • lancer le détecteur d'anomalies
  • ouvrir / escalader / fermer les lignes dans silver.alerts
  • marquer les lots d'inventaire comme `suspect` si sévérité >= BREAKAGE_RISK
  • produire un message miroir sur `coldchain.alerts` pour que Grafana /
    les consommateurs downstream puissent s'abonner sans interroger Postgres
"""
from __future__ import annotations

import json
import signal
import sys
import uuid

from confluent_kafka import Consumer, Producer
from loguru import logger

from ingestion.config import settings
from ingestion.utils.db import pg_conn
from streaming.anomaly import AnomalyDetector

BATCH_SIZE = 100
POLL_TIMEOUT_SEC = 1.0


def _build_consumer() -> Consumer:
    cfg = settings()
    return Consumer({
        "bootstrap.servers":   cfg.redpanda_brokers,
        "group.id":             "vigistock-consumer",
        "auto.offset.reset":    "earliest",
        "enable.auto.commit":   False,
    })


def _build_producer() -> Producer:
    cfg = settings()
    return Producer({
        "bootstrap.servers":   cfg.redpanda_brokers,
        "client.id":            "vigistock-consumer-alerts",
        "enable.idempotence":   True,
    })


# ---------------------------------------------------------------------------
# Écritures Postgres
# ---------------------------------------------------------------------------
def write_telemetry(events: list[dict]) -> None:
    if not events:
        return
    rows = [
        (
            e["event_ts"],
            e["fridge_id"],
            e["site_id"],
            e["temperature_c"],
            e.get("humidity_pct"),
            e.get("door_open", False),
        )
        for e in events
    ]
    sql = """
        INSERT INTO silver.telemetry_raw
          (event_ts, fridge_id, site_id, temperature_c, humidity_pct, door_open)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)


def upsert_alert(alert: dict) -> None:
    """Upsert idempotent, clé sur (fridge_id, opened_at)."""
    alert_id = _alert_id(alert)
    sql = """
        INSERT INTO silver.alerts
          (alert_id, opened_at, closed_at, site_id, fridge_id,
           severity, peak_temp_c, duration_sec)
        VALUES (%(id)s, %(opened)s, %(closed)s, %(site)s, %(fridge)s,
                %(sev)s,  %(peak)s, %(dur)s)
        ON CONFLICT (alert_id, opened_at) DO UPDATE SET
            closed_at    = EXCLUDED.closed_at,
            severity     = EXCLUDED.severity,
            peak_temp_c  = GREATEST(silver.alerts.peak_temp_c, EXCLUDED.peak_temp_c),
            duration_sec = EXCLUDED.duration_sec
    """
    params = {
        "id":     alert_id,
        "opened": alert["opened_at"],
        "closed": alert.get("closed_at"),
        "site":   alert["site_id"],
        "fridge": alert["fridge_id"],
        "sev":    alert["severity"],
        "peak":   alert["peak_temp_c"],
        "dur":    alert["duration_sec"],
    }
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)


def mark_lots_suspect(fridge_id: str, opened_at: str, reason: str) -> int:
    """Marque comme suspects les lots d'inventaire stockés dans le frigo défaillant."""
    sql = """
        UPDATE silver.inventory_lots
        SET suspect        = TRUE,
            suspect_reason = %s,
            suspect_at     = %s
        WHERE fridge_id = %s
          AND suspect = FALSE
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (reason, opened_at, fridge_id))
        return cur.rowcount


def _alert_id(alert: dict) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL,
                          f"{alert['fridge_id']}|{alert['opened_at']}"))


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------
def run() -> None:
    cfg = settings()
    consumer = _build_consumer()
    producer = _build_producer()
    detector = AnomalyDetector()

    consumer.subscribe([cfg.redpanda_topic_telemetry])

    stop = False
    def _sig(_a, _b): nonlocal stop; stop = True
    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    batch: list[dict] = []
    logger.info(f"consumer started, subscribed to {cfg.redpanda_topic_telemetry}")

    while not stop:
        msg = consumer.poll(POLL_TIMEOUT_SEC)
        if msg is None:
            if batch:
                _flush(batch, consumer, producer, detector)
                batch = []
            continue
        if msg.error():
            logger.error(f"kafka error: {msg.error()}")
            continue

        try:
            event = json.loads(msg.value().decode())
        except Exception:
            logger.exception("invalid JSON payload, skipping")
            continue

        batch.append(event)
        if len(batch) >= BATCH_SIZE:
            _flush(batch, consumer, producer, detector)
            batch = []

    if batch:
        _flush(batch, consumer, producer, detector)
    consumer.close()
    logger.info("consumer stopped cleanly")


def _flush(batch: list[dict], consumer: Consumer, producer: Producer,
           detector: AnomalyDetector) -> None:
    cfg = settings()
    # 1. dépose la télémétrie brute
    write_telemetry(batch)
    # 2. lance la détection d'anomalie et traite chaque alerte déclenchée
    for event in batch:
        alert = detector.process(event)
        if alert is None:
            continue
        upsert_alert(alert)
        producer.produce(
            topic=cfg.redpanda_topic_alerts,
            key=alert["fridge_id"].encode(),
            value=json.dumps(alert).encode(),
        )
        if alert["severity"] in ("BREAKAGE_RISK", "CRITICAL"):
            n = mark_lots_suspect(
                alert["fridge_id"], alert["opened_at"],
                f"{alert['severity']} - {alert['duration_sec']}s "
                f"above {alert['peak_temp_c']}°C",
            )
            if n:
                logger.warning(f"alert {alert['severity']} on {alert['fridge_id']}: "
                               f"flagged {n} inventory lots as suspect")
    producer.poll(0)
    consumer.commit(asynchronous=False)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
