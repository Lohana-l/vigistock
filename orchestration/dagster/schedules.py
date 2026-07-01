"""Planifications.

* nightly_pipeline : ingestion open data + prévisions Prophet, chaque nuit.
  Le backtest en est exclu : 6 folds Prophet par paire chaque nuit serait
  du gaspillage, la qualité du modèle ne bouge pas à cette fréquence.
* weekly_backtest : backtest walk-forward hebdomadaire, le dimanche matin,
  pour suivre la dérive du MAPE et de la couverture dans le temps.
"""
from dagster import AssetSelection, ScheduleDefinition, define_asset_job

nightly_job = define_asset_job(
    name="nightly_pipeline",
    selection=AssetSelection.groups("ingest", "ml")
    - AssetSelection.keys("forecast_backtests"),
)

daily_schedule = ScheduleDefinition(
    job=nightly_job,
    cron_schedule="15 3 * * *",   # 03:15 Europe/Paris
    execution_timezone="Europe/Paris",
)

weekly_backtest_job = define_asset_job(
    name="weekly_backtest",
    selection=AssetSelection.keys("forecast_backtests"),
)

weekly_backtest_schedule = ScheduleDefinition(
    job=weekly_backtest_job,
    cron_schedule="0 6 * * 0",    # dimanche 06:00 Europe/Paris
    execution_timezone="Europe/Paris",
)
