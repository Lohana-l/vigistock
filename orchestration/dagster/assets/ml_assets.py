"""Assets ML : prévisions de ruptures et backtests walk-forward."""
from dagster import AssetExecutionContext, MetadataValue, asset

from ingestion.utils.db import pg_conn
from ml.shortage_forecast import run as run_forecast

# Plafond de paires backtestées par run : 6 folds Prophet par paire, le
# walk-forward est coûteux. On backteste en priorité les paires les plus à
# risque, ce qui est aussi là où la qualité du modèle compte le plus.
_BACKTEST_MAX_PAIRS = 4


@asset(
    group_name="ml",
    description="Prévision de rupture Prophet par (site, médicament), horizon 30 jours.",
    compute_kind="prophet",
)
def shortage_forecasts(context: AssetExecutionContext) -> int:
    n = run_forecast()
    context.add_output_metadata({
        "forecasts_written": MetadataValue.int(n),
        "horizon_days":      MetadataValue.int(30),
    })
    return n


@asset(
    group_name="ml",
    deps=[shortage_forecasts],
    description=(
        "Backtest walk-forward (MAPE + couverture 80 %) sur les paires les plus "
        "à risque. Alimente silver.forecast_backtests, lu par la page Validation."
    ),
    compute_kind="prophet",
)
def forecast_backtests(context: AssetExecutionContext) -> int:
    """Orchestre ml/backtest.py, qui était écrit mais jamais planifié.

    Les paires sont triées par probabilité de rupture décroissante : on mesure
    la fiabilité du modèle là où ses prévisions déclenchent des décisions.
    """
    from ml.backtest import run as run_backtest

    sql = """
        SELECT site_id, drug_id
        FROM gold.v_forecast_latest
        ORDER BY shortage_prob DESC NULLS LAST
        LIMIT %s
    """
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (_BACKTEST_MAX_PAIRS,))
        pairs = [tuple(r) for r in cur.fetchall()]

    n_rows = 0
    for site_id, drug_id in pairs:
        df = run_backtest(site_id, drug_id)
        n_rows += len(df)

    context.add_output_metadata({
        "pairs_backtested": MetadataValue.int(len(pairs)),
        "fold_rows_written": MetadataValue.int(n_rows),
    })
    return n_rows
