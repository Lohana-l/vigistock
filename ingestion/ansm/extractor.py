"""Extracteur RSS de l'ANSM (France).

Endpoint : https://ansm.sante.fr/actualites.rss
L'ANSM publie ses alertes et signalements de pénurie sous forme de flux RSS public.
On tire le flux et on stocke chaque <item> dans bronze avec un identifiant stable dérivé
du GUID / lien de l'item.

SOURCE DE DONNÉES PUBLIQUE
--------------------------
Données de santé publique française (Agence Nationale de Sécurité du Médicament).
- Accès libre, pas de clé API ni d'authentification requise
- Réutilisation libre : reproductible et utilisable légalement
- Source gouvernementale : alertes officielles de sécurité et pénuries médicamenteuses

Voir docs/governance_hipaa_rgpd.md pour la politique de licence et de réutilisation.
"""
from __future__ import annotations

import hashlib

import feedparser
from loguru import logger

from ingestion.config import settings
from ingestion.utils.db import upsert_bronze
from ingestion.utils.http import session


def fetch_feed() -> list[dict]:
    cfg = settings()
    # feedparser ne partage pas notre session avec retry, donc on fait le GET manuellement
    # et on lui passe le texte brut, ce qui nous donne tenacity + UA + timeout.
    resp = session().get(cfg.ansm_rss_url, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    return feed.entries  # type: ignore[no-any-return]


def _row_id(entry: dict) -> str:
    key = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha1(str(key).encode(), usedforsecurity=False).hexdigest()


def run() -> int:
    try:
        entries = fetch_feed()
    except Exception as exc:
        logger.warning(f"ANSM feed unreachable ({exc}): skipping.")
        return 0

    rows = [
        {
            "source_row_id": _row_id(e),
            "payload": {
                "title":        e.get("title"),
                "link":         e.get("link"),
                "published":    e.get("published"),
                "summary":      e.get("summary"),
                "tags":         [t.get("term") for t in e.get("tags", [])],
            },
        }
        for e in entries
    ]
    return upsert_bronze("ansm_signalements", rows)


if __name__ == "__main__":
    run()
