"""Architecture du pipeline : la page où tout le vocabulaire technique vit.

Intention UX
------------
C'est ICI que la fierté technique s'exprime (Redpanda, TimescaleDB, Prophet,
Dagster, ChromaDB, hypertables…). Le jargon y est légitime et valorisant,
et il ne déborde pas sur les pages cliniques.

Layout :
* Un diagramme de pipeline organisé de gauche à droite (sens du flux),
  six étages : Sense, Stream, Store, Forecast, Reason, Act.
* Des onglets pour le deep-dive sur chaque étage.
* Un tableau de mapping cloud : l'équivalent managé de chaque choix OSS.
"""
from __future__ import annotations

import streamlit as st
from lib import components as C
from lib import icons as I

# ---------------------------------------------------------------------------
# En-tête de page (ton ambre : section Pipeline & données)
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Pipeline & données",
    icon="pipeline",
    tone="secondary",
    title="Architecture du pipeline",
    subtitle=(
        "Pipeline temps réel, 100 % open source, pensé pour tourner sur un "
        "MacBook M1 8 Go et se rebrancher en un changement de config sur "
        "AWS / GCP / Azure."
    ),
)


# ---------------------------------------------------------------------------
# Diagramme pipeline : 6 nœuds de gauche à droite, flèches SVG
# ---------------------------------------------------------------------------
C.section_header(
    "Le pipeline", icon="pipeline", tone="secondary",
    subtitle="de la sonde frigo à la décision pharmacien",
)

_NODES = [
    ("thermometer", "Sense",    "SimPy + Python"),
    ("zap",         "Stream",   "Redpanda (Kafka API)"),
    ("database",    "Store",    "TimescaleDB"),
    ("forecast",    "Forecast", "Prophet + Dagster"),
    ("chip",        "Reason",   "Ollama + ChromaDB"),
    ("file-text",   "Act",      "Streamlit + Grafana"),
]

cols = st.columns([1, .15, 1, .15, 1, .15, 1, .15, 1, .15, 1], gap="small")
for i, (icon, title, tech) in enumerate(_NODES):
    with cols[i * 2]:
        C.pipeline_node(icon=icon, title=title, tech=tech)
    if i < len(_NODES) - 1:
        with cols[i * 2 + 1]:
            C.pipeline_arrow()


# Bandeau orchestration transversale (Dagster)
st.markdown(
    f"""
    <div style="margin-top:1rem;background:#FFFFFF;
                border:1px dashed var(--ms-secondary-border);
                border-radius:var(--ms-radius-md);padding:.75rem 1rem;
                display:flex;justify-content:space-between;align-items:center;gap:.75rem;">
      <div style="display:flex;align-items:flex-start;gap:.55rem;
                  color:var(--ms-text-2);font-size:.875rem;">
        <span style="color:var(--ms-secondary);margin-top:2px;">{I.icon('pipeline', size=16)}</span>
        <span><strong>Orchestration transversale</strong> : Dagster
        software-defined assets : un graphe unique pilote ingestion batch,
        retraining ML et ré-indexation RAG. Asset checks Dagster = data
        quality continue.</span>
      </div>
      <span class="ms-pill warn"><span class="dot"></span>Dagster</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Onglets de deep-dive
# ---------------------------------------------------------------------------
C.section_header("Tout le détail technique", icon="search", tone="secondary",
                 subtitle="choix par étage, équivalences cloud, organisation du dépôt")

t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "Sense + Stream", "Store", "Forecast", "Reason (RAG + LLM)", "Act",
    "Multi-cloud", "Dépôt",
])

with t1:
    st.markdown(
        """
        ### Sense - IoT simulator (SimPy)
        - `simulator/` produit un signal réaliste (8 sites × 6 frigos = 48)
          avec pannes probabilistes, incident scripté et bruit gaussien.
        - Sortie : événements Kafka JSON `coldchain.telemetry` à 30 s
          (producteur : `simulator/run.py`).

        ### Stream - Redpanda + consumer Python
        - `streaming/consumer.py` : détection d'anomalie en vol
          (`streaming/anomaly.py`, seuils de durée hors zone 2-8 °C :
          30 min WARN, 2 h BREAKAGE_RISK, 4 h CRITICAL). Émet le miroir
          sur `coldchain.alerts` et marque les lots suspects.
        - Idempotence : alertes upsertées sur clé fonctionnelle
          (frigo + horodatage d'ouverture), commit d'offset après écriture.
        - À l'arrêt brutal : Redpanda rejoue, le consumer est at-least-once.
        """
    )

with t2:
    st.markdown(
        """
        ### Store - TimescaleDB (Postgres extension)
        - Hypertables `silver.telemetry_raw` (chunks 1 j) et
          `silver.alerts` (chunks 30 j).
        - Continuous aggregate `silver.telemetry_5m`, rafraîchi chaque minute.
        - `silver.forecasts` + `gold.forecast_points` matérialisent les
          prévisions Prophet ; vues `gold.v_*` consommées par l'UI.
        - Retention policy : télémétrie brute purgée à 90 j.

        **Pourquoi Timescale ?**
        Postgres : pas de nouveau dialecte SQL à apprendre, transactions ACID,
        hypertables = la seule extension qui combine compression columnar +
        continuous aggregates sans casser le contrat SQL.
        """
    )

with t3:
    st.markdown(
        """
        ### Forecast - Prophet sur Dagster
        - `ml/shortage_forecast.py` : un modèle Prophet par
          (site, médicament), saisonnalités hebdomadaire + annuelle,
          boosté par les signaux pénurie FDA / ANSM.
        - Réentraînement nocturne (schedule Dagster) + capteur qui
          rematérialise la prévision dès qu'une alerte BREAKAGE_RISK tombe.
        - Backtest walk-forward (6 folds de 15 j) hebdomadaire : MAPE et
          couverture 80 % écrits dans `silver.forecast_backtests`.

        **Outputs**
        - `silver.forecasts` (résumé par run) et `gold.forecast_points`
          (trajectoire quotidienne : médiane + bande de confiance 80 %).
        """
    )

with t4:
    st.markdown(
        """
        ### Reason - RAG + LLM local
        - `llm/indexer/run.py` : extraction + chunking (~800 tokens,
          chevauchement 100) + métadonnées ATC vers ChromaDB.
        - `llm/rag/` : retrieve top-5 (pré-filtre par code ATC), puis
          prompt SBAR, puis Ollama en mode JSON.
        - Validation d'ancrage (`llm/rag/validator.py`) : chaque citation
          `[doc:page]` doit référencer un chunk réellement récupéré,
          sinon le brief est dégradé avec avertissement.

        **Pourquoi local ?**
        Aucun PHI ne sort du périmètre. La compliance HIPAA / RGPD
        devient un argument commercial et non un frein.
        """
    )

with t5:
    st.markdown(
        """
        ### Act - Streamlit + Grafana
        - **Streamlit** : surface décisionnelle pour les pharmaciens
          (cette app). Multipages + ``st.fragment`` pour les zones live.
        - **Grafana** : surface ops temps réel (frigos, lag Kafka,
          latence requêtes). Alerting sur excursions et lag.
        - **Dagster UI** : surface engineering (asset graph, runs).

        Chaque surface a un public différent. La même donnée (Timescale)
        nourrit les trois.
        """
    )


# ---------------------------------------------------------------------------
# Onglet : mapping multi-cloud
# ---------------------------------------------------------------------------
with t6:
    st.caption("Chaque choix OSS a une équivalence managée : "
               "un changement de config, pas de réécriture.")

    import pandas as pd
    mapping = pd.DataFrame([
        ("Streaming bus",        "Redpanda (Kafka API)",     "Amazon MSK",
            "Confluent Cloud",            "Azure Event Hubs"),
        ("Time-series DB",       "TimescaleDB",              "Amazon Timestream",
            "GCP Bigtable",               "Azure Data Explorer"),
        ("Object store",         "MinIO",                    "Amazon S3",
            "Google Cloud Storage",       "Azure Blob"),
        ("Orchestrator",         "Dagster",                  "Dagster Cloud / MWAA",
            "Cloud Composer",             "Azure Data Factory"),
        ("Forecasting",          "Prophet (Python)",         "SageMaker Forecast",
            "Vertex AI Forecast",         "Azure ML Forecast"),
        ("LLM",                  "Ollama (phi3:mini)",       "Bedrock (Claude)",
            "Vertex AI (Gemini)",         "Azure OpenAI"),
        ("Vector store",         "ChromaDB",                 "OpenSearch + KNN",
            "pgvector / Vertex",          "Azure AI Search"),
        ("Embeddings",           "bge-small-en",             "Bedrock Titan",
            "text-embedding-005",         "Azure OpenAI Embeddings"),
        ("Real-time dashboards", "Grafana",                  "Managed Grafana",
            "Cloud Monitoring",           "Azure Monitor"),
        ("App layer",            "Streamlit",                "App Runner",
            "Cloud Run",                  "Azure Container Apps"),
    ], columns=["Layer", "OSS choice", "AWS", "GCP", "Azure"])

    st.dataframe(mapping, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Onglet : organisation du dépôt
# ---------------------------------------------------------------------------
with t7:
    st.caption("Où vit chaque composant dans le dépôt.")

    st.code(
        """vigistock/
├── dashboards/streamlit/    # cette app (UI pharmacien)
├── docs/                    # architecture, sources de données, gouvernance
├── ingestion/               # FDA, openFDA, ANSM, OpenPrescribing (batch)
├── simulator/               # SimPy cold-chain generator vers Redpanda
├── streaming/               # producer + consumer + anomaly detection
├── ml/                      # Prophet, backtests, metrics
├── llm/                     # RAG : chunking, indexer, prompt template
├── orchestration/dagster/   # @asset definitions, schedules, sensors
├── sql/                     # Timescale DDL, hypertables, materialized
├── infra/                   # Dockerfiles, terraform (cloud version)
├── docker-compose.yml       # full local stack
└── Makefile                 # `make help` pour tout enchaîner
""",
        language="text",
    )
