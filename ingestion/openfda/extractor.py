"""Extracteur openFDA Drug Label.

Endpoint : https://api.fda.gov/drug/label.json
On ne récupère les labels que pour les médicaments présents dans la table bronze shortages :
inutile de tirer 20 000 labels qu'on ne regardera jamais.

SOURCE DE DONNÉES PUBLIQUE
--------------------------
Ces données sont sous licence CC0 (domaine public).
- Accès libre, pas de clé API nécessaire
- Réutilisation libre : reproductible et utilisable légalement
- Source officielle FDA : informations complètes sur les étiquettes médicaments

Voir docs/governance_hipaa_rgpd.md pour la politique de licence et de réutilisation.
"""
from __future__ import annotations

import hashlib
from typing import Any

from loguru import logger

from ingestion.config import settings
from ingestion.utils.db import pg_conn, upsert_bronze
from ingestion.utils.http import get_json


def _drugs_in_shortage() -> list[str]:
    """Retourne les noms génériques uniques actuellement en pénurie dans le bronze shortages."""
    sql = """
        SELECT DISTINCT (payload ->> 'generic_name') AS name
        FROM bronze.fda_shortages
        WHERE (payload ->> 'generic_name') IS NOT NULL
        LIMIT 250
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall() if r[0]]


def fetch_label(generic_name: str) -> dict[str, Any] | None:
    cfg = settings()
    try:
        data = get_json(
            cfg.openfda_url,
            params={"search": f'openfda.generic_name:"{generic_name}"', "limit": 1},
        )
    except Exception as exc:
        logger.warning(f"openFDA fetch for {generic_name!r} failed: {exc}")
        return None
    results = data.get("results") or []
    return results[0] if results else None


def run() -> int:
    drugs = _drugs_in_shortage()
    if not drugs:
        logger.warning("No shortages in bronze yet: run `make ingest` first or "
                       "ensure FDA extractor ran.")
        return 0

    rows = []
    for name in drugs:
        label = fetch_label(name)
        if not label:
            continue
        set_id = label.get("set_id") or hashlib.sha1(name.encode(), usedforsecurity=False).hexdigest()
        rows.append({"source_row_id": set_id, "payload": label})

    return upsert_bronze("openfda_labels", rows)


if __name__ == "__main__":
    run()
