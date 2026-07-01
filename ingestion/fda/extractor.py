"""Extracteur FDA Drug Shortages.

Endpoint : https://api.fda.gov/drug/shortages.json
- Non authentifié, ~240 req/min anonyme.
- Jusqu'à 1000 enregistrements par page ; pagination via `limit` + `skip`.
- Retourne une ligne par (generic_name, status_date), upsertée dans bronze.

SOURCE DE DONNÉES PUBLIQUE
--------------------------
Ces données appartiennent au domaine public (U.S. FDA).
- Accès libre, pas de clé API nécessaire
- Réutilisation libre : reproductible et utilisable légalement
- Source gouvernementale : suivi officiel des pénuries médicamenteuses FDA

Voir docs/governance_hipaa_rgpd.md pour la politique de licence et de réutilisation.
"""
from __future__ import annotations

import hashlib
from typing import Any

from loguru import logger

from ingestion.config import settings
from ingestion.utils.db import upsert_bronze
from ingestion.utils.http import get_json

PAGE_SIZE = 1000
MAX_PAGES = 10  # garde-fou ; le dataset fait ~10 000 lignes au total


def _row_id(payload: dict[str, Any]) -> str:
    """Identifiant stable pour la déduplication. La FDA n'en fournit pas, on le hache."""
    key = f"{payload.get('generic_name','')}|{payload.get('status_date','')}|{payload.get('change_date','')}"
    return hashlib.sha1(key.encode(), usedforsecurity=False).hexdigest()


def fetch_page(skip: int) -> list[dict[str, Any]]:
    cfg = settings()
    data = get_json(cfg.fda_shortages_url, params={"limit": PAGE_SIZE, "skip": skip})
    return data.get("results", [])


def run() -> int:
    rows = []
    for page in range(MAX_PAGES):
        skip = page * PAGE_SIZE
        try:
            results = fetch_page(skip)
        except Exception as exc:
            # La FDA retourne 404 une fois qu'on dépasse le dataset : on traite ça comme la fin du flux
            logger.info(f"FDA paging stopped at skip={skip}: {exc}")
            break
        if not results:
            break
        rows.extend(
            {"source_row_id": _row_id(r), "payload": r} for r in results
        )
        logger.debug(f"FDA page {page}: +{len(results)} rows")
        if len(results) < PAGE_SIZE:
            break

    return upsert_bronze("fda_shortages", rows)


if __name__ == "__main__":
    run()
