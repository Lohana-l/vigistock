"""Tests unitaires pour le validateur RAG : schéma Pydantic + ancrage des citations."""
from __future__ import annotations

from llm.rag.retriever import RetrievedChunk
from llm.rag.validator import (
    Alternative,
    Brief,
    Citation,
    RedistributionCandidate,
    validate_and_ground,
)


def _retrieved(doc: str, page_from: int = 1, page_to: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{doc}#{page_from}",
        document_id=doc,
        section="1 Substitution",
        page_from=page_from,
        page_to=page_to,
        score=0.42,
        text="…",
    )


def _good_payload() -> dict:
    return {
        "alternatives": [
            {
                "name": "Zanamivir",
                "atc":  "J05AH01",
                "posology_note": "10 mg inh BID",
                "citations": [{"doc": "vaxflu_j_substitution.md", "page": 1}],
            }
        ],
        "redistribution_candidates": [
            {"site": "Lyon-Nord", "surplus_doses": 120},
        ],
        "confidence":           "medium",
        "insufficient_context": False,
        "reasoning_brief":      "FDA shortage + 2 suspect lots.",
    }


def test_valid_payload_parses_with_no_warnings():
    retrieved = [_retrieved("vaxflu_j_substitution.md")]
    brief, warnings = validate_and_ground(_good_payload(), retrieved)
    assert isinstance(brief, Brief)
    assert brief.confidence == "medium"
    assert len(brief.alternatives) == 1
    assert warnings == []


def test_citation_not_in_retrieval_yields_warning():
    retrieved = [_retrieved("other.md")]
    brief, warnings = validate_and_ground(_good_payload(), retrieved)
    assert any("vaxflu_j_substitution.md" in w for w in warnings)
    assert brief.alternatives  # le brief est quand même retourné, c'est l'appelant qui décide


def test_invalid_payload_is_degraded_not_crashed():
    bad = {"alternatives": "not a list"}
    brief, warnings = validate_and_ground(bad, [])
    assert brief.insufficient_context is True
    assert warnings and "schema validation failed" in warnings[0]


def test_citation_multi_page_range_matches():
    # le chunk récupéré couvre les pages 3-5 ; une citation en page 4 doit être acceptée
    retrieved = [_retrieved("proto.md", page_from=3, page_to=5)]
    payload = _good_payload()
    payload["alternatives"][0]["citations"] = [{"doc": "proto.md", "page": 4}]
    _, warnings = validate_and_ground(payload, retrieved)
    assert warnings == []


def test_empty_payload_is_valid_defaults():
    brief, warnings = validate_and_ground({}, [])
    assert brief.alternatives == []
    assert brief.redistribution_candidates == []
    assert warnings == []


def test_models_constructable_directly():
    # contrôle de base : les modèles Pydantic acceptent leurs champs documentés
    c = Citation(doc="x.md", page=2)
    a = Alternative(name="Foo", atc="J01CA04", citations=[c])
    r = RedistributionCandidate(site="Paris-Sud", surplus_doses=50)
    assert a.citations[0].page == 2
    assert r.surplus_doses == 50
