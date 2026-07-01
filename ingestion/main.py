"""CLI principale pour l'ingestion batch.

Usage :
    python -m ingestion.main --all
    python -m ingestion.main --source fda
"""
from __future__ import annotations

import click
from loguru import logger

from ingestion.ansm import extractor as ansm
from ingestion.fda import extractor as fda
from ingestion.openfda import extractor as openfda
from ingestion.openprescribing import extractor as op

EXTRACTORS = {
    "fda":              fda.run,
    "openfda":          openfda.run,
    "ansm":             ansm.run,
    "openprescribing":  op.run,
}


def run_ingest(sources: list[str] | None = None) -> dict[str, int]:
    """Lance les extracteurs demandés. Retourne le nombre de lignes par source."""
    sources = sources or list(EXTRACTORS)
    counts: dict[str, int] = {}
    for s in sources:
        if s not in EXTRACTORS:
            logger.error(f"Unknown source: {s}")
            continue
        try:
            counts[s] = EXTRACTORS[s]()
        except Exception:
            logger.exception(f"{s}: extractor crashed")
            counts[s] = -1
    return counts


@click.command()
@click.option("--all", "all_sources", is_flag=True, help="Run every extractor.")
@click.option("--source", multiple=True, help="Pick one or several sources.")
def main(all_sources: bool, source: tuple[str, ...]) -> None:
    targets = None if (all_sources or not source) else list(source)
    counts = run_ingest(targets)
    for s, n in counts.items():
        logger.info(f"  {s:20s} {n:>6} rows")


if __name__ == "__main__":
    main()
