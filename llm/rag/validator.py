"""Schéma Pydantic + vérification d'ancrage pour les briefs LLM."""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from llm.rag.retriever import RetrievedChunk


class Citation(BaseModel):
    doc:  str
    page: int


class Alternative(BaseModel):
    name:          str
    atc:           str
    posology_note: str = ""
    citations:     list[Citation] = Field(default_factory=list)


class RedistributionCandidate(BaseModel):
    site:           str
    surplus_doses:  int


class Brief(BaseModel):
    alternatives:               list[Alternative] = Field(default_factory=list)
    redistribution_candidates:  list[RedistributionCandidate] = Field(default_factory=list)
    confidence:                 str = "low"
    insufficient_context:       bool = False
    reasoning_brief:            str = ""


def validate_and_ground(payload: dict, retrieved: list[RetrievedChunk]) -> tuple[Brief, list[str]]:
    """Parse + vérifie que chaque citation référence bien un chunk récupéré.

    Retourne (brief, warnings). L'appelant décide s'il remonte les warnings.
    """
    warnings: list[str] = []
    try:
        brief = Brief(**payload)
    except ValidationError as exc:
        # Ne pas planter ; retourner un brief dégradé avec un avertissement.
        warnings.append(f"schema validation failed: {exc.errors()[0]['msg']}")
        return Brief(insufficient_context=True), warnings

    pages_by_doc: dict[str, set[int]] = {}
    for ch in retrieved:
        pages_by_doc.setdefault(ch.document_id, set()).update(
            range(ch.page_from, ch.page_to + 1)
        )

    for alt in brief.alternatives:
        for cit in alt.citations:
            if cit.doc not in pages_by_doc or cit.page not in pages_by_doc[cit.doc]:
                warnings.append(
                    f"alternative {alt.name!r} cites unseen ({cit.doc} p.{cit.page})"
                )

    return brief, warnings
