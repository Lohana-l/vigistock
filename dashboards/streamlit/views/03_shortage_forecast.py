"""Prévision des ruptures : quel médicament risque de manquer, et quand ?

Intention UX
------------
La page est structurée comme un entonnoir *liste classée puis courbe puis action* :

1. Tableau en haut = classement par risque avec barres de probabilité
   (comparables d'un seul regard) + marqueur « lot affecté par une excursion
   en cours » (pont causal §8, sens rupture vers frigo).
2. Milieu = la courbe du médicament sélectionné : historique + prévision +
   intervalle de confiance 80 %.
3. Bas = explicabilité (stock, consommation, probabilité) + CTA vers le
   brief de substitution.

Langage : mot métier d'abord. La fiabilité du modèle est dite en humain
(« élevée ») et le détail technique (MAPE) passe en infobulle.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import components as C
from lib.data import M
from lib.theme import TOK

_MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{d.day} {_MOIS_FR[d.month - 1]}"


# Médicaments dont un lot est affecté par une excursion EN COURS (§8).
# Dérivé des données : inventaire × alertes ouvertes (live) ou scénario (démo).
_EXCURSION_AFFECTED = M.excursion_affected_drugs()


# ---------------------------------------------------------------------------
# En-tête de page
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Pilotage : prévision",
    icon="forecast",
    title="Prévision des ruptures",
    subtitle=(
        "Quels médicaments risquent de manquer, et quand. Horizon de 14 à "
        "30 jours, fiabilité de prévision élevée."
    ),
    tip=(
        "Le modèle de prévision (Prophet) est réentraîné chaque nuit sur "
        "l'historique de consommation. Sa fiabilité est mesurée chaque "
        "semaine par backtest walk-forward (MAPE et couverture 80 %, "
        "table silver.forecast_backtests)."
    ),
)


# ---------------------------------------------------------------------------
# Barre KPI en haut
# ---------------------------------------------------------------------------
data = M.shortage_overview()
total = len(data)
critical = sum(1 for d in data if d["shortage_prob"] >= 0.6)
warn = sum(1 for d in data if 0.3 <= d["shortage_prob"] < 0.6)
soon = min(d["stockout_date"] for d in data)

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1: C.kpi_card(label="Médicaments suivis", value=total, icon="pill",
                    trend="médicaments sous surveillance de stock")
with c2: C.kpi_card(label="Risque élevé", value=critical, icon="flag",
                    tone="crit" if critical else "ok", frame="warn",
                    trend="probabilité ≥ 60 %, rupture probable sous 14 jours")
with c3: C.kpi_card(label="À surveiller", value=warn, icon="alert-triangle",
                    tone="warn" if warn else "ok", frame="warn",
                    trend="probabilité entre 30 et 60 %")
with c4: C.kpi_card(label="Rupture la plus proche", value=_date_fr(soon),
                    icon="clock", tone="warn",
                    trend="à anticiper dès maintenant")


# ---------------------------------------------------------------------------
# Ligne de filtres (conservée : Sites / Horizon)
# ---------------------------------------------------------------------------
flt_col1, flt_col2 = st.columns([2, 1])
with flt_col1:
    sites = sorted({d["site_id"] for d in data})
    site_sel = st.multiselect("Sites", sites, default=sites)
with flt_col2:
    horizon = st.selectbox("Horizon", ["14 jours", "30 jours"], index=1)

filtered = [d for d in data if d["site_id"] in site_sel]

# ---------------------------------------------------------------------------
# Sélecteur de vue : la page reste courte, chaque vue à un clic.
# (Un radio plutôt que st.tabs : le pont causal d'une page excursion peut
#  ainsi ouvrir DIRECTEMENT la vue « Détail du médicament ».)
# ---------------------------------------------------------------------------
_VIEWS = ["Classement par risque", "Détail du médicament"]

# Pré-filtrage si on arrive depuis le pont causal d'une excursion (§8)
_focus_atc = st.session_state.pop("forecast_focus", None)
if _focus_atc:
    st.session_state["forecast_view"] = _VIEWS[1]
if "forecast_view" not in st.session_state:
    st.session_state["forecast_view"] = _VIEWS[0]

view = st.radio("Vue", _VIEWS, key="forecast_view",
                horizontal=True, label_visibility="collapsed")


# ===========================================================================
# VUE 1 : Classement par risque (avec marqueur d'excursion §8)
# ===========================================================================
if view == _VIEWS[0]:
    C.section_header(
        "Classement par risque", icon="forecast",
        subtitle="la vue « Détail du médicament » trace la courbe de chacun",
    )

    df = pd.DataFrame(filtered)
    df["risque (%)"] = (df["shortage_prob"] * 100).round(0).astype(int)
    df["Chaîne du froid"] = df["atc_code"].map(
        lambda a: "Lot affecté par une excursion en cours"
        if a in _EXCURSION_AFFECTED else "Aucune excursion"
    )
    df = df.rename(columns={
        "drug_name":     "Médicament",
        "atc_code":      "ATC",
        "site_id":       "Site",
        "current_stock": "Stock",
        "stockout_date": "Rupture estimée",
    })[["Médicament", "ATC", "Site", "Stock", "Rupture estimée",
        "Chaîne du froid", "risque (%)"]]

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "risque (%)": st.column_config.ProgressColumn(
                "Probabilité de rupture",
                help="Probabilité de rupture de stock sur l'horizon choisi.",
                format="%d %%",
                min_value=0, max_value=100,
            ),
            "Stock": st.column_config.NumberColumn("Stock actuel", format="%d u."),
            "ATC": st.column_config.TextColumn(width="small"),
            "Chaîne du froid": st.column_config.TextColumn(
                help="Pont avec la surveillance des frigos : un lot de ce "
                     "médicament est-il touché par une excursion de température "
                     "en ce moment ?"),
        },
    )

    # Marqueur réciproque du pont causal : rupture vers frigo concerné (§8)
    affected_in_view = [d for d in filtered if d["atc_code"] in _EXCURSION_AFFECTED]
    if affected_in_view:
        aff = affected_in_view[0]
        exc = _EXCURSION_AFFECTED[aff["atc_code"]]
        C.causal_bridge(
            f"<b>{aff['drug_name']}</b> : le lot {exc['lot']} est affecté par une "
            f"excursion de température en cours ({exc['site']}, frigo "
            f"{exc['fridge']})."
        )
        with st.container(key="link_bridge_forecast"):
            if st.button("Voir le frigo concerné", key="btn_bridge_forecast"):
                st.session_state["selected_fridge"] = exc["fridge"]
                st.switch_page("views/02_cold_chain.py")


# ===========================================================================
# VUE 2 : Détail du médicament (courbe + explicabilité + action)
# ===========================================================================
else:
    C.section_header(
        "Détail du médicament", icon="search",
        subtitle="historique 90 jours, prévision et intervalle de confiance 80 %",
    )

    _choices = [f"{d['drug_name']} ({d['atc_code']})" for d in filtered]
    _default_idx = 0
    if _focus_atc:
        for i, d in enumerate(filtered):
            if d["atc_code"] == _focus_atc:
                _default_idx = i
                break

    drug_pick = st.selectbox("Médicament", _choices, index=_default_idx)
    sel_atc = drug_pick.split("(")[-1].rstrip(")") if drug_pick else "J07BB02"
    sel = next(d for d in filtered if d["atc_code"] == sel_atc)

    curve = M.shortage_forecast_curve(sel_atc, horizon_days=int(horizon.split()[0]))
    hist_df = pd.DataFrame(curve["history"])
    fc_df   = pd.DataFrame(curve["forecast"])
    hist_df["ts"] = pd.to_datetime(hist_df["ts"])
    fc_df["ts"]   = pd.to_datetime(fc_df["ts"])

    # Construction du graphique ----------------------------------------------
    fig = go.Figure()

    # Intervalle de confiance (ambre : la zone d'incertitude « chaude »)
    fig.add_trace(go.Scatter(
        x=fc_df["ts"].tolist() + fc_df["ts"][::-1].tolist(),
        y=fc_df["yhat_upper"].tolist() + fc_df["yhat_lower"][::-1].tolist(),
        fill="toself",
        fillcolor="rgba(180, 83, 9, .12)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        name="Intervalle 80 %",
    ))

    # Stock historique (vert marque)
    fig.add_trace(go.Scatter(
        x=hist_df["ts"], y=hist_df["stock"],
        mode="lines",
        line=dict(color=TOK.brand, width=2),
        name="Historique",
        hovertemplate="%{x|%d %b}<br><b>%{y} unités</b><extra></extra>",
    ))

    # Prévision (ambre pointillé)
    fig.add_trace(go.Scatter(
        x=fc_df["ts"], y=fc_df["yhat"],
        mode="lines",
        line=dict(color=TOK.secondary, width=2, dash="dot"),
        name="Prévision",
        hovertemplate="%{x|%d %b}<br><b>%{y:.0f}</b> (prévision)<extra></extra>",
    ))

    # Marqueur de date de rupture (rouge : strictement critique)
    sodate = pd.to_datetime(sel["stockout_date"])
    fig.add_vline(x=sodate, line_color=TOK.alert, line_dash="dash", line_width=1.5)
    fig.add_annotation(
        x=sodate, y=max(fc_df["yhat_upper"].max(), hist_df["stock"].max()) * 0.95,
        text=f"  Rupture estimée<br>  {_date_fr(sel['stockout_date'])}",
        showarrow=False,
        bgcolor="rgba(220, 38, 38, .07)",
        bordercolor=TOK.alert,
        borderwidth=1,
        font=dict(color="#B91C1C", size=11),
        xanchor="left",
    )

    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family=TOK.font_family, color=TOK.text_secondary, size=11),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-.18, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Stock disponible (unités)",
                   gridcolor=TOK.divider, zerolinecolor=TOK.divider),
        xaxis=dict(gridcolor=TOK.divider),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Ligne d'explicabilité ----------------------------------------------------
    e1, e2, e3 = st.columns(3, gap="small")
    with e1:
        C.kpi_card(label="Stock actuel",
                   value=f"{sel['current_stock']:,} u.".replace(",", " "),
                   icon="package",
                   trend=f"≈ {sel['current_stock'] / sel['daily_demand_mean']:.0f} jours d'autonomie")
    with e2:
        C.kpi_card(label="Consommation / jour",
                   value=f"{sel['daily_demand_mean']:.0f}",
                   icon="activity",
                   trend=f"variabilité ± {sel['daily_demand_std']:.1f}")
    with e3:
        C.kpi_card(label="Probabilité de rupture",
                   value=f"{int(sel['shortage_prob']*100)} %",
                   icon="alert-triangle",
                   tone=("crit" if sel["shortage_prob"] >= 0.6
                         else "warn" if sel["shortage_prob"] >= 0.3 else "ok"),
                   trend=f"sur l'horizon {horizon}")

    # Action recommandée : vers le brief SBAR ----------------------------------
    C.section_header("Action recommandée", icon="file-text")
    C.callout(
        f"Préparer un <strong>brief SBAR de substitution</strong> pour "
        f"<strong>{sel['drug_name']}</strong> : alternatives de même classe, "
        "sites du réseau avec surplus, sources cliniques citées.",
        variant="accent",
    )
    if st.button(f"Préparer le brief pour {sel['drug_name']}",
                 type="primary", use_container_width=True):
        st.session_state["copilot_drug"] = f"{sel['drug_name']}|{sel['atc_code']}"
        st.switch_page("views/04_clinical_copilot.py")
