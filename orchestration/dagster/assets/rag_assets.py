"""Assets RAG : rafraîchissement de l'index ChromaDB."""
from pathlib import Path

from dagster import AssetExecutionContext, MetadataValue, asset

from llm.indexer.chunker import chunk_directory

PROTOCOL_DIR = Path("protocols/seed")


@asset(
    group_name="rag",
    description="Rafraîchit la collection ChromaDB des chunks de protocoles cliniques.",
    compute_kind="chromadb",
)
def rag_index(context: AssetExecutionContext) -> int:
    """
    On invoque l'indexeur CLI de façon programmatique plutôt que de dupliquer la
    logique ici : le point d'entrée utilisé en CI / dev local reste identique à
    celui planifié dans Dagster.
    """
    from click.testing import CliRunner

    from llm.indexer.run import main

    runner = CliRunner()
    result = runner.invoke(main, ["--source", str(PROTOCOL_DIR), "--reset"])
    if result.exit_code != 0:
        raise RuntimeError(f"indexer failed: {result.output}")

    n_chunks = sum(1 for _ in chunk_directory(PROTOCOL_DIR))
    context.add_output_metadata({"chunks": MetadataValue.int(n_chunks)})
    return n_chunks
