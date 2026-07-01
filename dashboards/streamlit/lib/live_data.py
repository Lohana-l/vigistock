"""Implémentation LIVE du contrat de données : requêtes sur la vraie stack.

C'est le pont entre le pipeline (Redpanda puis TimescaleDB puis Prophet puis Dagster)
et l'UI Streamlit. Chaque fonction implémente EXACTEMENT la même signature
que ``mock_data.py`` (le contrat), mais en SQL sur les schémas réels :

* ``silver.telemetry_raw`` / ``silver.telemetry_5m`` : télémétrie frigos
  écrite par ``streaming/consumer.py``.
* ``silver.alerts``                                  : alertes d'excursion.
* ``silver.inventory_lots`` / ``gold.v_stock_current`` : stock par lot.
* ``gold.v_forecast_latest`` / ``silver.forecasts``  : sorties Prophet.
* ``silver.audit_log``                                : journal d'audit.

Robustesse
----------
Chaque fonction est enveloppée par ``@_with_fallback`` : si la base est
injoignable, on retombe sur l'équivalent mock et la bascule est LOGGÉE
(une erreur de schéma ne doit jamais être invisible). Un résultat vide
n'est un repli que lorsque le vide signifie « pipeline pas encore
alimenté » (flotte, KPI) ; pour les flux où le vide est un état sain
(alertes, journal d'audit), il est rendu tel quel : afficher de fausses
alertes en mode live serait mentir à l'utilisateur.
``ping()`` permet à l'UI d'afficher honnêtement le mode réellement actif.

Les lectures sont mises en cache 15 s (``st.cache_data``), aligné sur le
rythme de rafraîchissement des fragments de l'Overview.
"""
from __future__ import annotations

import logging
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import streamlit as st

from . import mock_data as _mock
from .settings import get_settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # psycopg absent : tout retombe sur le mock
    psycopg = None  # type: ignore


_CONNECT_TIMEOUT_S = 2

logger = logging.getLogger("vigistock.live_data")


# ---------------------------------------------------------------------------
# Connexion & helpers
# ---------------------------------------------------------------------------
def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Exécute une requête en lecture seule et retourne des lignes dict.

    Connexion courte (pas de pool) : les volumes lus par l'UI sont faibles
    et le cache 15 s absorbe la charge.
    """
    s = get_settings()
    with psycopg.connect(s.dsn, connect_timeout=_CONNECT_TIMEOUT_S,
                         row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@st.cache_data(ttl=15, show_spinner=False)
def ping() -> bool:
    """La base répond-elle ? Utilisé par le chip de mode du sidebar."""
    if psycopg is None:
        return False
    try:
        _query("SELECT 1")
        return True
    except Exception:
        return False


def _with_fallback(mock_fn_name: str, *, empty_falls_back: bool = True) -> Callable:
    """Décorateur de repli vers la fonction mock du même nom.

    * Erreur (base injoignable, schéma divergent) : repli mock, TOUJOURS
      loggé en warning pour rester diagnosticable.
    * Résultat vide : repli uniquement si ``empty_falls_back`` est vrai,
      c'est-à-dire quand le vide signifie « pipeline pas encore alimenté ».
      Pour un flux d'alertes ou un journal d'audit, vide est un état sain
      et il est rendu tel quel.
    """
    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                out = fn(*args, **kwargs)
            except Exception as exc:
                logger.warning("repli mock pour %s : %s", fn.__name__, exc)
                return getattr(_mock, mock_fn_name)(*args, **kwargs)
            if empty_falls_back and out in (None, [], {}):
                logger.info(
                    "repli mock pour %s : résultat vide, pipeline pas encore alimenté",
                    fn.__name__,
                )
                return getattr(_mock, mock_fn_name)(*args, **kwargs)
            return out
        return wrapper
    return deco


def _hm(ts: datetime) -> str:
    """Horodatage uniformisé « HH:MM » (heure locale UTC du serveur)."""
    return ts.astimezone(UTC).strftime("%H:%M")


# ---------------------------------------------------------------------------
# Référentiel médicaments (dim_drugs)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def _drugs() -> list[tuple[str, str]]:
    try:
        rows = _query(
            "SELECT generic_name, drug_id FROM silver.dim_drugs "
            "WHERE cold_chain ORDER BY generic_name"
        )
        return [(r["generic_name"], r["drug_id"]) for r in rows] or _mock.DRUGS
    except Exception:
        return _mock.DRUGS


# Contrat : ``DRUGS`` est consommé par les pages comme un attribut de module.
# Résolution PARESSEUSE via PEP 562 : l'ancienne affectation au niveau module
# figeait la liste à l'import, avant que la base soit prête, et l'app restait
# sur le mock jusqu'au redémarrage du conteneur. Ici chaque accès passe par
# _drugs() (cache 5 min), qui suit l'état réel de la base.
SITES = _mock.SITES  # libellés de secours uniquement


def __getattr__(name: str) -> Any:
    if name == "DRUGS":
        return _drugs()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Snapshot de la flotte
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("fleet_snapshot")
def fleet_snapshot() -> list[dict]:
    """Dernier relevé par frigo (1 h glissante) + nombre de lots actifs."""
    rows = _query("""
        SELECT DISTINCT ON (t.fridge_id)
               t.fridge_id,
               s.site_name                  AS site,
               t.temperature_c::float       AS temp_c,
               t.event_ts                   AS last_ts,
               COALESCE(l.n_lots, 0)        AS lots
        FROM silver.telemetry_raw t
        JOIN silver.dim_fridges f ON f.fridge_id = t.fridge_id
        JOIN silver.dim_sites   s ON s.site_id   = f.site_id
        LEFT JOIN (
            SELECT fridge_id, COUNT(*) AS n_lots
            FROM silver.inventory_lots
            WHERE expires_at > NOW()
            GROUP BY fridge_id
        ) l ON l.fridge_id = t.fridge_id
        WHERE t.event_ts > NOW() - INTERVAL '1 hour'
        ORDER BY t.fridge_id, t.event_ts DESC
    """)
    return [{
        "fridge_id": r["fridge_id"],
        "site":      r["site"],
        "temp_c":    round(r["temp_c"], 1),
        "lots":      int(r["lots"]),
        "last_seen": _hm(r["last_ts"]),
        "sparkline": [],   # non utilisé par l'UI actuelle
    } for r in rows]


@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("fridge_24h")
def fridge_24h(fridge_id: str = "F-01-03") -> list[dict]:
    """24 h de température en tranches de 5 min (agrégat continu)."""
    rows = _query("""
        SELECT bucket AS ts, avg_temp_c::float AS temp
        FROM silver.telemetry_5m
        WHERE fridge_id = %s AND bucket > NOW() - INTERVAL '24 hours'
        ORDER BY bucket
    """, (fridge_id,))
    return [{"ts": r["ts"].isoformat(), "temp": round(r["temp"], 2)}
            for r in rows]


@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("kpi_snapshot")
def kpi_snapshot() -> dict:
    fleet = fleet_snapshot()
    crit = sum(1 for f in fleet if f["temp_c"] > 10 or f["temp_c"] < 2)
    warn = sum(1 for f in fleet if 8 < f["temp_c"] <= 10)

    suspect = _query("""
        SELECT COUNT(*) AS n FROM silver.inventory_lots
        WHERE suspect AND expires_at > NOW()
    """)[0]["n"]

    at_risk = _query("""
        SELECT COUNT(DISTINCT drug_id) AS n
        FROM gold.v_forecast_latest WHERE shortage_prob >= 0.3
    """)[0]["n"]

    epm = _query("""
        SELECT COUNT(*) AS n FROM silver.telemetry_raw
        WHERE event_ts > NOW() - INTERVAL '5 minutes'
    """)[0]["n"]

    return {
        "open_alerts":     crit + warn,
        "critical_alerts": crit,
        "warn_alerts":     warn,
        "suspect_lots":    int(suspect),
        "at_risk_drugs":   int(at_risk),
        "fridges_total":   len(fleet),
        "sites_total":     len({f["site"] for f in fleet}),
        "uptime_pct":      _fleet_uptime_pct(),
        "events_per_min":  round(epm / 5),
    }


def _fleet_uptime_pct() -> float:
    """Disponibilité réelle : part des frigos référencés ayant émis de la
    télémétrie dans les 10 dernières minutes. Remplace l'ancienne valeur
    codée en dur, indéfendable sur une page qui se dit live."""
    row = _query("""
        SELECT COUNT(*) FILTER (WHERE t.fridge_id IS NOT NULL) AS up,
               COUNT(*)                                        AS total
        FROM silver.dim_fridges f
        LEFT JOIN (
            SELECT DISTINCT fridge_id
            FROM silver.telemetry_raw
            WHERE event_ts > NOW() - INTERVAL '10 minutes'
        ) t ON t.fridge_id = f.fridge_id
    """)[0]
    if not row["total"]:
        raise ValueError("aucun frigo référencé : dimensions pas encore seedées")
    return round(100.0 * row["up"] / row["total"], 1)


# ---------------------------------------------------------------------------
# Prévisions de rupture (sorties Prophet réelles)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
@_with_fallback("shortage_overview")
def shortage_overview() -> list[dict]:
    rows = _query("""
        SELECT d.generic_name                       AS drug_name,
               fl.drug_id                           AS atc_code,
               s.site_name                          AS site_id,
               COALESCE(st.doses_available, fl.doses_remaining, 0)
                 - COALESCE(st.doses_suspect, 0)    AS current_stock,
               fl.predicted_stockout_on             AS stockout_date,
               fl.horizon_days,
               fl.shortage_prob::float              AS shortage_prob
        FROM gold.v_forecast_latest fl
        JOIN silver.dim_drugs d ON d.drug_id = fl.drug_id
        JOIN silver.dim_sites s ON s.site_id = fl.site_id
        LEFT JOIN gold.v_stock_current st
               ON st.site_id = fl.site_id AND st.drug_id = fl.drug_id
        WHERE fl.predicted_stockout_on IS NOT NULL
        ORDER BY fl.shortage_prob DESC
    """)
    today = datetime.now(UTC).date()
    out = []
    for r in rows:
        days_left = max(1, (r["stockout_date"] - today).days)
        mean = max(0.1, float(r["current_stock"]) / days_left)
        out.append({
            "drug_name":         r["drug_name"],
            "atc_code":          r["atc_code"],
            "site_id":           r["site_id"],
            "current_stock":     int(r["current_stock"]),
            "stockout_date":     r["stockout_date"].isoformat(),
            "horizon_days":      int(r["horizon_days"]),
            "shortage_prob":     round(r["shortage_prob"], 2),
            # La demande journalière n'est pas matérialisée en gold :
            # estimée depuis stock / jours restants (suffisant pour l'UI).
            "daily_demand_mean": round(mean, 1),
            "daily_demand_std":  round(mean * 0.2, 1),
        })
    return out


@st.cache_data(ttl=60, show_spinner=False)
@_with_fallback("shortage_forecast_curve")
def shortage_forecast_curve(atc_code: str, *, horizon_days: int = 30) -> dict:
    """Courbe RÉELLE du dernier run Prophet.

    * Historique : trajectoire des ``doses_remaining`` des runs successifs
      (``silver.forecasts``) , l'évolution réellement observée du stock.
    * Prévision : les points quotidiens matérialisés par le job ML dans
      ``gold.forecast_points`` (médiane + bande de confiance 80 %).
    """
    hist = _query("""
        SELECT forecast_ts::date AS d, MAX(doses_remaining) AS stock
        FROM silver.forecasts
        WHERE drug_id = %s AND forecast_ts > NOW() - INTERVAL '90 days'
        GROUP BY 1 ORDER BY 1
    """, (atc_code,))
    if len(hist) < 5:
        raise ValueError("historique insuffisant")  # repli sur le mock
    history = [{"ts": r["d"].isoformat(), "stock": int(r["stock"])} for r in hist]

    # Points réels du dernier run (site le plus à risque pour ce médicament)
    pts = _query("""
        SELECT p.ds, p.stock_yhat, p.stock_yhat_lower, p.stock_yhat_upper
        FROM gold.v_forecast_points_latest p
        JOIN gold.v_forecast_latest fl
          ON fl.site_id = p.site_id AND fl.drug_id = p.drug_id
        WHERE p.drug_id = %s
        ORDER BY fl.shortage_prob DESC, p.ds
        LIMIT %s
    """, (atc_code, horizon_days))

    if pts:
        forecast = [{
            "ts":         r["ds"].isoformat(),
            "yhat":       float(r["stock_yhat"]),
            "yhat_lower": float(r["stock_yhat_lower"]),
            "yhat_upper": float(r["stock_yhat_upper"]),
        } for r in pts]
        return {"history": history, "forecast": forecast}

    # Repli (table de points pas encore alimentée) : déclin linéaire vers la
    # date de rupture prévue, avec bande d'incertitude croissante.
    latest = _query("""
        SELECT predicted_stockout_on, doses_remaining
        FROM gold.v_forecast_latest
        WHERE drug_id = %s ORDER BY shortage_prob DESC LIMIT 1
    """, (atc_code,))[0]

    today = datetime.now(UTC).date()
    last_stock = float(latest["doses_remaining"] or history[-1]["stock"])
    days_to_zero = max(1, (latest["predicted_stockout_on"] - today).days) \
        if latest["predicted_stockout_on"] else horizon_days
    daily = last_stock / days_to_zero

    from datetime import timedelta
    forecast = []
    for i in range(1, horizon_days + 1):
        center = max(0.0, last_stock - daily * i)
        spread = max(10.0, daily * 0.35 * (i ** 0.5))
        forecast.append({
            "ts":         (today + timedelta(days=i)).isoformat(),
            "yhat":       round(center, 1),
            "yhat_lower": round(max(0.0, center - spread), 1),
            "yhat_upper": round(center + spread, 1),
        })
    return {"history": history, "forecast": forecast}


# ---------------------------------------------------------------------------
# Flux d'alertes (silver.alerts via gold.v_alerts_active)
# ---------------------------------------------------------------------------
_SEVERITY_LEVEL = {"CRITICAL": "crit", "BREAKAGE_RISK": "crit",
                   "WARN": "warn", "INFO": "info"}
_SEVERITY_TITLE = {
    "CRITICAL":      "Rupture de la chaîne du froid",
    "BREAKAGE_RISK": "Risque de casse de la chaîne du froid",
    "WARN":          "Excursion modérée",
    "INFO":          "Information",
}


@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("recent_alerts", empty_falls_back=False)
def recent_alerts() -> list[dict]:
    rows = _query("""
        SELECT opened_at, site_name, fridge_id, severity,
               peak_temp_c::float AS peak, duration_sec
        FROM gold.v_alerts_active
        ORDER BY opened_at DESC LIMIT 5
    """)
    out = []
    for r in rows:
        mins = (r["duration_sec"] or 0) // 60
        peak = f"{r['peak']:.1f}".replace(".", ",") if r["peak"] else "?"
        out.append({
            "ts":    _hm(r["opened_at"]),
            "level": _SEVERITY_LEVEL.get(r["severity"], "warn"),
            "title": f"{_SEVERITY_TITLE.get(r['severity'], r['severity'])} (frigo {r['fridge_id']})",
            "site":  r["site_name"],
            "msg":   f"Pic à {peak} °C, {mins} min hors de la zone 2-8 °C.",
            "tech":  f"{r['severity']} ({r['fridge_id']})",
        })
    return out


# ---------------------------------------------------------------------------
# Pont causal excursion vers rupture : version LIVE.
# Joint les lots d'inventaire aux frigos ayant une alerte ouverte.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("excursion_affected_drugs", empty_falls_back=False)
def excursion_affected_drugs() -> dict:
    rows = _query("""
        SELECT DISTINCT ON (l.drug_id)
               l.drug_id, l.lot_id, l.doses, l.fridge_id,
               s.site_name, d.generic_name
        FROM silver.inventory_lots l
        JOIN silver.alerts a   ON a.fridge_id = l.fridge_id
                              AND a.closed_at IS NULL
        JOIN silver.dim_sites s ON s.site_id = l.site_id
        JOIN silver.dim_drugs d ON d.drug_id = l.drug_id
        WHERE l.expires_at > NOW()
        ORDER BY l.drug_id, l.doses DESC
    """)
    return {r["drug_id"]: {
        "fridge":    r["fridge_id"],
        "site":      r["site_name"],
        "lot":       r["lot_id"],
        "doses":     int(r["doses"]),
        "drug_name": r["generic_name"],
    } for r in rows}


@st.cache_data(ttl=15, show_spinner=False)
@_with_fallback("telemetry_freshness")
def telemetry_freshness() -> str:
    """Âge réel du dernier point de télémétrie reçu."""
    age = _query("""
        SELECT EXTRACT(EPOCH FROM (NOW() - MAX(event_ts)))::int AS s
        FROM silver.telemetry_raw
    """)[0]["s"]
    if age is None:
        raise ValueError("aucune télémétrie")
    m, s = divmod(int(age), 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


# ---------------------------------------------------------------------------
# Santé des services : sondes TCP réelles (timeout court)
# ---------------------------------------------------------------------------
def _probe(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def services_status() -> list[dict]:
    s = get_settings()
    rp_host, _, rp_port = s.redpanda_brokers.partition(":")
    ol_host = s.ollama_host.split("//")[-1].split(":")[0]
    targets = [
        ("TimescaleDB", s.timescale_host, s.timescale_port, "hypertables"),
        ("Redpanda",    rp_host, int(rp_port or 9092),      "bus Kafka API"),
        ("Ollama",      ol_host, 11434,                     s.ollama_model),
        ("ChromaDB",    s.chroma_host, s.chroma_port,       s.chroma_collection),
        ("Dagster",     "dagster", 3000,                    "webserver"),
        ("Grafana",     "grafana", 3000,                    "alerting"),
    ]
    return [{
        "name":   name,
        "state":  "ok" if _probe(host, port) else "crit",
        "mode":   "live",
        "detail": detail,
    } for name, host, port, detail in targets]


# ---------------------------------------------------------------------------
# Journal d'audit (silver.audit_log)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
@_with_fallback("audit_log", empty_falls_back=False)
def audit_log() -> list[dict]:
    rows = _query("""
        SELECT at, actor, action, alert_id, payload
        FROM silver.audit_log ORDER BY at DESC LIMIT 20
    """)
    return [{
        "ts":       r["at"].strftime("%Y-%m-%d %H:%M:%S"),
        "actor":    r["actor"],
        "role":     (r["payload"] or {}).get("role", "non renseigné"),
        "event":    r["action"],
        "brief_id": (r["payload"] or {}).get("brief_id", r["alert_id"] or "non renseigné"),
        "drug":     (r["payload"] or {}).get("drug", "non renseigné"),
        "ok":       (r["payload"] or {}).get("ok", True),
        "note":     (r["payload"] or {}).get("note", ""),
    } for r in rows]


# ---------------------------------------------------------------------------
# Qualité de données : interrogation LIVE du webserver Dagster (GraphQL).
# Repli mock si le webserver est éteint ou l'API indisponible.
# ---------------------------------------------------------------------------
def _dagster_gql(query: str) -> dict:
    import requests
    resp = requests.post(
        get_settings().dagster_graphql_url,
        json={"query": query},
        timeout=2,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


@st.cache_data(ttl=30, show_spinner=False)
def dagster_available() -> bool:
    """Le webserver Dagster répond-il ? Permet à l'UI d'étiqueter honnêtement
    la provenance des contrôles (live vs valeurs de démonstration) : la seule
    disponibilité de la base ne garantit pas celle de l'orchestrateur."""
    try:
        _dagster_gql("{ __typename }")
        return True
    except Exception:
        return False


@st.cache_data(ttl=30, show_spinner=False)
@_with_fallback("dagster_runs")
def dagster_runs() -> list[dict]:
    """Derniers runs réels du webserver Dagster."""
    data = _dagster_gql("""
    {
      runsOrError(limit: 8) {
        ... on Runs {
          results { jobName status startTime endTime }
        }
      }
    }
    """)
    out = []
    for r in data["runsOrError"]["results"]:
        start = r.get("startTime")
        end = r.get("endTime")
        duration = int(end - start) if (start and end) else 0
        status_map = {"SUCCESS": "ok", "FAILURE": "crit", "STARTED": "warn",
                      "QUEUED": "warn", "CANCELED": "crit"}
        out.append({
            "job":        r["jobName"],
            "status":     status_map.get(r["status"], "warn"),
            "duration_s": duration,
            "started":    datetime.fromtimestamp(start, tz=UTC)
                          .strftime("%H:%M") if start else "en attente",
        })
    return out[:4]


@st.cache_data(ttl=30, show_spinner=False)
@_with_fallback("asset_checks")
def asset_checks() -> list[dict]:
    """Asset checks réels : dernier statut d'exécution par check."""
    data = _dagster_gql("""
    {
      assetNodes {
        assetKey { path }
        assetChecksOrError {
          ... on AssetChecks {
            checks {
              name
              executionForLatestMaterialization {
                status
                evaluation { timestamp }
              }
            }
          }
        }
      }
    }
    """)
    status_map = {"SUCCEEDED": ("pass", "ok"), "FAILED": ("fail", "crit"),
                  "EXECUTION_FAILED": ("fail", "crit"),
                  "IN_PROGRESS": ("warn", "warn"), "SKIPPED": ("warn", "warn")}
    out = []
    for node in data["assetNodes"]:
        checks = (node.get("assetChecksOrError") or {}).get("checks") or []
        asset = "/".join(node["assetKey"]["path"])
        for c in checks:
            ex = c.get("executionForLatestMaterialization") or {}
            result, severity = status_map.get(ex.get("status", ""), ("warn", "warn"))
            ts = (ex.get("evaluation") or {}).get("timestamp")
            out.append({
                "asset":    asset,
                "check":    c["name"],
                "result":   result,
                "value":    ex.get("status", "non exécuté"),
                "severity": severity,
                "last_run": datetime.fromtimestamp(ts, tz=UTC)
                            .strftime("%Y-%m-%d %H:%M UTC") if ts else "jamais exécuté",
            })
    return out
