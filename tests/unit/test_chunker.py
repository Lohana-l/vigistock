"""Tests unitaires pour le découpage de protocoles."""
from __future__ import annotations

from pathlib import Path

from llm.indexer.chunker import _ATC_RE, Chunk, chunk_directory, chunk_text_file


def _atc_codes(text: str) -> list[str]:
    return sorted(set(_ATC_RE.findall(text)))


def test_atc_regex_finds_full_codes():
    assert _atc_codes("Insulin (ATC A10AB01) rapid-acting.") == ["A10AB01"]
    assert _atc_codes("Oseltamivir J05AH02 is preferred.") == ["J05AH02"]


def test_atc_regex_ignores_class_prefixes():
    # "A10AB" seul est une classe (pas de chiffres terminaux 1-2) ; ne doit PAS matcher
    codes = _atc_codes("Combine A10AB and J07BB02 as per protocol.")
    assert codes == ["J07BB02"]


def test_atc_regex_empty_when_absent():
    assert _atc_codes("No ATC mentioned here, just text.") == []


def test_chunker_on_markdown(tmp_path: Path):
    big_section = ("Insulin (ATC A10AB01) is indicated. " * 400).strip()
    md = tmp_path / "big.md"
    md.write_text(
        "# 1 Section A\n\n" + big_section + "\n\n# 2 Section B\n\n" + big_section,
        encoding="utf-8",
    )
    chunks = list(chunk_directory(tmp_path))
    assert len(chunks) >= 1
    for c in chunks:
        assert isinstance(c, Chunk)
        assert c.document_id == "big"
        assert c.page_from >= 1
        assert c.page_to >= c.page_from


def test_chunker_extracts_atc_metadata(tmp_path: Path):
    md = tmp_path / "protocol.md"
    md.write_text(
        "# 1 Substitution\n\nUse Oseltamivir J05AH02 as first line.",
        encoding="utf-8",
    )
    [chunk] = chunk_text_file(md)
    assert "J05AH02" in chunk.atc_codes


def test_chunker_handles_empty_directory(tmp_path: Path):
    assert list(chunk_directory(tmp_path)) == []
