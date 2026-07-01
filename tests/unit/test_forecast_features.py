"""Tests unitaires pour les helpers de features de prévision.

``external_shortage_signal`` touche Postgres, donc on patch la connexion et
on vérifie l'*arithmétique du facteur de boost* indépendamment de la base.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


@contextmanager
def _fake_conn(rows: list[tuple[str, str]]):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    cur.fetchall.return_value = rows
    yield conn


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([], 1.0),
        ([("fda",  "active")], 1.2),
        ([("ansm", "active")], 1.2),
        ([("ema",  "active")], 1.15),
        ([("fda",  "active"), ("ansm", "active")], 1.4),
        # plafonné à 1.5
        ([("fda",  "active"), ("ansm", "active"), ("ema", "active"),
          ("fda",  "resolved")], 1.5),
        # source inconnue : repli à 0.05
        ([("who",  "active")], 1.05),
    ],
)
def test_external_shortage_signal(monkeypatch, rows, expected):
    from ml import features as feat

    def _fake_pg_conn():
        return _fake_conn(rows)

    monkeypatch.setattr(feat, "pg_conn", _fake_pg_conn)
    got = feat.external_shortage_signal("D-1")
    assert got == pytest.approx(expected, abs=1e-6)
