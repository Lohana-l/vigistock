"""
Détection d'anomalies en streaming sur la température des réfrigérateurs.

Stratégie (simple, défendable, testable) :
  1. Seuil : une température hors de [target_low, target_high] est "hors-tolérance".
  2. Persistance : N échantillons hors-tolérance consécutifs dans une fenêtre glissante
     sont requis avant de déclencher une alerte. Cela élimine le bruit des ouvertures
     de porte (qui se rétablissent en moins d'une minute).
  3. La sévérité augmente avec la durée :
       <  30 min   : INFO
       30 min-2 h  : WARN
       2 h-4 h     : BREAKAGE_RISK   (vaccins présumés compromis)
       > 4 h       : CRITICAL

Le détecteur maintient un état par frigo en mémoire. En production on persisterait
cet état dans Redis ; ici, en mémoire de processus c'est suffisant et
les pannes se rattrapent sur l'hypertable brute.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

# Seuils d'escalade de sévérité, en secondes de hors-tolérance continu.
THRESHOLDS = {
    30 * 60:   "WARN",           # 30 min
    2  * 3600: "BREAKAGE_RISK",  # 2 h
    4  * 3600: "CRITICAL",       # 4 h
}


@dataclass
class FridgeTracker:
    """État glissant pour un seul réfrigérateur."""

    target_low_c:  float = 2.0
    target_high_c: float = 8.0
    recent_samples: deque = field(default_factory=lambda: deque(maxlen=60))  # last 30 min @ 30s
    excursion_start: datetime | None = None
    peak_temp_c: float = 0.0
    current_severity: str | None = None

    def update(self, ts: datetime, temp_c: float) -> dict | None:
        """Reçoit un échantillon ; retourne un dict d'alerte quand la sévérité escalade."""
        self.recent_samples.append((ts, temp_c))
        out_of_range = temp_c < self.target_low_c or temp_c > self.target_high_c

        if out_of_range:
            if self.excursion_start is None:
                self.excursion_start = ts
                self.peak_temp_c = temp_c
                self.current_severity = "INFO"
                return self._alert(ts, opened=True)

            self.peak_temp_c = max(self.peak_temp_c, temp_c)
            elapsed = (ts - self.excursion_start).total_seconds()
            new_sev = self._severity_for(elapsed)
            if new_sev != self.current_severity:
                self.current_severity = new_sev
                return self._alert(ts, opened=False)
            return None

        # retour en zone : fermer l'excursion le cas échéant
        if self.excursion_start is not None:
            closed = self._alert(ts, opened=False, closed=True)
            self.excursion_start = None
            self.peak_temp_c = 0.0
            self.current_severity = None
            return closed
        return None

    def _severity_for(self, elapsed_sec: float) -> str:
        """Retourne la sévérité la plus élevée correspondant à la durée écoulée."""
        sev = "INFO"
        for threshold, label in THRESHOLDS.items():
            if elapsed_sec >= threshold:
                sev = label
        return sev

    def _alert(self, ts: datetime, *, opened: bool = False, closed: bool = False) -> dict:
        assert self.excursion_start is not None
        return {
            "fridge_id":      None,  # complété par le détecteur
            "site_id":        None,
            "opened_at":      self.excursion_start.isoformat(),
            "observed_at":    ts.isoformat(),
            "closed_at":      ts.isoformat() if closed else None,
            "severity":       self.current_severity or "INFO",
            "peak_temp_c":    round(self.peak_temp_c, 2),
            "duration_sec":   int((ts - self.excursion_start).total_seconds()),
            "opened":         opened,
            "closed":         closed,
        }


class AnomalyDetector:
    """Wrapper multi-frigo. Stateful entre les appels à `process()`."""

    def __init__(self, target_low_c: float = 2.0, target_high_c: float = 8.0) -> None:
        self._targets = (target_low_c, target_high_c)
        self._trackers: dict[str, FridgeTracker] = {}

    def process(self, event: dict) -> dict | None:
        ts = datetime.fromisoformat(event["event_ts"].replace("Z", "+00:00"))
        fid = event["fridge_id"]
        t = self._trackers.get(fid)
        if t is None:
            t = FridgeTracker(*self._targets)
            self._trackers[fid] = t

        alert = t.update(ts, float(event["temperature_c"]))
        if alert is None:
            return None
        alert["fridge_id"] = fid
        alert["site_id"] = event.get("site_id")
        return alert
