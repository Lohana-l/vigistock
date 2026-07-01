"""Paramètres centralisés pour les modules ingestion, streaming et LLM."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Chargé une seule fois depuis .env via pydantic-settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- TimescaleDB ---
    timescale_host:     str = "timescaledb"
    timescale_port:     int = 5432
    timescale_db:       str = "vigistock"
    timescale_user:     str = "vigistock"
    timescale_password: str = "change-me"

    # --- Redpanda ---
    redpanda_brokers:           str = "redpanda:9092"
    redpanda_topic_telemetry:   str = "coldchain.telemetry"
    redpanda_topic_alerts:      str = "coldchain.alerts"

    # --- MinIO ---
    minio_endpoint:           str = "http://minio:9000"
    minio_access_key:         str = "minioadmin"
    minio_secret_key:         str = "minioadmin"
    minio_bucket_protocols:   str = "protocols"

    # --- Ollama / Chroma ---
    ollama_host:        str = "http://ollama:11434"
    ollama_model:       str = "phi3:mini"
    ollama_embed_model: str = "bge-small-en"
    ollama_temperature: float = 0.2
    chroma_host:        str = "chromadb"
    chroma_port:        int = 8000
    chroma_collection:  str = "clinical_protocols"

    # --- APIs publiques ---
    fda_shortages_url:    str = "https://api.fda.gov/drug/shortages.json"
    openfda_url:          str = "https://api.fda.gov/drug/label.json"
    ansm_rss_url:         str = "https://ansm.sante.fr/actualites.rss"
    openprescribing_url:  str = "https://openprescribing.net/api/1.0"

    # --- Drapeaux comportement ---
    use_synthetic_fallback:    bool = True
    simulator_sites:           int  = 8
    simulator_fridges_per_site: int = 6
    simulator_tick_seconds:    int  = 30

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.timescale_user}:{self.timescale_password}"
            f"@{self.timescale_host}:{self.timescale_port}/{self.timescale_db}"
        )


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
