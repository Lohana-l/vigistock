"""Tests unitaires pour le détecteur d'anomalie streaming.

Le détecteur est une fonction pure sur l'historique récent d'un frigo,
ce qui permet de tester l'échelle d'escalade de sévérité sans Kafka ni
Timescale.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from streaming.anomaly import AnomalyDetector, FridgeTracker


@pytest.fixture
def tracker() -> FridgeTracker:
    return FridgeTracker(target_low_c=2.0, target_high_c=8.0)


def _feed(tracker: FridgeTracker, temps: list[float],
          start: datetime | None = None, step_seconds: int = 60) -> list[dict]:
    ts = start or datetime(2026, 4, 1, 4, 0, 0, tzinfo=UTC)
    out: list[dict] = []
    for t in temps:
        alert = tracker.update(ts, t)
        if alert is not None:
            out.append(alert)
        ts += timedelta(seconds=step_seconds)
    return out


def test_in_range_never_alerts(tracker: FridgeTracker):
    alerts = _feed(tracker, [4.0, 4.2, 3.8, 4.1, 4.3] * 10)
    assert alerts == []


def test_short_excursion_stays_warn(tracker: FridgeTracker):
    # 10 minutes légèrement au-dessus : ouverture (INFO) sans atteindre WARN
    alerts = _feed(tracker, [9.0] * 10, step_seconds=60)
    # la première alerte est le marqueur d'ouverture d'excursion
    assert alerts[0]["opened"] is True
    assert alerts[0]["severity"] == "INFO"
    severities = {a["severity"] for a in alerts}
    assert "BREAKAGE_RISK" not in severities
    assert "CRITICAL" not in severities


def test_two_hour_excursion_is_breakage_risk(tracker: FridgeTracker):
    # 130 minutes au-dessus de la plage : doit escalader à BREAKAGE_RISK
    alerts = _feed(tracker, [9.5] * 130, step_seconds=60)
    final = alerts[-1]
    assert final["severity"] == "BREAKAGE_RISK"


def test_four_hour_excursion_is_critical(tracker: FridgeTracker):
    alerts = _feed(tracker, [10.0] * 250, step_seconds=60)
    final = alerts[-1]
    assert final["severity"] == "CRITICAL"


def test_recovery_closes_the_excursion(tracker: FridgeTracker):
    _feed(tracker, [9.5] * 45)
    after = _feed(
        tracker, [4.0] * 5,
        start=datetime(2026, 4, 1, 5, 0, 0, tzinfo=UTC),
    )
    # Retour en zone doit émettre exactement une alerte "fermée"
    closed_events = [a for a in after if a["closed"]]
    assert len(closed_events) == 1


def test_multi_fridge_detector_isolates_state():
    det = AnomalyDetector(target_low_c=2.0, target_high_c=8.0)
    ts = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
    last_a = last_b = None
    for _ in range(200):
        ev_a = {"fridge_id": "A", "event_ts": ts.isoformat(),
                "temperature_c": 9.5, "site_id": "S-1"}
        ev_b = {"fridge_id": "B", "event_ts": ts.isoformat(),
                "temperature_c": 4.0, "site_id": "S-1"}
        r_a = det.process(ev_a)
        r_b = det.process(ev_b)
        last_a = r_a if r_a is not None else last_a
        last_b = r_b if r_b is not None else last_b
        ts += timedelta(seconds=60)
    # A doit avoir des alertes ; B ne doit rien avoir
    assert last_a is not None
    assert last_a["severity"] in {"WARN", "BREAKAGE_RISK", "CRITICAL"}
    assert last_b is None
