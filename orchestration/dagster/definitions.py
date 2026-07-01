"""Point d'entrée Dagster : assets + planifications + capteurs + checks assemblés."""
from dagster import Definitions, load_assets_from_modules

from orchestration.dagster.assets import ingest, ml_assets, rag_assets
from orchestration.dagster.checks import data_quality_checks
from orchestration.dagster.schedules import daily_schedule, weekly_backtest_schedule
from orchestration.dagster.sensors import alert_to_forecast_sensor

all_assets = load_assets_from_modules([ingest, ml_assets, rag_assets])

defs = Definitions(
    assets=all_assets,
    asset_checks=data_quality_checks,
    schedules=[daily_schedule, weekly_backtest_schedule],
    sensors=[alert_to_forecast_sensor],
)
