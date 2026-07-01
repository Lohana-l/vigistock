"""Jeu de données mock déterministe qui fait tourner la démo sans stack live.

Le générateur plante une petite histoire de panne cohérente pour que le dashboard
*raconte* quelque chose :

* 6 sites, 24 réfrigérateurs de chaîne du froid.
* 2 frigos en BREAKAGE_RISK (>10 °C), 1 en WARN (8-10 °C).
* 5 médicaments dans la table pénurie, le premier à ~78 % de probabilité de rupture.
* 24 h de télémétrie toutes les 5 min par frigo avec une excursion plantée dans la
  dernière heure du pire frigo, pour que le graphique de détail montre un vrai pic.

Quand la stack live est disponible (``USE_MOCK_DATA=false``), les mêmes callables
sont censés être réimplémentés contre TimescaleDB. Ce module est le contrat
que Streamlit consomme.
"""
from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

_RND = random.Random(42)

# ---------------------------------------------------------------------------
# Données de référence statiques
# ---------------------------------------------------------------------------
SITES = [
    "CHU Lyon-Sud",
    "CHU Lyon-Nord",
    "Hôpital Cochin",
    "CHU Bordeaux Pellegrin",
    "CHU Toulouse Rangueil",
    "Pharmacie Centrale Grenoble",
]

DRUGS: list[tuple[str, str]] = [
    ("Influenza vaccine (inactivated)", "J07BB02"),
    ("Insulin glargine",                "A10AE04"),
    ("Amoxicillin/clavulanate",         "J01CR02"),
    ("MMR vaccine",                     "J07BD52"),
    ("Insulin detemir",                 "A10AE05"),
]


# ---------------------------------------------------------------------------
# Snapshot de la flotte
# ---------------------------------------------------------------------------
def fleet_snapshot() -> list[dict]:
    """Retourne l'état actuel des 24 frigos de la flotte.

    Les pannes sont *plantées* (déterministes) pour que la démo raconte toujours
    la même histoire quelle que soit l'heure d'ouverture de la page.
    """
    rows: list[dict] = []
    for site_idx, site in enumerate(SITES):
        for f in range(1, 5):
            fid = f"F-{site_idx + 1:02d}-{f:02d}"
            temp = 4.5 + _RND.gauss(0, 0.6)
            # pannes plantées
            if (site_idx, f) == (0, 3):  temp = 9.4
            elif (site_idx, f) == (3, 1): temp = 11.2
            elif (site_idx, f) == (1, 2): temp = 8.6
            rows.append({
                "fridge_id": fid,
                "site":      site,
                "temp_c":    round(temp, 1),
                "lots":      _RND.randint(3, 18),
                # Horodatage uniformisé : heure « HH:MM » (jamais de durée mélangée)
                "last_seen": (datetime.now(UTC)
                              - timedelta(seconds=_RND.randint(15, 240)))
                              .strftime("%H:%M"),
                "sparkline": _spark(fid),
            })
    return rows


def _spark(fridge_id: str, n: int = 24) -> list[float]:
    """Courte série temporelle pour le mini-graphe des cartes (dernières ~2 h)."""
    rng = random.Random(hash(fridge_id) & 0xFFFF)
    base = [4.5 + 0.6 * math.sin(i / 6) + rng.gauss(0, 0.2) for i in range(n)]
    if fridge_id == "F-01-03":
        for i in range(n - 6, n):
            base[i] += (i - (n - 6)) * 0.7
    elif fridge_id == "F-04-01":
        for i in range(n - 4, n):
            base[i] += (i - (n - 4)) * 1.0
    return [round(b, 2) for b in base]


def fridge_24h(fridge_id: str = "F-01-03") -> list[dict]:
    """Retourne ``24 × 12 = 288`` points (tranches de 5 min) pour le drill-down."""
    n = 24 * 12
    end = datetime.now(UTC).replace(second=0, microsecond=0)
    rng = random.Random(hash(fridge_id) & 0xFFFF)
    base = [4.5 + 0.6 * math.sin(i / 12) + rng.gauss(0, 0.25) for i in range(n)]
    if fridge_id == "F-01-03":
        for i in range(n - 12, n):
            base[i] += (i - (n - 12)) * 0.4
    elif fridge_id == "F-04-01":
        for i in range(n - 18, n):
            base[i] += (i - (n - 18)) * 0.5
    return [{"ts": (end - timedelta(minutes=5 * (n - i))).isoformat(),
             "temp": round(base[i], 2)} for i in range(n)]


def kpi_snapshot() -> dict:
    fleet = fleet_snapshot()
    crit = sum(1 for f in fleet if f["temp_c"] > 10 or f["temp_c"] < 2)
    warn = sum(1 for f in fleet if 8 < f["temp_c"] <= 10)
    return {
        "open_alerts":     crit + warn,
        "critical_alerts": crit,
        "warn_alerts":     warn,
        "suspect_lots":    7,
        "at_risk_drugs":   4,
        "fridges_total":   len(fleet),
        "sites_total":     len({f["site"] for f in fleet}),
        "uptime_pct":      99.7,
        "events_per_min":  142,
    }


# ---------------------------------------------------------------------------
# Prévisions de rupture (sortie Prophet, simulée)
# ---------------------------------------------------------------------------
def shortage_overview() -> list[dict]:
    today = datetime.now(UTC).date()
    return [
        {"drug_name": "Influenza vaccine (inactivated)", "atc_code": "J07BB02",
         "site_id": "CHU Lyon-Sud", "current_stock": 640,
         "stockout_date": (today + timedelta(days=11)).isoformat(),
         "horizon_days": 14, "shortage_prob": 0.78,
         "daily_demand_mean": 58.0, "daily_demand_std": 12.4},
        {"drug_name": "Insulin glargine", "atc_code": "A10AE04",
         "site_id": "Hôpital Cochin", "current_stock": 320,
         "stockout_date": (today + timedelta(days=18)).isoformat(),
         "horizon_days": 30, "shortage_prob": 0.61,
         "daily_demand_mean": 17.8, "daily_demand_std": 4.1},
        {"drug_name": "Amoxicillin/clavulanate", "atc_code": "J01CR02",
         "site_id": "CHU Bordeaux Pellegrin", "current_stock": 1450,
         "stockout_date": (today + timedelta(days=23)).isoformat(),
         "horizon_days": 30, "shortage_prob": 0.42,
         "daily_demand_mean": 62.2, "daily_demand_std": 9.0},
        {"drug_name": "MMR vaccine", "atc_code": "J07BD52",
         "site_id": "CHU Toulouse Rangueil", "current_stock": 220,
         "stockout_date": (today + timedelta(days=26)).isoformat(),
         "horizon_days": 30, "shortage_prob": 0.31,
         "daily_demand_mean": 8.4, "daily_demand_std": 2.8},
        {"drug_name": "Insulin detemir", "atc_code": "A10AE05",
         "site_id": "CHU Lyon-Nord", "current_stock": 510,
         "stockout_date": (today + timedelta(days=29)).isoformat(),
         "horizon_days": 30, "shortage_prob": 0.18,
         "daily_demand_mean": 17.0, "daily_demand_std": 4.4},
    ]


def shortage_forecast_curve(atc_code: str, *, horizon_days: int = 30) -> dict:
    """Retourne les points historiques + prévision pour le graphique Prophet.

    Format de sortie ::
        {
            "history":  [{"ts": ISO, "stock": int}, ...]   (~90 jours)
            "forecast": [{"ts": ISO, "yhat": float,
                          "yhat_lower": float, "yhat_upper": float}, ...]
        }
    """
    today = datetime.now(UTC).date()
    rng = random.Random(hash(atc_code) & 0xFFFF)

    # Stock initial et profil de consommation par famille ATC
    if atc_code.startswith("J07"):
        base, daily, noise = 2200, 58, 14
    elif atc_code.startswith("A10"):
        base, daily, noise = 900, 22, 6
    elif atc_code.startswith("J01"):
        base, daily, noise = 3800, 64, 18
    else:
        base, daily, noise = 1500, 30, 8

    history: list[dict] = []
    stock = base
    for i in range(90, 0, -1):
        # Légère saisonnalité hebdomadaire
        seasonal = 1.0 + 0.08 * math.sin((90 - i) / 7 * 2 * math.pi)
        consumed = max(0, daily * seasonal + rng.gauss(0, noise))
        stock = max(0, stock - consumed + (rng.choice([0, 0, 0, 240]) if i % 9 == 0 else 0))
        history.append({"ts": (today - timedelta(days=i)).isoformat(),
                        "stock": round(stock)})

    last = history[-1]["stock"]
    forecast: list[dict] = []
    for i in range(1, horizon_days + 1):
        seasonal = 1.0 + 0.08 * math.sin((90 + i) / 7 * 2 * math.pi)
        center = max(0, last - daily * seasonal * i + rng.gauss(0, noise * 0.5))
        spread = max(20, daily * 0.35 * math.sqrt(i))
        forecast.append({
            "ts":         (today + timedelta(days=i)).isoformat(),
            "yhat":       round(center, 1),
            "yhat_lower": round(max(0, center - spread), 1),
            "yhat_upper": round(center + spread, 1),
        })
    return {"history": history, "forecast": forecast}


# ---------------------------------------------------------------------------
# Santé système (mock pour mode hors-ligne / CI)
# ---------------------------------------------------------------------------
def services_status() -> list[dict]:
    """Payload d'état des services simulé, utilisé par la page Overview."""
    return [
        {"name": "Ollama",      "state": "ok",  "mode": "mock",  "detail": "phi3:mini (mock)"},
        {"name": "Redpanda",    "state": "ok",  "mode": "mock",  "detail": "1 partition, lag 0"},
        {"name": "TimescaleDB", "state": "ok",  "mode": "mock",  "detail": "hypertables ok"},
        {"name": "ChromaDB",    "state": "ok",  "mode": "mock",  "detail": "232 chunks, 7 docs"},
        {"name": "Dagster",     "state": "ok",  "mode": "live",  "detail": "5 assets up to date"},
        {"name": "Grafana",     "state": "ok",  "mode": "live",  "detail": "alerting healthy"},
    ]


# ---------------------------------------------------------------------------
# Flux d'alertes récentes (en haut à droite "ce qui se passe maintenant")
# ---------------------------------------------------------------------------
def recent_alerts() -> list[dict]:
    """Flux d'alertes : libellés humains d'abord (« mot métier en premier »),
    le code technique d'origine est conservé dans ``tech`` (infobulle)."""
    now = datetime.now(UTC)
    return [
        {"ts": (now - timedelta(minutes=2)).strftime("%H:%M"),
         "level": "crit",
         "title": "Rupture de la chaîne du froid (frigo F-04-01)",
         "site":  "CHU Bordeaux Pellegrin",
         "msg":   "11,2 °C depuis 72 min, hors de la zone de sécurité 2-8 °C.",
         "tech":  "EXCURSION 11.2 °C (F-04-01)"},
        {"ts": (now - timedelta(minutes=14)).strftime("%H:%M"),
         "level": "crit",
         "title": "Risque de casse de la chaîne du froid (frigo F-01-03)",
         "site":  "CHU Lyon-Sud",
         "msg":   "Pic à 9,4 °C. Lot VAX-2026-0142 à vérifier (640 doses).",
         "tech":  "BREAKAGE_RISK (F-01-03)"},
        {"ts": (now - timedelta(minutes=37)).strftime("%H:%M"),
         "level": "warn",
         "title": "Risque de rupture : vaccin grippe (Influenza)",
         "site":  "Réseau",
         "msg":   "Probabilité de rupture sous 14 jours : 78 %.",
         "tech":  "Shortage signal FDA (J07BB02)"},
        {"ts": (now - timedelta(hours=1, minutes=2)).strftime("%H:%M"),
         "level": "info",
         "title": "Prévisions recalculées",
         "site":  "Réseau",
         "msg":   "5 médicaments mis à jour, fiabilité élevée.",
         "tech":  "Forecast rerun Prophet (Dagster), MAPE moyen 7,4 %"},
        {"ts": (now - timedelta(hours=2)).strftime("%H:%M"),
         "level": "warn",
         "title": "Excursion modérée résolue (frigo F-02-02)",
         "site":  "CHU Lyon-Nord",
         "msg":   "Pointe à 8,6 °C résolue après 8 min.",
         "tech":  "Excursion modérée (F-02-02)"},
    ]


# ---------------------------------------------------------------------------
# Pont causal excursion vers rupture : quels médicaments ont un lot stocké dans
# un frigo actuellement en excursion ? (contrat consommé par les pages
# Tour de contrôle, Réfrigérateurs et Prévision des ruptures)
# ---------------------------------------------------------------------------
def excursion_affected_drugs() -> dict:
    """Mapping ``atc_code`` vers ``{fridge, site, lot, doses, drug_name}``.

    Version démo : le scénario plante le lot Influenza dans le frigo critique
    de Bordeaux. En live, la même fonction joint ``inventory_lots`` aux
    alertes ouvertes.
    """
    return {
        "J07BB02": {
            "fridge":    "F-04-01",
            "site":      "CHU Bordeaux Pellegrin",
            "lot":       "VAX-2026-0142",
            "doses":     640,
            "drug_name": "Influenza vaccine (inactivated)",
        },
    }


def telemetry_freshness() -> str:
    """Âge du dernier point de télémétrie reçu (objectif ≤ 5 min)."""
    return "1 min 32 s"


# ---------------------------------------------------------------------------
# Qualité de données : checks d'assets à la Dagster
# ---------------------------------------------------------------------------
def asset_checks() -> list[dict]:
    return [
        {"asset": "raw_telemetry",            "check": "freshness ≤ 5 min",
         "result": "pass", "value": "1 min 32 s",   "severity": "ok",
         "last_run": "2026-05-27 09:14 UTC"},
        {"asset": "raw_telemetry",            "check": "schema unchanged",
         "result": "pass", "value": "12 cols",      "severity": "ok",
         "last_run": "2026-05-27 09:14 UTC"},
        {"asset": "raw_telemetry",            "check": "temp ∈ [-30, 40] °C",
         "result": "pass", "value": "0 outliers",   "severity": "ok",
         "last_run": "2026-05-27 09:14 UTC"},
        {"asset": "silver_excursions",        "check": "no duplicate alerts",
         "result": "pass", "value": "0 dup",        "severity": "ok",
         "last_run": "2026-05-27 09:12 UTC"},
        {"asset": "silver_excursions",        "check": "alert volume vs J-7",
         "result": "warn", "value": "+38 %",        "severity": "warn",
         "last_run": "2026-05-27 09:12 UTC"},
        {"asset": "gold_shortage_forecast",   "check": "MAPE ≤ 12 %",
         "result": "pass", "value": "7.4 %",        "severity": "ok",
         "last_run": "2026-05-27 08:30 UTC"},
        {"asset": "gold_shortage_forecast",   "check": "freshness ≤ 24 h",
         "result": "pass", "value": "4 h 18 m",     "severity": "ok",
         "last_run": "2026-05-27 08:30 UTC"},
        {"asset": "rag_protocol_index",       "check": "embedding drift ≤ 0.05",
         "result": "pass", "value": "0.018",        "severity": "ok",
         "last_run": "2026-05-26 22:00 UTC"},
        {"asset": "rag_protocol_index",       "check": "PDF ingestion errors",
         "result": "fail", "value": "1 ANSM PDF",   "severity": "crit",
         "last_run": "2026-05-26 22:00 UTC"},
    ]


def dagster_runs() -> list[dict]:
    return [
        {"job": "coldchain_streaming",    "status": "ok",   "duration_s": 14400, "started": "05:00"},
        {"job": "shortage_forecast_job",  "status": "ok",   "duration_s": 372,   "started": "08:30"},
        {"job": "rag_indexer_job",        "status": "warn", "duration_s": 188,   "started": "22:00"},
        {"job": "openfda_ingestion_job",  "status": "ok",   "duration_s": 56,    "started": "07:00"},
    ]


# ---------------------------------------------------------------------------
# Journal d'audit (page de validation)
# ---------------------------------------------------------------------------
def audit_log() -> list[dict]:
    return [
        {"ts": "2026-05-27 09:14:02", "actor": "pharmacist@cochin", "role": "pharmacist",
         "event": "brief_validated", "brief_id": "b71f4a8e2c1d",
         "drug": "Insulin glargine", "ok": True, "note": "stock vérifié"},
        {"ts": "2026-05-27 09:11:55", "actor": "nurse@cochin", "role": "nurse",
         "event": "5B_check", "brief_id": "b71f4a8e2c1d",
         "drug": "Insulin glargine", "ok": True, "note": "5/5 cases cochées"},
        {"ts": "2026-05-27 08:58:21", "actor": "pharmacist@lyon-sud", "role": "pharmacist",
         "event": "brief_rejected", "brief_id": "a302d11abf04",
         "drug": "Influenza vaccine", "ok": False, "note": "stock_check fail"},
    ]
