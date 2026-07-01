"""Tour de contrôle : la page d'accueil.

Intention UX (refonte validée)
------------------------------
L'utilisateur est un humain pressé (pharmacien, soignant). La page n'est plus
un mur de métriques : c'est un FIL D'ACTIONS PRIORISÉ à 3 niveaux de lecture,
à voir et comprendre en 3 secondes :

1. **ACTION** (« À traiter maintenant ») : deux cartes d'alerte hiérarchisées
   qui racontent le problème en langage humain, avec des boutons d'action
   concrets (verbe d'abord) et le pont causal excursion vers rupture (§8).
2. **CONTEXTE** (« En un coup d'œil ») : 3 KPI sobres, bord supérieur coloré
   sémantiquement. Aucun jargon technique.
3. **SANTÉ TECHNIQUE** : une barre fine discrète en bas de page. C'est ici,
   et seulement ici, que la fierté technique s'exprime sur cette page.

Comportement live
-----------------
Les KPI et alertes se rafraîchissent toutes les 15 s via
``st.fragment(run_every=…)`` : seul le fragment se réexécute, la position de
défilement et les widgets restent en place.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from lib import components as C
from lib.data import M
from lib.theme import TOK, fridge_state, state_color

# ---------------------------------------------------------------------------
# Helpers locaux
# ---------------------------------------------------------------------------
_MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(iso: str) -> str:
    """``2026-06-18`` devient ``18 juin``."""
    d = datetime.fromisoformat(iso)
    return f"{d.day} {_MOIS_FR[d.month - 1]}"


# Libellés courts français des médicaments à risque (pour la carte ambre)
_DRUG_SHORT = {
    "Influenza vaccine (inactivated)": "Influenza",
    "Insulin glargine":                "Insuline glargine",
    "Amoxicillin/clavulanate":         "Amoxicilline",
    "MMR vaccine":                     "MMR",
    "Insulin detemir":                 "Insuline détémir",
}


# ---------------------------------------------------------------------------
# En-tête de page : la promesse de l'écran en une phrase
# ---------------------------------------------------------------------------
kpis = M.kpi_snapshot()

C.page_header(
    eyebrow="Pilotage (temps réel)",
    icon="tower",
    title="Vue d'ensemble",
    subtitle=(
        f"{kpis['sites_total']} sites hospitaliers, {kpis['fridges_total']} "
        "réfrigérateurs surveillés en continu. Les actions les plus "
        "urgentes s'affichent en premier."
    ),
)


# ===========================================================================
# NIVEAU 1 (ACTION) : « À traiter maintenant »
# Tout est dérivé des données (alertes, lots affectés, prévisions) :
# en mode live, la carte raconte la VRAIE excursion en cours.
# ===========================================================================
C.section_header("À traiter maintenant", icon="flag", tone="crit")

shortages = M.shortage_overview()
at_risk = [d for d in shortages if d["shortage_prob"] >= 0.3]
nearest = min(d["stockout_date"] for d in shortages) if shortages else None
risk_names = ", ".join(_DRUG_SHORT.get(d["drug_name"], d["drug_name"]) for d in at_risk)

# Alerte critique la plus récente + lot affecté (pont excursion vers rupture)
alerts = M.recent_alerts()
top_crit = next((a for a in alerts if a["level"] == "crit"), None)
affected = M.excursion_affected_drugs()
aff_atc, aff = (next(iter(affected.items())) if affected else (None, None))
# Probabilité de rupture du médicament affecté (lien causal chiffré)
aff_prob = next((d["shortage_prob"] for d in shortages
                 if aff_atc and d["atc_code"] == aff_atc), None)

col_crit, col_warn = st.columns(2, gap="medium")

# -- Carte CRITIQUE : l'excursion en cours, racontée en langage humain -------
with col_crit:
    if top_crit and aff:
        C.alert_card(
            level="crit",
            icon="thermometer",
            title=top_crit["title"].split(" (")[0].strip(),
            body_html=(
                f"<b>{top_crit['site']}</b> : {top_crit['msg']}<br/>"
                f"{aff['doses']} doses de {_DRUG_SHORT.get(aff['drug_name'], aff['drug_name'])} "
                f"menacées (lot {aff['lot']})."
            ),
        )
        # Pont causal excursion vers rupture (§8) : l'histoire centrale du produit.
        prob_txt = (f"<b>risque de rupture : {int(aff_prob * 100)} %</b>"
                    if aff_prob else "<b>stock déjà sous tension</b>")
        C.causal_bridge(
            f"Ce lot alimente un stock déjà sous tension : {prob_txt} sur "
            f"{_DRUG_SHORT.get(aff['drug_name'], aff['drug_name'])}."
        )
        with st.container(key="link_bridge_overview"):
            if st.button("Voir l'impact sur les ruptures", key="btn_bridge_overview"):
                st.session_state["forecast_focus"] = aff_atc
                st.switch_page("views/03_shortage_forecast.py")

        # Boutons d'action concrets : un verbe, une décision.
        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("Mettre le lot en quarantaine", type="primary",
                         use_container_width=True, key="btn_quarantine_overview"):
                st.toast(f"Lot {aff['lot']} marqué « suspect » "
                         f"({aff['doses']} doses bloquées).")
        with a2:
            if st.button("Voir le détail 24 h", use_container_width=True,
                         key="btn_detail_overview"):
                st.session_state["selected_fridge"] = aff["fridge"]
                st.switch_page("views/02_cold_chain.py")
    else:
        C.alert_card(
            level="resolved",
            icon="check-circle",
            title="Aucune excursion critique en cours",
            body_html="Tous les réfrigérateurs sont dans la zone de "
                      "sécurité 2-8 °C.",
        )

# -- Carte À SURVEILLER : ruptures prévues -----------------------------------
with col_warn:
    if at_risk:
        C.alert_card(
            level="warn",
            icon="forecast",
            title=f"{len(at_risk)} médicaments risquent de manquer",
            body_html=(
                f"Prévision sur 14 à 30 jours : {risk_names}.<br/>"
                f"La rupture la plus proche est estimée au "
                f"<b>{_date_fr(nearest)}</b>."
            ),
        )
    else:
        C.alert_card(
            level="resolved",
            icon="forecast",
            title="Aucune rupture prévue",
            body_html="Aucun médicament suivi ne dépasse 30 % de probabilité "
                      "de rupture sur l'horizon 14-30 jours.",
        )
    with st.container(key="amber_open_forecast"):
        if st.button("Ouvrir la prévision des ruptures",
                     use_container_width=True, key="btn_open_forecast"):
            st.switch_page("views/03_shortage_forecast.py")


# ===========================================================================
# NIVEAU 2 (CONTEXTE) : « En un coup d'œil »
# ===========================================================================
C.section_header("L'état du réseau en bref", icon="eye",
                 subtitle="actualisé toutes les 15 secondes")


@st.fragment(run_every=15)
def render_kpis() -> None:
    k = M.kpi_snapshot()
    ok_fridges = k["fridges_total"] - k["open_alerts"]
    C.kpi_strip([
        dict(label="Alertes ouvertes", value=k["open_alerts"], icon="flag",
             tone="crit" if k["critical_alerts"] else "warn" if k["open_alerts"] else "ok",
             frame="warn",
             trend=f"{k['critical_alerts']} critique, {k['warn_alerts']} modérées"),
        dict(label="Lots à vérifier", value=k["suspect_lots"], icon="package",
             tone="warn" if k["suspect_lots"] else "ok", frame="warn",
             trend="en attente de contrôle"),
        dict(label="Réfrigérateurs suivis", value=k["fridges_total"], icon="fridge",
             tone="ok",
             trend=f"{ok_fridges} OK, {k['open_alerts']} en alerte"),
    ])


render_kpis()


# ===========================================================================
# Corps : frigos à surveiller (gauche) · flux d'alertes + services (droite)
# ===========================================================================
left, right = st.columns([2, 1], gap="large")

with left:
    C.section_header(
        "Chaîne du froid", icon="fridge",
        subtitle="frigos urgents, excursions par site",
    )

    @st.fragment(run_every=15)
    def render_critical_fridges() -> None:
        fleet = M.fleet_snapshot()
        ranked = sorted(
            fleet,
            key=lambda f: {"crit": 0, "warn": 1, "ok": 2}[fridge_state(f["temp_c"])],
        )
        attention = [f for f in ranked if fridge_state(f["temp_c"]) != "ok"][:6]
        if not attention:
            C.callout("<strong>Aucun frigo hors-tolérance.</strong> "
                      "Tout le réseau est dans la zone de sécurité 2-8 °C.")
            return
        for i in range(0, len(attention), 3):
            cols = st.columns(3, gap="small")
            for col, f in zip(cols, attention[i:i + 3], strict=False):
                with col:
                    C.fridge_tile(f)

    # Onglets : la page reste courte, chaque vue à un clic.
    tab_fridges, tab_heat = st.tabs(
        ["Réfrigérateurs à surveiller", "Excursions par site (24 h)"])

    with tab_fridges:
        render_critical_fridges()

    with tab_heat:
        st.caption("Minutes hors-tolérance par tranche horaire "
                   "(illustration, scénario de démo).")
        fleet_now = M.fleet_snapshot()
        rng = np.random.default_rng(7)
        sites = list({f["site"] for f in fleet_now})
        hours = [f"{h:02d}h" for h in range(24)]
        matrix = rng.poisson(lam=2.0, size=(len(sites), 24))

        # Pannes plantées du scénario de démo, uniquement si le site existe
        # dans la flotte servie (en live, les noms viennent de la base).
        def _plant(site: str, hour: int, minutes: int) -> None:
            if site in sites:
                matrix[sites.index(site), hour] = minutes

        _plant("CHU Lyon-Sud", 22, 38)
        _plant("CHU Lyon-Sud", 23, 26)
        _plant("CHU Bordeaux Pellegrin", 21, 18)
        _plant("CHU Bordeaux Pellegrin", 22, 42)
        _plant("CHU Lyon-Nord", 14, 11)

        df = pd.DataFrame(matrix, index=sites, columns=hours)
        fig = px.imshow(
            df,
            labels=dict(x="Heure", y="Site", color="min hors-tolérance"),
            # Échelle « chaleur » : du blanc froid à l'ambre puis au rouge.
            color_continuous_scale=[
                [0.00, "#F8FAFC"],
                [0.20, TOK.secondary_subtle],
                [0.55, TOK.secondary],
                [1.00, TOK.alert],
            ],
            aspect="auto",
        )
        fig.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=20),
            coloraxis_colorbar=dict(thickness=10, len=0.8),
            font=dict(family=TOK.font_family, color=TOK.text_secondary, size=12),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
        fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})


with right:
    C.section_header("Activité", icon="activity", subtitle="temps réel")

    @st.fragment(run_every=15)
    def render_alerts_feed() -> None:
        # 3 alertes visibles, le reste derrière « Voir plus » : la colonne
        # reste équilibrée avec celle de gauche.
        alerts = M.recent_alerts()
        for a in alerts[:3]:
            C.feed_item(
                title=a["title"], site=a["site"], msg=a["msg"], ts=a["ts"],
                color=state_color(a["level"]), tech=a.get("tech", ""),
            )
        if len(alerts) > 3:
            # Lien texte (pas un bloc) : bascule l'affichage du reste.
            def _toggle_feed() -> None:
                st.session_state["feed_expanded"] = \
                    not st.session_state.get("feed_expanded", False)

            expanded = st.session_state.get("feed_expanded", False)
            lbl = ("Voir moins" if expanded
                   else f"Voir plus ({len(alerts) - 3} alertes)")
            with st.container(key="link_more_alerts"):
                st.button(lbl, key="btn_more_alerts", on_click=_toggle_feed)
            if expanded:
                for a in alerts[3:]:
                    C.feed_item(
                        title=a["title"], site=a["site"], msg=a["msg"],
                        ts=a["ts"], color=state_color(a["level"]),
                        tech=a.get("tech", ""),
                    )

    _SERVICE_ROLES = {
        "Ollama":      "Génération des briefs",
        "Redpanda":    "Flux de mesures",
        "TimescaleDB": "Base de données",
        "ChromaDB":    "Index documentaire",
        "Dagster":     "Orchestration",
        "Grafana":     "Supervision technique",
    }

    tab_feed, tab_svc = st.tabs(["Flux d'alertes", "État des services"])

    with tab_feed:
        render_alerts_feed()

    with tab_svc:
        for svc in M.services_status():
            role = _SERVICE_ROLES.get(svc["name"], svc["name"])
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:.5rem .75rem;background:var(--ms-bg);
                            border:1px solid var(--ms-border);
                            border-radius:8px;margin-bottom:.35rem;"
                     title="{svc['name']} : {svc['detail']}">
                  <div style="display:flex;align-items:center;gap:.5rem;">
                    <span style="width:8px;height:8px;border-radius:50%;
                                background:{state_color(svc['state'])};"></span>
                    <span style="font-weight:600;color:var(--ms-text);
                                 font-size:.875rem;">{role}</span>
                  </div>
                  <div style="font-size:.72rem;color:var(--ms-text-3);">{svc['name']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ===========================================================================
# Prochaines actions : où voulez-vous aller ?
# ===========================================================================
C.section_header("Prochaines actions", icon="arrow-right",
                 subtitle="où voulez-vous aller ?")

c1, c2, c3 = st.columns(3, gap="small")
with c1:
    if st.button("Voir tous les réfrigérateurs",
                 use_container_width=True, type="primary"):
        st.switch_page("views/02_cold_chain.py")
with c2:
    if st.button("Ouvrir la prévision des ruptures",
                 use_container_width=True, key="btn_next_forecast"):
        st.switch_page("views/03_shortage_forecast.py")
with c3:
    if st.button("Préparer un brief SBAR",
                 use_container_width=True):
        st.switch_page("views/04_clinical_copilot.py")


# ===========================================================================
# NIVEAU 3 (SANTÉ TECHNIQUE) : barre fine discrète, en bas de page.
# ===========================================================================
C.section_header("Pipeline & données", icon="pipeline", tone="secondary")

from lib.data import data_mode

tcol1, tcol2 = st.columns([4, 1.2], gap="small")
with tcol1:
    C.tech_bar(events_per_min=kpis["events_per_min"],
               uptime_pct=kpis["uptime_pct"],
               source_label=data_mode()["label"])
with tcol2:
    st.page_link("views/06_architecture.py", label="Architecture du pipeline")
