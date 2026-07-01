"""Pipeline RAG complet : alerte + inventaire, puis contexte récupéré, puis brief LLM, puis JSON validé."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from loguru import logger

from ingestion.utils.db import pg_conn
from llm.rag.client import generate_json
from llm.rag.retriever import Retriever
from llm.rag.validator import Brief, validate_and_ground

PROMPT_PATH = Path(__file__).parent / "prompts" / "v1.txt"


def _format_context(chunks) -> str:
    blocks = []
    for c in chunks:
        blocks.append(
            f"[{c.document_id} p.{c.page_from}-{c.page_to}] section: {c.section}\n{c.text}"
        )
    return "\n---\n".join(blocks)


def _format_surplus(rows: list[dict]) -> str:
    if not rows:
        return "(none within 200 km)"
    return "\n".join(f"  • {r['site_id']} - {r['surplus_doses']} doses" for r in rows)


def _surplus_candidates(drug_id: str, exclude_site: str) -> list[dict]:
    """Sites avec du stock positif pour le même médicament : proxy pour la redistribution."""
    sql = """
        SELECT site_id, SUM(doses) AS surplus_doses
        FROM silver.inventory_lots
        WHERE drug_id = %s
          AND site_id <> %s
          AND suspect = FALSE
          AND expires_at > NOW()
        GROUP BY site_id
        HAVING SUM(doses) > 0
        ORDER BY surplus_doses DESC
        LIMIT 5
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (drug_id, exclude_site))
        return [{"site_id": s, "surplus_doses": int(d)} for s, d in cur.fetchall()]


def generate_substitution_brief(
    *,
    alert_id: str,
    drug_id: str,
    drug_name: str,
    site_id: str,
    site_name: str,
    lot_id: str,
    suspect_doses: int,
    days_to_stockout: int,
    severity: str,
) -> Brief:
    retriever = Retriever()
    chunks = retriever.search(
        query=f"clinical substitution for {drug_name} ({drug_id})",
        atc_code=drug_id,
        k=5,
    )

    surplus = _surplus_candidates(drug_id, site_id)
    prompt = PROMPT_PATH.read_text().format(
        drug_name=drug_name,
        atc_code=drug_id,
        lot_id=lot_id,
        suspect_doses=suspect_doses,
        site_name=site_name,
        days_to_stockout=days_to_stockout,
        severity=severity,
        surplus_table=_format_surplus(surplus),
        context_blocks=_format_context(chunks) or "(no context retrieved)",
    )

    payload = generate_json(prompt)
    brief, warnings = validate_and_ground(payload, chunks)
    if warnings:
        logger.warning(f"brief warnings for {alert_id}: {warnings}")

    _persist(alert_id, site_id, drug_id, brief, prompt, [c.chunk_id for c in chunks])
    return brief


def _persist(alert_id: str, site_id: str, drug_id: str, brief: Brief,
             prompt: str, chunk_ids: list[str]) -> None:
    sql = """
        INSERT INTO silver.recommendations
          (rec_id, alert_id, site_id, drug_id, brief, prompt_hash, retrieved_chunks)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
    """
    rec_id = str(uuid.uuid4())
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            rec_id, alert_id, site_id, drug_id,
            brief.model_dump_json(), prompt_hash, chunk_ids,
        ))
