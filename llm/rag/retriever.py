"""Retriever ChromaDB : recherche sémantique avec pré-filtrage par code ATC.

Les imports de chromadb et sentence-transformers (qui tire torch, plusieurs
centaines de Mo) sont PARESSEUX : ils n'ont lieu qu'à l'instanciation du
Retriever. Le module reste ainsi importable à coût quasi nul, ce dont
dépendent le validateur (qui n'a besoin que de RetrievedChunk), ses tests
unitaires et le dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from ingestion.config import settings

EMBED_MODEL_LOCAL = "BAAI/bge-small-en-v1.5"


@dataclass
class RetrievedChunk:
    chunk_id:    str
    document_id: str
    section:     str
    page_from:   int
    page_to:     int
    score:       float
    text:        str


class Retriever:
    """Encapsule ChromaDB + sentence-transformers ; une instance par processus."""

    def __init__(self) -> None:
        # Imports différés : voir docstring du module.
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        cfg = settings()
        self._client = chromadb.HttpClient(
            host=cfg.chroma_host,
            port=cfg.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._coll = self._client.get_or_create_collection(cfg.chroma_collection)
        self._embedder = SentenceTransformer(EMBED_MODEL_LOCAL)

    def search(
        self, query: str, k: int = 5, atc_code: str | None = None,
    ) -> list[RetrievedChunk]:
        embedding = self._embedder.encode([query], normalize_embeddings=True).tolist()

        where = None
        if atc_code:
            # Chroma "where" supporte `$contains` pour les recherches sous-chaîne.
            where = {"atc_codes": {"$contains": atc_code}}

        try:
            res = self._coll.query(
                query_embeddings=embedding, n_results=k, where=where,
            )
        except Exception as exc:
            logger.warning(f"Chroma query failed ({exc}); retrying without filter")
            res = self._coll.query(query_embeddings=embedding, n_results=k)

        out: list[RetrievedChunk] = []
        for cid, doc, meta, dist in zip(
            res["ids"][0], res["documents"][0],
            res["metadatas"][0], res["distances"][0], strict=False,
        ):
            out.append(RetrievedChunk(
                chunk_id=cid,
                document_id=meta.get("document_id", "?"),
                section=meta.get("section", "-"),
                page_from=int(meta.get("page_from", 1)),
                page_to=int(meta.get("page_to", 1)),
                score=float(1.0 - dist),  # distance cosinus convertie en similarité
                text=doc,
            ))
        return out
