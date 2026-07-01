"""Extracteur OpenPrescribing.net : volumes de prescription GP au Royaume-Uni (CC-BY).

Endpoint : https://openprescribing.net/api/1.0
On tire un petit échantillon (un code BNF chimique, tous les CCG, 36 derniers mois)
pour amorcer le modèle de demande avec une saisonnalité réaliste. Volume de démo uniquement.

SOURCE DE DONNÉES PUBLIQUE
--------------------------
Ces données sont sous licence CC BY 4.0 (Creative Commons Attribution).
- Accès libre, pas de clé API nécessaire
- Réutilisation libre : reproductible et utilisable légalement
- Source NHS : données réelles de prescription GP britannique avec patterns de demande réalistes

Voir docs/governance_hipaa_rgpd.md pour la politique de licence et de réutilisation.
"""
from __future__ import annotations

import hashlib
from typing import Any

from loguru import logger

from ingestion.config import settings
from ingestion.utils.db import upsert_bronze
from ingestion.utils.http import get_json

# Code BNF chimique pour l'oseltamivir : demande saisonnière illustrative
DEFAULT_BNF_CODE = "0507000I0"


def _row_id(rec: dict[str, Any]) -> str:
    key = f"{rec.get('row_id','')}|{rec.get('date','')}|{rec.get('row_name','')}"
    return hashlib.sha1(key.encode(), usedforsecurity=False).hexdigest()


def run(bnf_code: str = DEFAULT_BNF_CODE) -> int:
    cfg = settings()
    url = f"{cfg.openprescribing_url}/spending_by_org"
    try:
        results = get_json(
            url,
            params={"code": bnf_code, "format": "json", "org_type": "ccg"},
        )
    except Exception as exc:
        logger.warning(f"OpenPrescribing unreachable ({exc}): skipping.")
        return 0

    if not isinstance(results, list):
        logger.warning(f"Unexpected payload from OpenPrescribing: {type(results)}")
        return 0

    rows = [{"source_row_id": _row_id(r), "payload": r} for r in results]
    return upsert_bronze("openprescribing_usage", rows)


if __name__ == "__main__":
    run()
