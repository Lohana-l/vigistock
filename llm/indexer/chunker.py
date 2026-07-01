"""
Découpage de PDFs de protocoles cliniques en chunks.

On utilise pypdf pour l'extraction tenant compte de la mise en page, et on découpe
en chunks d'environ 800 tokens avec un chevauchement de 100 tokens, en préférant
les limites de section / titre quand elles existent.
Chaque chunk porte des métadonnées qui permettent de citer des numéros de page exacts plus tard.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from pypdf import PdfReader

CHUNK_TOKENS = 800
OVERLAP_TOKENS = 100


@dataclass
class Chunk:
    document_id: str
    section:     str
    page_from:   int
    page_to:     int
    text:        str
    atc_codes:   list[str]


_HEADING_RE = re.compile(r"^\s*\d+(\.\d+)*\s+[A-Z][^\n]{3,80}$", re.MULTILINE)
_ATC_RE     = re.compile(r"\b([A-Z]\d{2}[A-Z]{2}\d{1,2})\b")


def _approx_tokens(text: str) -> int:
    """1 token ≈ 0,75 mots ; suffisamment précis pour les heuristiques de découpage."""
    return int(len(text.split()) / 0.75)


def _extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]


def _detect_section(text: str) -> str:
    m = _HEADING_RE.search(text)
    return m.group(0).strip() if m else "-"


def chunk_document(pdf_path: Path, document_id: str | None = None) -> list[Chunk]:
    if pdf_path.suffix.lower() != ".pdf":
        # On autorise les seeds Markdown pour que la démo fonctionne sans vrais PDFs.
        return chunk_text_file(pdf_path, document_id=document_id)

    pages = _extract_pages(pdf_path)
    return _chunk_pages(pages, document_id or pdf_path.stem)


def chunk_text_file(path: Path, document_id: str | None = None) -> list[Chunk]:
    pages = [(1, path.read_text())]
    return _chunk_pages(pages, document_id or path.stem)


def _chunk_pages(pages: list[tuple[int, str]], doc_id: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_pages: list[int] = []
    buf_section = "-"

    def _flush(start_page: int, end_page: int) -> None:
        if not buf:
            return
        body = "\n".join(buf).strip()
        if not body:
            return
        chunks.append(Chunk(
            document_id=doc_id,
            section=buf_section,
            page_from=start_page,
            page_to=end_page,
            text=body,
            atc_codes=sorted(set(_ATC_RE.findall(body))),
        ))

    for page_num, text in pages:
        section = _detect_section(text) or buf_section
        if section != buf_section and buf:
            _flush(min(buf_pages), max(buf_pages))
            buf, buf_pages = [], []
        buf_section = section
        buf.append(text)
        buf_pages.append(page_num)

        if _approx_tokens("\n".join(buf)) >= CHUNK_TOKENS:
            _flush(min(buf_pages), max(buf_pages))
            # transporter le chevauchement
            overlap = "\n".join(buf)[-OVERLAP_TOKENS * 5:]   # ~5 chars/token
            buf, buf_pages = [overlap], [page_num]

    _flush(min(buf_pages) if buf_pages else 1,
           max(buf_pages) if buf_pages else 1)
    logger.debug(f"{doc_id}: produced {len(chunks)} chunks")
    return chunks


def chunk_directory(dir_path: Path) -> Iterable[Chunk]:
    for f in sorted(dir_path.rglob("*")):
        if f.suffix.lower() in (".pdf", ".md", ".txt"):
            yield from chunk_document(f)
