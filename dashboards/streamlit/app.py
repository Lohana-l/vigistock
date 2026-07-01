"""Vigistock : point d'entrée Streamlit.

Architecture
------------
On enregistre les pages via ``st.navigation(..., position="hidden")`` et on
construit le sidebar NOUS-MÊMES avec ``st.page_link``. Pourquoi :

* La navigation native ne permet ni icônes SVG, ni libellé de section coloré
  (la section « Pipeline & données » est identifiée en ambre, c'est validé).
* Les pages restent déclarées en **un seul** endroit, groupées par audience
  humaine (Pilotage, Aide clinique, Pipeline & données, Projet), pas par
  ordre alphabétique du système de fichiers.

Structure du sidebar (validée) :
  EN HAUT   : logo plein (bouclier + flocon) + nom + statut résumé.
  AU MILIEU : navigation par audience, libellés français parlants.
  EN BAS    : statut système uniquement, chip ambre « Mode démo ».
              (À terme : zone réservée à l'identité utilisateur.)
"""
from __future__ import annotations

import streamlit as st
from lib import icons as I
from lib import style
from lib.data import M
from lib.settings import get_settings

# ---------------------------------------------------------------------------
# 1) Page config : doit être le *tout premier* appel Streamlit.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Vigistock",
    page_icon=":material/health_and_safety:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/Lohana-l/vigistock",
        "Report a bug": "https://github.com/Lohana-l/vigistock/issues",
        "About": (
            "**Vigistock** - Suivi de la chaîne du froid, prévision "
            "des ruptures de médicaments et aide clinique pour les pharmacies "
            "hospitalières. Projet portfolio de Lohana Utim, Data Engineer et ex-soignante."
        ),
    },
)


# ---------------------------------------------------------------------------
# 2) Injecter le design system
# ---------------------------------------------------------------------------
style.inject()

s = get_settings()


# ---------------------------------------------------------------------------
# 3) Déclaration des pages : libellés français, groupées par audience humaine.
#    `key` : clé du conteneur (CSS par item) · `icon` : icône SVG (icons.py).
# ---------------------------------------------------------------------------
NAV: list[dict] = [
    {
        "section": "Pilotage", "tone": "brand",
        "items": [
            {"key": "nav_overview",  "icon": "tower",
             "page": st.Page("views/01_overview.py",          title="Vue d'ensemble", default=True)},
            {"key": "nav_fridges",   "icon": "fridge",
             "page": st.Page("views/02_cold_chain.py",        title="Réfrigérateurs")},
            {"key": "nav_forecast",  "icon": "forecast",
             "page": st.Page("views/03_shortage_forecast.py", title="Prévision des ruptures")},
        ],
    },
    {
        "section": "Aide clinique", "tone": "brand",
        "items": [
            {"key": "nav_sbar",      "icon": "file-text",
             "page": st.Page("views/04_clinical_copilot.py",  title="Brief SBAR")},
            {"key": "nav_valid",     "icon": "check-circle",
             "page": st.Page("views/05_validation.py",        title="Validation")},
        ],
    },
    {
        # Section technique identifiée explicitement, label en ambre (validé).
        "section": "Pipeline & données", "tone": "secondary",
        "items": [
            {"key": "nav_archi",     "icon": "pipeline",
             "page": st.Page("views/06_architecture.py",      title="Architecture du pipeline")},
            {"key": "nav_quality",   "icon": "bar-chart",
             "page": st.Page("views/07_data_quality.py",      title="Qualité des données")},
        ],
    },
    {
        "section": "Projet", "tone": "brand",
        "items": [
            {"key": "nav_about",     "icon": "info",
             "page": st.Page("views/08_about.py",             title="À propos / Stack")},
        ],
    },
]

_ALL_PAGES = [it["page"] for grp in NAV for it in grp["items"]]
nav = st.navigation(_ALL_PAGES, position="hidden")


# ---------------------------------------------------------------------------
# 4) CSS par item de nav : icône SVG en masque + état actif.
#    (Généré ici car les clés et icônes sont déclarées ci-dessus.)
# ---------------------------------------------------------------------------
def _nav_css() -> str:
    rules: list[str] = []
    for grp in NAV:
        for it in grp["items"]:
            rules.append(
                f'.st-key-{it["key"]} [data-testid="stPageLink-NavLink"]::before {{'
                f'-webkit-mask-image: {I.css_mask(it["icon"])};'
                f'mask-image: {I.css_mask(it["icon"])};}}'
            )
    return "<style>" + "".join(rules) + "</style>"


st.markdown(_nav_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 5) Sidebar : identité en haut, nav au milieu, statut système en bas.
# ---------------------------------------------------------------------------
with st.sidebar:
    # -- A. EN HAUT : logo plein + nom + statut résumé (pastille verte) ------
    # Compteurs calculés depuis la source réellement servie (live ou mock) :
    # une valeur codée en dur mentirait dès que la flotte change de taille.
    _fleet = M.fleet_snapshot()
    _n_sites = len({f["site"] for f in _fleet})
    st.markdown(
        f"""
        <div class="ms-sidebrand">
          {I.logo(40)}
          <div>
            <div class="name">Vigistock</div>
            <div class="status">
              <span class="dot"></span> Surveillance active : {_n_sites} sites, {len(_fleet)} frigos
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -- B. NAVIGATION groupée par audience ----------------------------------
    # Libellés de section sans icône (validé) : texte seul, l'ambre suffit
    # à identifier la section technique.
    for grp in NAV:
        tone_cls = "ms-navlabel secondary" if grp["tone"] == "secondary" else "ms-navlabel"
        st.markdown(
            f'<div class="{tone_cls}">{grp["section"]}</div>',
            unsafe_allow_html=True,
        )
        for it in grp["items"]:
            with st.container(key=it["key"]):
                st.page_link(it["page"], label=it["page"].title)

    # État actif : fond vert très clair + texte/icône vert primaire + gras.
    _active = next(
        (it["key"] for grp in NAV for it in grp["items"]
         if it["page"].title == nav.title),
        None,
    )
    if _active:
        st.markdown(
            f"<style>.st-key-{_active} {{}}"
            f".st-key-{_active} [data-testid='stPageLink-NavLink'] {{"
            f"background: var(--ms-brand-subtle); color: var(--ms-brand);"
            f"font-weight: 700;}}</style>",
            unsafe_allow_html=True,
        )

    # -- C. EN BAS : statut système uniquement --------------------------------
    # Le chip dit HONNÊTEMENT ce qui est servi : démo / stack live / repli.
    from lib.data import data_mode
    _dm = data_mode()
    _chip_style = ("background:var(--ms-brand-subtle);"
                   "border-color:var(--ms-brand-border);"
                   "color:var(--ms-brand-hover);") if _dm["mode"] == "live" else ""
    _okline_html = (
        f'<div class="okline"><span class="dot"></span>{_dm["okline"]}</div>'
        if _dm.get("okline") else ""
    )
    st.markdown(
        f"""
        <div class="ms-sidefoot">
          <span class="ms-demo-chip" style="{_chip_style}">
            <span class="dot" style="{'background:var(--ms-ok);' if _dm['mode'] == 'live' else ''}"></span>
            {_dm['label']}
          </span>
          {_okline_html}
          <div class="note">{_dm['note']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 6) Lancer la page sélectionnée
# ---------------------------------------------------------------------------
nav.run()
