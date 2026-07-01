"""Réfrigérateurs : inventaire complet de la flotte avec drill-down.

Intention UX
------------
Liste dense, filtres rapides, détail zoomable, layout *maître/détail* :

* **Barre de filtres en haut** : site + état + tri, sur une seule ligne.
* **Grille maître** : chaque frigo en tuile, triée par criticité pour que
  l'œil tombe sur ce qui compte sans défiler.
* **Panneau de détail** : 24 h de température avec bandes de tolérance,
  lots affectés, action de quarantaine, et le pont causal excursion vers
  rupture (§8) quand le frigo est en alerte.

Langage : libellés humains partout, le seuil technique passe en infobulle.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import components as C
from lib.data import M
from lib.theme import (
    TEMP_CRIT_HIGH,
    TEMP_OK_HIGH,
    TEMP_OK_LOW,
    TOK,
    fridge_state,
    state_label,
)

# ---------------------------------------------------------------------------
# En-tête de page
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Pilotage : chaîne du froid",
    icon="fridge",
    title="Réfrigérateurs",
    subtitle="L'état de chaque réfrigérateur du réseau, les plus urgents d'abord.",
    tip=(
        "Zone de sécurité 2-8 °C (référence OMS PQS E003). "
        "Au-delà de 8 °C : à surveiller. Au-delà de 10 °C : critique, "
        "le lot doit être contrôlé."
    ),
)


# ---------------------------------------------------------------------------
# Barre de filtres (conservée : Site / État / Tri)
# ---------------------------------------------------------------------------
fleet = M.fleet_snapshot()
sites = ["Tous les sites", *sorted({f["site"] for f in fleet})]

# Filtres dans un panneau-carte : la zone de commande est identifiable
# d'un coup d'œil (clé "panel_*" : surface carte, voir style.py).
with st.container(key="panel_filtres_frigos"):
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 1])

    with f_col1:
        site = st.selectbox("Site", sites, index=0)
    with f_col2:
        state_filter = st.multiselect(
            "État", ["ok", "warn", "crit"], default=["warn", "crit"],
            format_func=state_label,
        )
    with f_col3:
        sort_by = st.selectbox(
            "Tri", ["Criticité (déc.)", "Température (déc.)", "ID frigo"],
        )
    with f_col4:
        st.write("")
        st.write("")
        if st.button("Rafraîchir", use_container_width=True):
            st.rerun()


# Application des filtres
filtered = [f for f in fleet if site == "Tous les sites" or f["site"] == site]
if state_filter:
    filtered = [f for f in filtered if fridge_state(f["temp_c"]) in state_filter]

# Application du tri
if sort_by == "Criticité (déc.)":
    rank = {"crit": 0, "warn": 1, "ok": 2}
    filtered.sort(key=lambda f: (rank[fridge_state(f["temp_c"])], -f["temp_c"]))
elif sort_by == "Température (déc.)":
    filtered.sort(key=lambda f: -f["temp_c"])
else:
    filtered.sort(key=lambda f: f["fridge_id"])


# ---------------------------------------------------------------------------
# Ligne de compteurs (bord supérieur sémantique)
# ---------------------------------------------------------------------------
counts = {"ok": 0, "warn": 0, "crit": 0}
for f in filtered:
    counts[fridge_state(f["temp_c"])] += 1

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    C.kpi_card(label="Frigos affichés", value=len(filtered), icon="fridge",
               trend=f"sur {len({f['site'] for f in filtered})} sites")
with c2:
    # Chiffre par défaut si tous les frigos affichés sont en zone,
    # ambre sinon (y compris 0 en zone).
    _ok_tone = ("ok" if filtered and counts["ok"] == len(filtered) else "warn")
    C.kpi_card(label="OK", value=counts["ok"], icon="check-circle",
               tone=_ok_tone,
               trend="dans la zone de sécurité 2-8 °C")
with c3:
    C.kpi_card(label="À surveiller", value=counts["warn"], icon="alert-triangle",
               tone="warn" if counts["warn"] else "ok", frame="warn",
               trend="frigos au-dessus de 8 °C")
with c4:
    C.kpi_card(label="Critiques", value=counts["crit"], icon="thermometer",
               tone="crit" if counts["crit"] else "ok", frame="crit",
               trend="frigos au-dessus de 10 °C, lots à contrôler")


# ---------------------------------------------------------------------------
# Layout maître / détail
# ---------------------------------------------------------------------------
# Grille pleine largeur, détail en dessous : plus de colonne orpheline.
with st.container():
    C.section_header(
        "Grille des frigos", icon="fridge",
        subtitle=f"{len(filtered)} résultats",
        right="cliquez sur « Voir le détail 24 h »",
    )

    if "selected_fridge" not in st.session_state:
        st.session_state.selected_fridge = filtered[0]["fridge_id"] if filtered else None

    if not filtered:
        C.callout("Aucun frigo ne correspond aux filtres choisis.")
    else:
        for i in range(0, len(filtered), 3):
            row = st.columns(3, gap="small")
            for col, f in zip(row, filtered[i:i + 3], strict=False):
                with col:
                    clicked = C.fridge_tile(f, on_click_key=f"btn_{f['fridge_id']}")
                    if clicked:
                        st.session_state.selected_fridge = f["fridge_id"]
                        st.rerun()


with st.container():
    sel = st.session_state.get("selected_fridge")
    selected = next((f for f in fleet if f["fridge_id"] == sel), None)

    if not selected:
        C.callout("Sélectionnez un frigo pour ouvrir son détail 24 h.")
    else:
        C.section_header(
            f"Détail du frigo {selected['fridge_id']}", icon="search",
            subtitle=f"{selected['site']}, {selected['lots']} lots actifs",
            right=f"dernier relevé {C.fmt_heure(selected['last_seen'])}",
        )

        # Priorité d'abord : le pont causal excursion vers rupture (§8) est la
        # première chose visible si CE frigo héberge un lot sous tension.
        sel_state = fridge_state(selected["temp_c"])
        _aff_here = next(
            ((atc, a) for atc, a in M.excursion_affected_drugs().items()
             if a["fridge"] == selected["fridge_id"]),
            None,
        )
        if sel_state != "ok" and _aff_here:
            _atc, _aff = _aff_here
            _prob = next((d["shortage_prob"] for d in M.shortage_overview()
                          if d["atc_code"] == _atc), None)
            _prob_txt = (f"<b>risque de rupture : {int(_prob * 100)} %</b>"
                         if _prob else "<b>stock déjà sous tension</b>")
            C.causal_bridge(
                f"Ce frigo stocke le lot {_aff['lot']} ({_aff['doses']} doses) "
                f"qui alimente un stock déjà sous tension : {_prob_txt} sur "
                f"{_aff['drug_name']}."
            )
            with st.container(key="link_bridge_fridge"):
                if st.button("Voir l'impact sur les ruptures",
                             key="btn_bridge_fridge"):
                    st.session_state["forecast_focus"] = _atc
                    st.switch_page("views/03_shortage_forecast.py")

        # Onglets : courbe d'abord, lots & actions à un clic, le panneau
        # de détail tient à l'écran sans défilement.
        tab_temp, tab_lots = st.tabs(["Température 24 h", "Lots & actions"])

        with tab_temp:
            # Graphique 24 h avec bandes de tolérance -------------------------
            history = M.fridge_24h(selected["fridge_id"])
            df = pd.DataFrame(history)
            df["ts"] = pd.to_datetime(df["ts"])

            fig = go.Figure()

            # bande de tolérance 2-8 °C (vert sain)
            fig.add_hrect(y0=TEMP_OK_LOW, y1=TEMP_OK_HIGH,
                          fillcolor="rgba(22, 163, 74, .06)", line_width=0)
            # bande « à surveiller » 8-10 °C (ambre)
            fig.add_hrect(y0=TEMP_OK_HIGH, y1=10,
                          fillcolor="rgba(180, 83, 9, .08)", line_width=0)
            # bande critique >10 °C (rouge)
            fig.add_hrect(y0=10, y1=TEMP_CRIT_HIGH + 1,
                          fillcolor="rgba(220, 38, 38, .07)", line_width=0)

            # Lignes de seuil
            for y, color, dash in [
                (TEMP_OK_LOW, TOK.text_tertiary, "dot"),
                (TEMP_OK_HIGH, TOK.warn, "dash"),
                (10, TOK.crit, "dash"),
            ]:
                fig.add_hline(y=y, line_dash=dash, line_color=color,
                              line_width=1, opacity=0.7)

            fig.add_trace(go.Scatter(
                x=df["ts"], y=df["temp"],
                mode="lines",
                line=dict(color=TOK.brand, width=2),
                fill="tozeroy",
                fillcolor="rgba(15, 118, 110, .06)",
                hovertemplate="%{x|%H:%M}<br><b>%{y:.2f} °C</b><extra></extra>",
                name="Température",
            ))

            fig.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=20, b=20),
                font=dict(family=TOK.font_family, color=TOK.text_secondary, size=11),
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                yaxis=dict(title="°C", gridcolor=TOK.divider,
                           zerolinecolor=TOK.divider, range=[0, 13]),
                xaxis=dict(gridcolor=TOK.divider),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

            # Ligne de mini-stats : une simple ligne de texte, pas des blocs.
            vals = df["temp"].astype(float)
            min_v, max_v, mean_v = vals.min(), vals.max(), vals.mean()
            excursion_minutes = int((vals > TEMP_OK_HIGH).sum() * 5)

            _max_color = ("var(--ms-crit)" if max_v > TEMP_OK_HIGH
                          else "var(--ms-text)")
            _exc_color = ("var(--ms-crit)" if excursion_minutes
                          else "var(--ms-ok)")
            _max_note = (f' <span style="color:var(--ms-crit);font-size:.78rem;">'
                         f'(+{max_v - TEMP_OK_HIGH:.1f} au-dessus du seuil)</span>'
                         if max_v > TEMP_OK_HIGH else "")
            st.markdown(
                f"""
                <div style="display:flex;gap:2.4rem;flex-wrap:wrap;
                            margin:.6rem 0 .2rem;font-size:.9rem;">
                  <div><span style="color:var(--ms-text-3);font-size:.72rem;
                       text-transform:uppercase;letter-spacing:.05em;
                       font-weight:700;">Min (24 h)</span><br/>
                       <b>{min_v:.1f} °C</b></div>
                  <div><span style="color:var(--ms-text-3);font-size:.72rem;
                       text-transform:uppercase;letter-spacing:.05em;
                       font-weight:700;">Max (24 h)</span><br/>
                       <b style="color:{_max_color};">{max_v:.1f} °C</b>{_max_note}</div>
                  <div><span style="color:var(--ms-text-3);font-size:.72rem;
                       text-transform:uppercase;letter-spacing:.05em;
                       font-weight:700;">Moyenne</span><br/>
                       <b>{mean_v:.1f} °C</b></div>
                  <div><span style="color:var(--ms-text-3);font-size:.72rem;
                       text-transform:uppercase;letter-spacing:.05em;
                       font-weight:700;">Hors-tolérance</span><br/>
                       <b style="color:{_exc_color};">{excursion_minutes} min</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab_lots:
            # Lots affectés ----------------------------------------------------
            lots_df = pd.DataFrame([
                {"Lot": f"LOT-{selected['fridge_id']}-{i:03d}",
                 "Médicament": d[0],
                 "ATC": d[1],
                 "Doses": (selected["lots"] * 47) // (i + 1),
                 "Exp.": f"2027-{((i * 3) % 11) + 1:02d}-15"}
                for i, d in enumerate(M.DRUGS[: min(selected["lots"], 4)])
            ])
            st.dataframe(lots_df, hide_index=True, use_container_width=True)

            # Actions ----------------------------------------------------------
            a1, a2 = st.columns(2)
            with a1:
                if st.button("Mettre le lot en quarantaine",
                             use_container_width=True, type="primary",
                             disabled=sel_state == "ok"):
                    st.toast(f"Lots de {selected['fridge_id']} marqués « suspects ».")
            with a2:
                if st.button("Préparer un brief de substitution",
                             use_container_width=True):
                    st.session_state["copilot_drug"] = M.DRUGS[0][0]
                    st.switch_page("views/04_clinical_copilot.py")
