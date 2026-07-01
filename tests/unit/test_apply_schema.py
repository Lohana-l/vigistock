"""Tests unitaires du découpeur SQL de scripts/apply_schema.py.

Régression couverte : un point-virgule typographique dans un commentaire
français (« indéfiniment ; les vues silver... ») coupait le statement en
deux et faisait échouer db-init au démarrage de la stack.
"""
from __future__ import annotations

from pathlib import Path

from scripts.apply_schema import _statements

SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "timescale"

_SQL_STARTERS = ("CREATE", "SELECT", "INSERT", "DELETE", "ALTER", "DROP", "--")


def test_semicolon_in_comment_does_not_split():
    sql = (
        "-- On garde le JSONB indéfiniment ; les vues silver castent le reste.\n"
        "CREATE TABLE t (id INT);\n"
    )
    stmts = _statements(sql)
    assert len(stmts) == 1
    assert stmts[0].endswith("CREATE TABLE t (id INT)")


def test_semicolon_in_string_literal_does_not_split():
    sql = "INSERT INTO t (txt) VALUES ('a;b');\nSELECT 1;\n"
    stmts = _statements(sql)
    assert len(stmts) == 2
    assert "'a;b'" in stmts[0]


def test_comment_only_fragments_are_dropped():
    sql = "-- en-tête seul\n\nSELECT 1;\n-- pied de page\n"
    stmts = _statements(sql)
    assert len(stmts) == 1


def test_real_schema_files_split_into_valid_statements():
    """Chaque statement issu des vrais fichiers DDL doit commencer par un
    mot-clé SQL (éventuellement précédé de commentaires) : c'est exactement
    l'invariant que la régression avait cassé."""
    files = sorted(SQL_DIR.glob("*.sql"))
    assert files, "fichiers DDL introuvables"
    for f in files:
        for stmt in _statements(f.read_text()):
            first_code_line = next(
                (ln.strip() for ln in stmt.splitlines()
                 if ln.strip() and not ln.strip().startswith("--")),
                "",
            )
            assert first_code_line.upper().startswith(_SQL_STARTERS), (
                f"{f.name} : fragment suspect -> {first_code_line[:60]!r}"
            )
