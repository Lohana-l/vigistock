"""Aiguillage de la source de données : mock (démo) ou stack live.

C'est le SEUL endroit où l'app choisit qui remplit le contrat de données.
Les pages importent ``from lib.data import M`` et ne savent pas (et n'ont
pas à savoir) si ``M`` est le mock ou la vraie stack.

Règles
------
* ``USE_MOCK_DATA=false`` (défaut, .env) utilise ``live_data`` : requêtes
  TimescaleDB réelles, sorties du pipeline seedé par db-init.
* ``USE_MOCK_DATA=true`` utilise le mock : démo reproductible hors stack.
  Chaque fonction live retombe individuellement sur le mock (bascule
  loggée) si la base est injoignable : la démo ne casse jamais.

``data_mode()`` dit honnêtement à l'UI ce qui est réellement servi
(le chip du sidebar l'affiche).
"""
from __future__ import annotations

from . import mock_data
from .settings import get_settings

_settings = get_settings()

if _settings.use_mock_data:
    M = mock_data
else:
    # Réexport volontaire : M est le contrat consommé par toutes les pages.
    from . import live_data as M  # noqa: F401  # type: ignore[no-redef]


def data_mode() -> dict:
    """Mode réellement actif, pour le chip de statut du sidebar.

    Retourne ``{"mode": ..., "label": ..., "note": ...}`` avec mode ∈
    ``demo`` | ``live`` | ``fallback``.
    """
    if _settings.use_mock_data:
        return {
            "mode": "demo",
            "label": "Mode démo (télémétrie simulée)",
            "okline": "Signaux pénurie réels : FDA / ANSM (open data)",
            "note": "Aucune donnée patient. Réinitialisé à chaque démarrage.",
        }
    from . import live_data
    if live_data.ping():
        return {
            "mode": "live",
            "label": "Stack live (télémétrie simulée)",
            "okline": "Signaux pénurie réels : FDA / ANSM (open data)",
            "note": "Capteurs IoT simulés (SimPy) en continu. "
                    "Aucune donnée patient.",
        }
    return {
        "mode": "fallback",
        "label": "Stack injoignable : repli démo",
        "okline": "",
        "note": "La base ne répond pas : données simulées servies en repli. "
                "Aucune donnée patient. Lancez la stack (docker compose up).",
    }
