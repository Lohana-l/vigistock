"""Configuration runtime : chargée depuis ``.env``.

Source unique de vérité pour les options dépendantes de l'environnement (hôte LLM,
DSN TimescaleDB, drapeaux mode démo). Pur ``pydantic-settings`` pour que la même
classe soit réutilisable depuis les scripts CLI (``simulator.run`` etc.).
"""
from __future__ import annotations

from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # repli gracieux si pip install pas encore fait
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # --- Serveur ---
    app_name:        str  = "Vigistock"
    app_build:       str  = "v4.0-streamlit"
    debug:           bool = False

    # --- TimescaleDB ---
    timescale_host:     str = "timescaledb"
    timescale_port:     int = 5432
    timescale_db:       str = "vigistock"
    timescale_user:     str = "vigistock"
    timescale_password: str = "vigistock"

    # --- Redpanda ---
    redpanda_brokers:         str = "redpanda:9092"
    redpanda_topic_telemetry: str = "coldchain.telemetry"
    redpanda_topic_alerts:    str = "coldchain.alerts"

    # --- Ollama ---
    ollama_host:        str = "http://ollama:11434"
    ollama_model:       str = "phi3:mini"
    ollama_embed_model: str = "bge-small-en"
    ollama_temperature: float = 0.2
    ollama_timeout_s:   float = 60.0

    # --- ChromaDB ---
    chroma_host:       str = "chromadb"
    chroma_port:       int = 8000
    chroma_collection: str = "clinical_protocols"

    # --- Dagster (webserver GraphQL : runs + asset checks en live) ---
    dagster_graphql_url: str = "http://dagster:3000/graphql"

    # --- Drapeaux démo ---
    # Live par défaut : le pipeline est seedé par db-init et l'UI doit servir
    # les vraies tables. Le repli mock par fonction reste automatique (et
    # loggé) si la base est injoignable : la démo ne casse jamais.
    use_mock_data: bool = False
    use_llm_mock:  bool = True

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.timescale_user}:{self.timescale_password}"
            f"@{self.timescale_host}:{self.timescale_port}/{self.timescale_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
