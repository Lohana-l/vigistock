"""Assets d'ingestion : un par source publique."""
from dagster import AssetExecutionContext, MetadataValue, asset

from ingestion.ansm import extractor as ansm
from ingestion.fda import extractor as fda
from ingestion.openfda import extractor as openfda
from ingestion.openprescribing import extractor as op


@asset(
    group_name="ingest",
    description="Jeu de données FDA drug-shortages (rafraîchissement quotidien).",
    compute_kind="python",
)
def fda_shortages(context: AssetExecutionContext) -> int:
    n = fda.run()
    context.add_output_metadata({"rows": MetadataValue.int(n)})
    return n


@asset(
    group_name="ingest",
    deps=[fda_shortages],
    description="Labels SPL openFDA pour les médicaments actuellement en pénurie.",
    compute_kind="python",
)
def openfda_labels(context: AssetExecutionContext) -> int:
    n = openfda.run()
    context.add_output_metadata({"rows": MetadataValue.int(n)})
    return n


@asset(
    group_name="ingest",
    description="Signalements RSS ANSM (France).",
    compute_kind="python",
)
def ansm_signalements(context: AssetExecutionContext) -> int:
    n = ansm.run()
    context.add_output_metadata({"rows": MetadataValue.int(n)})
    return n


@asset(
    group_name="ingest",
    description="Volumes de prescription GP OpenPrescribing.net UK (CC-BY).",
    compute_kind="python",
)
def openprescribing_usage(context: AssetExecutionContext) -> int:
    n = op.run()
    context.add_output_metadata({"rows": MetadataValue.int(n)})
    return n
