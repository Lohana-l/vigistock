"""Qualité des données : asset checks Dagster + santé du pipeline.

Intention UX
------------
Page de la section « Pipeline & données » : le vocabulaire technique y est
légitime. Elle expose les asset-checks que le pipeline exécute en continu,
pour vérifier en un regard que la couche données est observée, pas juste
livrée.

Layout
------
1. Bande KPI : comptages pass / warn / fail + jauge de fraîcheur.
2. Tableau asset-checks : filtrable par asset + sévérité.
3. Runs Dagster récents : petite liste avec durée et statut.
4. Mini-graphe de drift d'embeddings pour le corpus RAG : ferme la boucle
   côté LLM.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import components as C
from lib.data import M
from lib.theme import TOK

# ---------------------------------------------------------------------------
# En-tête (ton ambre : section Pipeline & données)
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Pipeline & données",
    icon="bar-chart",
    tone="secondary",
    title="Qualité des données",
    subtitle=(
        "Les contrôles automatiques qui vérifient en continu que les données "
        "du pipeline sont fiables : fraîcheur, schéma, volumes, dérive. "
        "Si la qualité dégrade, le pipeline ne livre pas : il alerte."
    ),
)


# ---------------------------------------------------------------------------
# Bande KPI
# ---------------------------------------------------------------------------
checks = M.asset_checks()
p = sum(1 for c in checks if c["result"] == "pass")
w = sum(1 for c in checks if c["result"] == "warn")
f = sum(1 for c in checks if c["result"] == "fail")
score = round(100 * p / max(1, len(checks)))

# Blocs explicites : on dit DE QUOI on parle (contrôles automatiques de
# qualité des données), pas un chiffre hors contexte.
c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    C.kpi_card(label="Contrôles réussis", value=p, icon="check-circle",
               tone="ok" if p == len(checks) else "warn",
               trend=f"sur {len(checks)} contrôles automatiques de qualité "
                     f"des données ({score} %)")
with c2:
    C.kpi_card(label="À investiguer", value=w, icon="alert-triangle",
               tone="warn" if w else "ok", frame="warn",
               trend="contrôle(s) signalant une dérive, à vérifier dans la journée")
with c3:
    C.kpi_card(label="En échec", value=f, icon="x-circle",
               tone="crit" if f else "ok", frame="warn",
               trend="contrôle(s) bloquant la mise à jour des données en aval")
with c4:
    C.kpi_card(label="Dernière donnée reçue",
               value=M.telemetry_freshness(),
               icon="clock", tone="ok",
               trend="âge de la dernière mesure, objectif : moins de 5 minutes")


# ---------------------------------------------------------------------------
# Tableau des asset-checks
# ---------------------------------------------------------------------------
from lib.data import data_mode

# Provenance honnête : « live » seulement si le webserver Dagster répond
# vraiment, pas seulement la base (les contrôles affichés restent le mock sinon).
_dagster_up = (data_mode()["mode"] == "live"
               and getattr(M, "dagster_available", lambda: False)())
_src = "live (webserver Dagster)" if _dagster_up else "valeurs de démonstration"

# ---------------------------------------------------------------------------
# Onglets : la page tient à l'écran, chaque volet à un clic.
# ---------------------------------------------------------------------------
tab_checks, tab_runs, tab_drift = st.tabs(
    ["Contrôles automatiques", "Runs Dagster", "Drift RAG"])


with tab_checks:
    C.section_header(
        "Contrôles automatiques", icon="check-circle", tone="secondary",
        subtitle="chaque table de données a ses contrôles, exécutés à chaque run Dagster",
        right=_src,
    )

    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        assets = sorted({c["asset"] for c in checks})
        asset_filter = st.multiselect("Tables de données", assets, default=assets)
    with filter_col2:
        severity_filter = st.multiselect(
            "Résultat", ["pass", "warn", "fail"],
            default=["pass", "warn", "fail"], format_func=str.upper,
        )

    filtered = [c for c in checks
                if c["asset"] in asset_filter and c["result"] in severity_filter]

    df = pd.DataFrame(filtered)
    df["Statut"] = df["result"].map({"pass": "PASS", "warn": "WARN", "fail": "FAIL"})
    df = df.rename(columns={
        "asset":     "Table de données",
        "check":     "Contrôle automatique",
        "value":     "Valeur observée",
        "last_run":  "Dernier run",
    })[["Table de données", "Contrôle automatique", "Statut", "Valeur observée", "Dernier run"]]

    st.dataframe(df, hide_index=True, use_container_width=True)


with tab_runs:
    C.section_header("Runs Dagster récents", icon="refresh", tone="secondary",
                     right=_src)

    runs = M.dagster_runs()
    cols = st.columns(len(runs), gap="small")
    for col, r in zip(cols, runs, strict=False):
        state = "ok" if r["status"] == "ok" else ("warn" if r["status"] == "warn" else "crit")
        mins, secs = divmod(r["duration_s"], 60)
        duration = (f"{mins // 60}h {mins % 60:02d}m" if mins >= 60
                    else f"{mins} min {secs:02d}")
        with col:
            st.markdown(
                f"""
                <div class="ms-tile {state}">
                  <div class="ms-tile-id">{r['job']}</div>
                  <div style="display:flex;justify-content:flex-end;align-items:flex-end;
                              margin-top:.45rem;">
                    <span class="ms-pill {state}"><span class="dot"></span>{r['status'].upper()}</span>
                  </div>
                  <div class="ms-tile-meta" style="margin-top:.45rem;">
                    <span><b>Durée</b> {duration}</span>
                    <span><b>Début</b> {r['started']}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


with tab_drift:
    C.section_header(
        "Drift d'embeddings (corpus RAG)", icon="activity", tone="secondary",
        subtitle="distance moyenne aux centroïdes par version d'index, seuil d'alerte 0,05",
        right="valeurs de démonstration",
    )

    rng = np.random.default_rng(11)
    days = pd.date_range("2026-05-14", periods=14, freq="D")
    drift = 0.012 + rng.normal(0, .003, size=14).cumsum() * .15
    drift = np.clip(drift, 0.005, 0.055)
    drift[-1] = 0.018  # valeur actuelle

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=0.05,
                  fillcolor="rgba(22, 163, 74, .05)", line_width=0)
    fig.add_hrect(y0=0.05, y1=0.08,
                  fillcolor="rgba(220, 38, 38, .05)", line_width=0)
    fig.add_hline(y=0.05, line_dash="dash", line_color=TOK.alert, line_width=1)

    fig.add_trace(go.Scatter(
        x=days, y=drift,
        mode="lines+markers",
        line=dict(color=TOK.secondary, width=2),
        marker=dict(color=TOK.secondary, size=6,
                    line=dict(color="#FFFFFF", width=1)),
        fill="tozeroy",
        fillcolor="rgba(180, 83, 9, .08)",
        name="drift",
        hovertemplate="%{x|%d %b}<br><b>%{y:.3f}</b><extra></extra>",
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family=TOK.font_family, color=TOK.text_secondary, size=11),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        yaxis=dict(title="Distance moyenne", gridcolor=TOK.divider,
                   zerolinecolor=TOK.divider, range=[0, 0.08]),
        xaxis=dict(gridcolor=TOK.divider),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    C.callout(
        "<strong>Lecture.</strong> Le corpus RAG (protocoles ANSM / OMS / NICE) "
        "dérive lentement à chaque ré-indexation. Tant que la distance moyenne "
        "aux centroïdes reste sous <code>0.05</code>, les requêtes restent "
        "stables. Au-delà, on déclenche un re-rerank fine-tuned.",
        variant="warn",
    )
