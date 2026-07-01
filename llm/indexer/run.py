"""
Construction / rafraîchissement de la collection ChromaDB de chunks de protocoles cliniques.

Usage :
    python -m llm.indexer.run --source protocols/seed
    python -m llm.indexer.run --source s3://protocols/*.pdf
"""
from __future__ import annotations

import contextlib
import hashlib
from pathlib import Path

import chromadb
import click
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from sentence_transformers import SentenceTransformer

from ingestion.config import settings
from llm.indexer.chunker import Chunk, chunk_directory

DEFAULT_SOURCE = Path("protocols/seed")
EMBED_MODEL_LOCAL = "BAAI/bge-small-en-v1.5"   # fallback léger, tourne sur CPU


def _chroma_client() -> chromadb.HttpClient:
    cfg = settings()
    return chromadb.HttpClient(
        host=cfg.chroma_host,
        port=cfg.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _embedder():
    """Retourne un callable qui transforme du texte en list[float]."""
    # sentence-transformers local est portable ; en production on basculerait sur
    # les embeddings Ollama (`ollama_embed_model`) : même interface.
    return SentenceTransformer(EMBED_MODEL_LOCAL)


def _chunk_id(c: Chunk) -> str:
    h = hashlib.sha1(
        f"{c.document_id}|{c.page_from}-{c.page_to}|{c.text[:80]}".encode(),
        usedforsecurity=False,
    )
    return h.hexdigest()


@click.command()
@click.option("--source", "-s", default=str(DEFAULT_SOURCE),
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--reset/--keep", default=True,
              help="Supprime la collection avant ré-indexation.")
def main(source: Path, reset: bool) -> None:
    cfg = settings()
    client = _chroma_client()
    name = cfg.chroma_collection

    if reset:
        # La collection peut ne pas exister au premier lancement : non bloquant.
        with contextlib.suppress(Exception):
            client.delete_collection(name)

    coll = client.get_or_create_collection(name=name,
                                           metadata={"hnsw:space": "cosine"})

    chunks = list(chunk_directory(source))
    if not chunks:
        logger.warning(f"no chunks found in {source}")
        return
    logger.info(f"indexing {len(chunks)} chunks into ChromaDB::{name}")

    embedder = _embedder()
    embeddings = embedder.encode(
        [c.text for c in chunks], show_progress_bar=True, normalize_embeddings=True,
    ).tolist()

    coll.upsert(
        ids        =[_chunk_id(c) for c in chunks],
        documents  =[c.text for c in chunks],
        embeddings =embeddings,
        metadatas  =[
            {
                "document_id": c.document_id,
                "section":     c.section,
                "page_from":   c.page_from,
                "page_to":     c.page_to,
                "atc_codes":   ",".join(c.atc_codes) or "",
            }
            for c in chunks
        ],
    )
    logger.success(f"indexed {len(chunks)} chunks")


if __name__ == "__main__":
    main()
