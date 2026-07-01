"""Couche CSS du design system : transforme le chrome Streamlit par défaut
en une application hospitalière claire, lisible en 3 secondes.

Comment ça fonctionne
---------------------
1. Un bloc ``:root`` de tokens (miroir de ``theme.py``), source unique.
2. Reset du shell Streamlit + masquage des éléments natifs qui dénotent
   (menu « ⋮ », toolbar, décoration) pour un rendu 100 % maîtrisé.
3. Sidebar sur fond vert très clair (identité visuelle) avec une navigation
   custom : état actif = fond vert clair + texte vert primaire + gras.
4. Classes de composants (``.ms-*``) consommées par ``components.py``.

Le CSS reste dans **un** seul fichier pour qu'un designer puisse le modifier
sans toucher au Python.
"""
from __future__ import annotations

import streamlit as st

from .theme import TOK, Status

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  /* Marque (vert sapin) */
  --ms-brand: {TOK.brand};
  --ms-brand-hover: {TOK.brand_hover};
  --ms-brand-subtle: {TOK.brand_subtle};
  --ms-brand-border: {TOK.brand_border};

  /* Secondaire (ambre brûlé) */
  --ms-secondary: {TOK.secondary};
  --ms-secondary-dark: {TOK.secondary_dark};
  --ms-secondary-subtle: {TOK.secondary_subtle};
  --ms-secondary-border: {TOK.secondary_border};

  /* Critique (rouge strict) */
  --ms-alert: {TOK.alert};
  --ms-alert-subtle: {TOK.alert_subtle};
  --ms-alert-border: {TOK.alert_border};

  /* Surfaces */
  --ms-bg: {TOK.bg};
  --ms-bg-muted: {TOK.bg_muted};
  --ms-surface: {TOK.surface};
  --ms-border: {TOK.border};
  --ms-border-strong: {TOK.border_strong};
  --ms-divider: {TOK.divider};

  /* Texte */
  --ms-text: {TOK.text};
  --ms-text-2: {TOK.text_secondary};
  --ms-text-3: {TOK.text_tertiary};

  /* Statut */
  --ms-ok: {TOK.ok};
  --ms-warn: {TOK.warn};
  --ms-crit: {TOK.crit};

  /* Rayons / ombres */
  --ms-radius-sm: {TOK.radius_sm};
  --ms-radius-md: {TOK.radius_md};
  --ms-radius-lg: {TOK.radius_lg};
  --ms-shadow-sm: {TOK.shadow_sm};
  --ms-shadow-md: {TOK.shadow_md};
  --ms-shadow-lg: {TOK.shadow_lg};
}}

/* --------------------------------------------------------------------- *
 * 1) Reset global + masquage du chrome Streamlit natif (rendu maîtrisé)
 * --------------------------------------------------------------------- */
html, body, [class*="css"] {{
  font-family: {TOK.font_family};
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--ms-text);
}}

.stApp {{
  background:
    radial-gradient(1200px 600px at 90% -10%, rgba(15, 118, 110, .05), transparent 60%),
    radial-gradient(900px 500px at -10% 10%, rgba(180, 83, 9, .03), transparent 60%),
    var(--ms-bg);
}}

.main .block-container {{
  max-width: 1440px;
  padding: 1.25rem 2rem 4rem;
}}

/* Masque le pied de page, la status widget, le menu « ⋮ », la toolbar et la
   barre de décoration : rendu production, zéro chrome qui dénote. */
footer, [data-testid="stStatusWidget"] {{ display: none !important; }}
#MainMenu, [data-testid="stMainMenu"] {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}

/* Flèche de collapse du sidebar : discrète, aux couleurs de la marque. */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {{
  color: var(--ms-text-3);
  border-radius: 8px;
}}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover {{
  color: var(--ms-brand);
  background: var(--ms-brand-subtle);
}}

/* Hiérarchie typographique : titre page > en-tête section > titre carte >
   corps > méta. */
h1, .stMarkdown h1 {{
  font-size: 1.875rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--ms-text); margin: 0 0 .25rem 0;
}}
h2, .stMarkdown h2 {{
  font-size: 1.375rem; font-weight: 650; letter-spacing: -0.01em;
  color: var(--ms-text); margin: 1.5rem 0 .5rem 0;
}}
h3, .stMarkdown h3 {{
  font-size: 1.0625rem; font-weight: 600; color: var(--ms-text);
  margin: 1rem 0 .25rem 0;
}}
h5, .stMarkdown h5 {{
  font-size: .9375rem; font-weight: 650; color: var(--ms-text);
}}
.stMarkdown p, .stMarkdown li {{
  color: var(--ms-text-2); line-height: 1.55;
}}

/* --------------------------------------------------------------------- *
 * 2) Sidebar : fond vert très clair (identité visuelle), nav custom.
 * --------------------------------------------------------------------- */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #F0FDFA 0%, #F4F7F9 100%);
  border-right: 1px solid var(--ms-border);
}}
[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}
/* NE PAS forcer display:flex sur le conteneur du sidebar : les éléments
   markdown (libellés de section) se font rétrécir par flex-shrink et
   chevauchent les items de nav. Le flux normal suffit. */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
  gap: 0rem;
}}

/* -- Libellés de section de nav (PILOTAGE, AIDE CLINIQUE…) -------------- */
.ms-navlabel {{
  display: flex; align-items: center; gap: .45rem;
  font-size: .67rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .1em;
  color: var(--ms-text-3);
  /* Streamlit fige la hauteur du conteneur d'élément markdown à
     (hauteur du contenu - 1rem) : tout padding vertical déborde sur
     l'élément suivant. On garde donc le texte sur une ligne de 24 px
     (= la hauteur servie) et on absorbe le delta de 16 px avec un
     padding-bas transparent. pointer-events:none pour que ce débord
     invisible ne vole pas les clics de l'item de nav en dessous. */
  margin: 0; padding: 0 .25rem 16px; line-height: 24px;
  pointer-events: none;
}}
/* L'espacement AU-DESSUS d'un libellé de section passe par la marge du
   conteneur (les marges, elles, sont respectées par le layout Streamlit). */
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.ms-navlabel) {{
  margin-top: 1.4rem;
}}
.ms-navlabel.secondary {{ color: var(--ms-secondary); }}

/* -- Items de nav : st.page_link stylé -------------------------------- */
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
  display: flex; align-items: center; gap: .6rem;
  padding: .55rem .7rem;
  border-radius: var(--ms-radius-md);
  color: var(--ms-text-2);
  font-weight: 500;
  margin-bottom: 4px;
  transition: background .15s ease, color .15s ease;
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {{
  color: inherit !important; font-weight: inherit !important;
  font-size: .875rem; margin: 0; line-height: 1.3;
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{
  background: rgba(15, 118, 110, .08);
  color: var(--ms-brand);
}}
/* Icône SVG de chaque item : masque CSS injecté par app.py (par clé). */
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]::before {{
  content: "";
  width: 17px; height: 17px; flex-shrink: 0;
  background-color: currentColor;
  -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
  -webkit-mask-position: center; mask-position: center;
  -webkit-mask-size: contain; mask-size: contain;
}}
/* État actif (classe ajoutée par app.py sur le conteneur keyé) :
   fond vert très clair + texte/icône vert primaire + gras. */
[data-testid="stSidebar"] .ms-nav-active [data-testid="stPageLink-NavLink"] {{
  background: var(--ms-brand-subtle);
  color: var(--ms-brand);
  font-weight: 700;
}}

/* -- Marque en haut du sidebar ----------------------------------------- */
.ms-sidebrand {{
  display: flex; align-items: center; gap: .65rem;
  padding: .25rem 0 .9rem;
  border-bottom: 1px solid var(--ms-border);
  margin-bottom: .25rem;
}}
.ms-sidebrand .name {{
  font-weight: 800; color: var(--ms-brand);
  letter-spacing: -.01em; font-size: 1.12rem; line-height: 1.2;
}}
.ms-sidebrand .status {{
  display: flex; align-items: center; gap: .35rem;
  font-size: .72rem; color: var(--ms-text-2); margin-top: .15rem;
}}
.ms-sidebrand .status .dot {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ms-ok); flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, .15);
}}

/* -- Pied de sidebar : statut système uniquement ------------------------ */
.ms-sidefoot {{
  border-top: 1px solid var(--ms-border);
  margin: 0; padding-top: .9rem;
}}
/* Espace au-dessus du pied : via le conteneur, pas via margin (même raison). */
[data-testid="stSidebar"] .stMarkdown:has(.ms-sidefoot) {{
  padding-top: 1.25rem;
}}
.ms-demo-chip {{
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .28rem .6rem;
  border-radius: 999px;
  background: var(--ms-secondary-subtle);
  border: 1px solid var(--ms-secondary-border);
  color: var(--ms-secondary-dark);
  font-size: .72rem; font-weight: 700; letter-spacing: .01em;
}}
.ms-demo-chip .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ms-secondary); flex-shrink: 0;
}}
/* Ligne « tout va bien » discrète sous le chip : pastille verte + texte */
.ms-sidefoot .okline {{
  display: flex; align-items: center; gap: .4rem;
  font-size: .72rem; font-weight: 600;
  color: var(--ms-text-2);
  margin-top: .55rem;
}}
.ms-sidefoot .okline .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ms-ok); flex-shrink: 0;
}}
.ms-sidefoot .note {{
  font-size: .7rem; color: var(--ms-text-3);
  line-height: 1.5; margin-top: .4rem;
}}

/* --------------------------------------------------------------------- *
 * 3) st.metric : carte plate avec bordure subtile.
 * --------------------------------------------------------------------- */
[data-testid="stMetric"] {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: 1rem 1.25rem;
  box-shadow: var(--ms-shadow-sm);
}}
[data-testid="stMetricLabel"] p {{
  color: var(--ms-text-2) !important;
  font-size: .72rem !important; font-weight: 600 !important;
  letter-spacing: .02em; text-transform: uppercase;
  white-space: normal !important;
}}
[data-testid="stMetricValue"] {{
  color: var(--ms-text) !important;
  font-size: 1.25rem !important; font-weight: 700 !important;
  letter-spacing: -0.01em; line-height: 1.15 !important;
}}
[data-testid="stMetricDelta"] {{ font-weight: 600 !important; margin-top: .25rem; }}

/* --------------------------------------------------------------------- *
 * 4) Boutons : primaire (vert plein), secondaire (outline).
 *    Variante ambre via conteneur keyé `.ms-amber` (ajouté par app/pages).
 * --------------------------------------------------------------------- */
.stButton > button {{
  border-radius: var(--ms-radius-md);
  font-weight: 600; letter-spacing: .01em;
  padding: .55rem 1rem;
  transition: all .15s ease;
  border: 1px solid var(--ms-border-strong);
  background: var(--ms-surface);
  color: var(--ms-text);
  /* Le libellé d'un bouton tient TOUJOURS sur une seule ligne */
  white-space: nowrap;
}}
.stButton > button p {{ white-space: nowrap; }}
.stButton > button:hover {{
  border-color: var(--ms-brand);
  color: var(--ms-brand);
  background: var(--ms-brand-subtle);
}}
.stButton > button[kind="primary"] {{
  background: var(--ms-brand);
  border-color: var(--ms-brand);
  color: #FFFFFF;
  box-shadow: 0 1px 2px 0 rgb(15 118 110 / .25);
}}
.stButton > button[kind="primary"]:hover {{
  background: var(--ms-brand-hover);
  border-color: var(--ms-brand-hover);
  color: #FFFFFF;
}}

/* Variante AMBRE : envelopper le bouton dans st.container(key="...amber...") */
/* Respiration entre la carte au-dessus et le bouton : pas de blocs collés */
[class*="st-key-amber"] {{ margin-top: .6rem; }}
[class*="st-key-amber"] .stButton > button,
.ms-amber .stButton > button {{
  background: var(--ms-secondary);
  border-color: var(--ms-secondary);
  color: #FFFFFF;
}}
[class*="st-key-amber"] .stButton > button:hover,
.ms-amber .stButton > button:hover {{
  background: var(--ms-secondary-dark);
  border-color: var(--ms-secondary-dark);
  color: #FFFFFF;
}}

/* Variante LIEN : texte gras couleur primaire, cliquable, pas de bloc.
   (ponts causaux, « Voir le détail 24 h », « Voir plus » du flux d'alertes) */
[class*="st-key-link"] .stButton > button {{
  background: transparent; border: none; box-shadow: none;
  color: var(--ms-brand); font-weight: 700; font-size: .9rem;
  padding: .15rem .1rem; text-decoration: none;
}}
[class*="st-key-link"] .stButton > button p {{ font-weight: 700; }}
[class*="st-key-link"] .stButton > button:hover {{
  color: var(--ms-brand-hover); text-decoration: underline;
  background: transparent;
}}

.stFormSubmitButton > button {{
  background: var(--ms-brand); border-color: var(--ms-brand);
  color: #FFFFFF; font-weight: 600;
  border-radius: var(--ms-radius-md);
}}
.stFormSubmitButton > button:hover {{
  background: var(--ms-brand-hover); border-color: var(--ms-brand-hover);
}}

/* Liens de page dans le corps (st.page_link hors sidebar) : lien ambre. */
.main [data-testid="stPageLink-NavLink"] {{
  color: var(--ms-secondary); font-weight: 600;
  padding: .2rem .4rem; border-radius: 8px;
}}
.main [data-testid="stPageLink-NavLink"] p {{
  color: inherit !important; font-weight: inherit !important; margin: 0;
}}
.main [data-testid="stPageLink-NavLink"]:hover {{
  background: var(--ms-secondary-subtle);
  color: var(--ms-secondary-dark);
}}

/* --------------------------------------------------------------------- *
 * 5) Champs de saisie
 * --------------------------------------------------------------------- */
.stTextInput input, .stTextArea textarea,
.stSelectbox > div > div, .stMultiSelect > div > div,
.stNumberInput input, .stDateInput input {{
  border-radius: var(--ms-radius-md) !important;
  border-color: var(--ms-border) !important;
  background-color: var(--ms-surface) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
  border-color: var(--ms-brand) !important;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, .15) !important;
}}

/* --------------------------------------------------------------------- *
 * 6) Onglets
 * --------------------------------------------------------------------- */
.stTabs {{ margin: .75rem 0 .5rem; }}
.stTabs [data-baseweb="tab-list"] {{
  gap: .25rem; background: var(--ms-bg-muted);
  padding: .25rem; border-radius: var(--ms-radius-md);
  border: 1px solid var(--ms-border);
  margin-bottom: .75rem;
}}
.stTabs [data-baseweb="tab"] {{
  border-radius: 8px; padding: .375rem .9rem;
  color: var(--ms-text-2); font-weight: 500;
  background: transparent; height: 36px;
}}
.stTabs [aria-selected="true"] {{
  background: var(--ms-surface); color: var(--ms-brand);
  box-shadow: var(--ms-shadow-sm); font-weight: 600;
}}

/* --------------------------------------------------------------------- *
 * 7) Expandeurs · 8) Séparateurs · 9) Tableaux
 * --------------------------------------------------------------------- */
[data-testid="stExpander"] {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  box-shadow: var(--ms-shadow-sm);
}}
[data-testid="stExpander"] summary {{ font-weight: 600; color: var(--ms-text); }}

hr {{ border-color: var(--ms-divider) !important; margin: 1.5rem 0; }}

[data-testid="stDataFrame"] thead tr th {{
  background: var(--ms-bg-muted) !important;
  color: var(--ms-text-2) !important;
  font-weight: 600 !important;
  text-transform: uppercase; letter-spacing: .03em;
  font-size: .75rem !important;
}}
[data-testid="stDataFrame"] tbody tr:hover td {{
  background: var(--ms-brand-subtle) !important;
}}

/* --------------------------------------------------------------------- *
 * 10) Composants du design system (.ms-*), consommés par components.py
 * --------------------------------------------------------------------- */

/* -- En-tête de page : bandeau teinté qui porte l'identité --------------- */
.ms-pagehead {{
  margin: 0 0 1.1rem;
  padding: 1.1rem 1.4rem 1.2rem;
  border-radius: var(--ms-radius-lg);
  background:
    radial-gradient(420px 140px at 100% 0%, rgba(180, 83, 9, .05), transparent 70%),
    linear-gradient(135deg, var(--ms-brand-subtle) 0%, rgba(230, 245, 241, .25) 55%, transparent 100%);
  border: 1px solid var(--ms-brand-border);
  border-left: 4px solid var(--ms-brand);
}}
.ms-pagehead.secondary {{
  background:
    radial-gradient(420px 140px at 100% 0%, rgba(15, 118, 110, .05), transparent 70%),
    linear-gradient(135deg, var(--ms-secondary-subtle) 0%, rgba(254, 243, 226, .25) 55%, transparent 100%);
  border-color: var(--ms-secondary-border);
  border-left-color: var(--ms-secondary);
}}
.ms-pagehead .eyebrow {{
  display: flex; align-items: center; gap: .4rem;
  text-transform: uppercase; letter-spacing: .11em;
  font-size: .7rem; font-weight: 700;
  color: var(--ms-brand); margin-bottom: .3rem;
}}
.ms-pagehead .eyebrow.secondary {{ color: var(--ms-secondary); }}
.ms-pagehead h1 {{
  font-size: 1.75rem; font-weight: 750; letter-spacing: -.02em;
  color: var(--ms-text); margin: 0;
}}
.ms-pagehead .sub {{
  color: var(--ms-text-2); font-size: .9375rem;
  margin-top: .3rem; max-width: 75ch; line-height: 1.55;
}}

/* -- Panneau-carte : tout conteneur keyé "panel_*" devient une surface
      carte (fond blanc, bordure, ombre). Permet d'envelopper des widgets
      Streamlit (filtres, formulaires, graphes) dans une vraie carte. ----- */
[class*="st-key-panel"] {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: 1rem 1.15rem;
  box-shadow: var(--ms-shadow-sm);
}}
/* Variante ambre pour les panneaux techniques (clé "panel_amber_*") */
[class*="st-key-panel_amber"] {{
  border-top: 3px solid var(--ms-secondary);
}}

/* Les formulaires (brief SBAR, validations) deviennent eux aussi des
   cartes : la zone de saisie est identifiable d'un coup d'œil. */
[data-testid="stForm"] {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: 1rem 1.15rem;
  box-shadow: var(--ms-shadow-sm);
}}

/* -- En-tête de section normalisé (motif obligatoire §6) :
      [icône SVG] + [LIBELLÉ CAPITALES gras] + [filet horizontal] --------- */
.ms-sech {{
  display: flex; align-items: center; gap: .55rem;
  /* Respiration généreuse entre les sections : chaque bloc est identifiable */
  margin: 2.4rem 0 1rem;
}}
.ms-sech .ic {{
  display: flex; align-items: center; justify-content: center;
  color: var(--ms-brand); flex-shrink: 0;
}}
.ms-sech .lbl {{
  font-size: .78rem; font-weight: 750;
  text-transform: uppercase; letter-spacing: .09em;
  color: var(--ms-text); white-space: nowrap;
}}
.ms-sech .sub {{
  /* Le sous-titre peut passer à la ligne : il ne doit JAMAIS déborder
     sur le bloc voisin dans une colonne étroite. */
  font-size: .78rem; color: var(--ms-text-3);
  font-weight: 500; white-space: normal; min-width: 0;
}}
.ms-sech .rule {{
  flex: 1; height: 1px; background: var(--ms-divider); min-width: 2rem;
}}
.ms-sech .right {{
  font-size: .75rem; color: var(--ms-text-3); font-weight: 500;
  white-space: nowrap;
}}
/* Sections critiques (À traiter maintenant) et techniques (Pipeline & données) */
.ms-sech.crit .ic {{ color: var(--ms-crit); }}
.ms-sech.secondary .ic {{ color: var(--ms-secondary); }}
.ms-sech.secondary .lbl {{ color: var(--ms-secondary-dark); }}

/* -- Carte d'alerte (états : critique / à surveiller / résolu) ---------- */
.ms-alert-card {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: 1.1rem 1.25rem;
  box-shadow: var(--ms-shadow-sm);
  position: relative; overflow: hidden;
  height: 100%;
}}
.ms-alert-card::before {{
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
}}
.ms-alert-card.crit    {{ border-color: var(--ms-alert-border); }}
.ms-alert-card.crit::before    {{ background: var(--ms-crit); }}
.ms-alert-card.warn    {{ border-color: var(--ms-secondary-border); }}
.ms-alert-card.warn::before    {{ background: var(--ms-secondary); }}
.ms-alert-card.resolved::before {{ background: var(--ms-ok); }}

.ms-alert-card .head {{
  display: flex; align-items: center; justify-content: space-between;
  gap: .5rem; margin-bottom: .35rem;
}}
.ms-alert-card .head .t {{
  display: flex; align-items: center; gap: .5rem;
  font-weight: 750; color: var(--ms-text); font-size: 1.02rem;
  letter-spacing: -.01em;
}}
.ms-alert-card.crit .head .t svg {{ color: var(--ms-crit); }}
.ms-alert-card.warn .head .t svg {{ color: var(--ms-secondary); }}
.ms-alert-card.resolved .head .t svg {{ color: var(--ms-ok); }}
.ms-alert-card .body {{
  color: var(--ms-text-2); font-size: .9rem; line-height: 1.55;
}}
.ms-alert-card .body b, .ms-alert-card .body strong {{ color: var(--ms-text); }}
.ms-alert-card .meta {{
  font-size: .78rem; color: var(--ms-text-3); margin-top: .4rem;
}}

/* -- Badge de statut (contraste AA, lisible à distance) ----------------- */
.ms-badge {{
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .18rem .55rem; border-radius: 999px;
  font-size: .72rem; font-weight: 750; letter-spacing: .03em;
  text-transform: uppercase; white-space: nowrap;
  border: 1px solid transparent;
}}
.ms-badge.crit {{ background: {Status.crit_bg}; color: {Status.crit_fg}; border-color: {Status.crit_border}; }}
.ms-badge.warn {{ background: {Status.warn_bg}; color: {Status.warn_fg}; border-color: {Status.warn_border}; }}
.ms-badge.ok   {{ background: {Status.ok_bg};   color: {Status.ok_fg};   border-color: {Status.ok_border}; }}

/* -- Pont causal excursion vers rupture (différenciateur produit §8) ------- */
.ms-bridge {{
  display: flex; align-items: flex-start; gap: .55rem;
  background: var(--ms-brand-subtle);
  border: 1.5px dashed var(--ms-brand);
  border-radius: var(--ms-radius-md);
  padding: .65rem .8rem;
  margin-top: .75rem;
  color: var(--ms-brand-hover);
  font-size: .85rem; line-height: 1.5;
}}
.ms-bridge svg {{ color: var(--ms-brand); margin-top: 1px; }}
.ms-bridge b {{ color: var(--ms-brand-hover); }}

/* -- Barre santé technique (niveau 3 de l'Overview, discrète) ----------- */
.ms-techbar {{
  display: flex; align-items: center; gap: .6rem; flex-wrap: wrap;
  background: var(--ms-bg-subtle);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: .55rem .9rem;
  font-size: .8rem; color: var(--ms-text-2);
}}
.ms-techbar .dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--ms-ok); flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, .14);
}}
.ms-techbar .sep {{ color: var(--ms-text-3); }}
.ms-techbar .spacer {{ flex: 1; }}

/* -- Infobulle « Comment ça marche ? » (icône info SVG) ------------------ */
.ms-tip {{
  display: inline-flex; align-items: center; gap: .25rem;
  color: var(--ms-text-3); cursor: help;
  border-bottom: 1px dotted var(--ms-text-3);
  font-size: .8rem; font-weight: 500;
}}
.ms-tip:hover {{ color: var(--ms-brand); border-bottom-color: var(--ms-brand); }}

/* -- Bloc KPI : simple, cadre couleur primaire, gros chiffre coloré ------- */
.ms-kpi {{
  background: var(--ms-surface);
  border: 1.5px solid var(--ms-brand-border);
  border-radius: var(--ms-radius-lg);
  padding: .9rem 1.05rem;
  box-shadow: var(--ms-shadow-sm);
  height: 100%;
}}
.ms-kpi .ms-kpi-row {{ display: flex; align-items: center; justify-content: space-between; }}
.ms-kpi .ms-kpi-lbl {{
  font-size: .72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em;
  color: var(--ms-text-2);
}}
.ms-kpi .ms-kpi-val {{
  font-size: 1.45rem; font-weight: 700; color: var(--ms-text);
  letter-spacing: -.01em; line-height: 1.15; margin-top: .25rem;
}}
/* Le chiffre porte l'état réel :
   - tout va bien : couleur par défaut (encre), pas de vert ;
   - à surveiller / dégradé : ambre (l'« orangé ») ;
   - rouge réservé aux comptes réellement critiques (> 0). */
.ms-kpi .ms-kpi-val.ok   {{ color: var(--ms-text); }}
.ms-kpi .ms-kpi-val.warn {{ color: var(--ms-secondary); }}
.ms-kpi .ms-kpi-val.crit {{ color: var(--ms-crit); }}
/* Valeur longue (durée, texte) : taille contenue, pas d'effet pancarte */
.ms-kpi .ms-kpi-val.small {{ font-size: 1.05rem; font-weight: 700; }}
/* Identité du bloc : les blocs neutres et OK gardent le cadre par défaut ;
   seuls les blocs de vigilance (À surveiller, Critiques) prennent le cadre
   et l'icône ambre. */
.ms-kpi.f-warn, .ms-kpi.f-crit {{ border-color: var(--ms-secondary); }}
.ms-kpi.f-warn .ms-kpi-icon,
.ms-kpi.f-crit .ms-kpi-icon {{ color: var(--ms-secondary); }}
.ms-kpi .ms-kpi-trend {{
  font-size: .78rem; font-weight: 500; margin-top: .4rem;
  color: var(--ms-text-2); line-height: 1.4;
}}
.ms-kpi .ms-kpi-trend.up   {{ color: {Status.ok_fg}; font-weight: 600; }}
.ms-kpi .ms-kpi-trend.down {{ color: {Status.crit_fg}; font-weight: 600; }}
.ms-kpi .ms-kpi-icon {{
  display: flex; align-items: center; justify-content: center;
  color: var(--ms-text-3);
}}

/* -- Pill de statut ------------------------------------------------------ */
.ms-pill {{
  display: inline-flex; align-items: center; gap: .375rem;
  padding: .2rem .55rem; border-radius: 999px;
  font-size: .75rem; font-weight: 700; letter-spacing: .02em;
  border: 1px solid transparent; white-space: nowrap;
}}
.ms-pill .dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; display: inline-block;
}}
.ms-pill.ok   {{ background: {Status.ok_bg};   color: {Status.ok_fg};   border-color: {Status.ok_border}; }}
.ms-pill.warn {{ background: {Status.warn_bg}; color: {Status.warn_fg}; border-color: {Status.warn_border}; }}
.ms-pill.crit {{ background: {Status.crit_bg}; color: {Status.crit_fg}; border-color: {Status.crit_border}; }}
.ms-pill.info {{ background: {Status.info_bg}; color: {Status.info_fg}; border-color: {Status.info_border}; }}
.ms-pill.muted{{ background: var(--ms-bg-muted); color: var(--ms-text-2); border-color: var(--ms-border); }}

/* -- Tuile frigo ---------------------------------------------------------- */
.ms-tile {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: .9rem 1rem;
  box-shadow: var(--ms-shadow-sm);
  transition: all .15s ease;
  position: relative; overflow: hidden;
}}
.ms-tile:hover {{ box-shadow: var(--ms-shadow-md); border-color: var(--ms-border-strong); }}
.ms-tile.crit {{ border-color: {Status.crit_border}; box-shadow: 0 0 0 3px rgba(220, 38, 38, .06); }}
.ms-tile.warn {{ border-color: {Status.warn_border}; }}
.ms-tile .ms-tile-id {{
  font-family: {TOK.font_mono};
  font-size: .75rem; color: var(--ms-text-2); letter-spacing: .04em;
}}
.ms-tile .ms-tile-temp {{
  /* Taille contenue et JAMAIS de retour à la ligne : « 9.4 °C » d'un bloc */
  font-size: 1.2rem; font-weight: 700; letter-spacing: -.01em;
  line-height: 1.1; white-space: nowrap;
}}
.ms-tile .ms-tile-temp.ok   {{ color: {Status.ok_fg}; }}
.ms-tile .ms-tile-temp.warn {{ color: {Status.warn_fg}; }}
.ms-tile .ms-tile-temp.crit {{ color: {Status.crit_fg}; }}
.ms-tile .ms-tile-meta {{
  display: flex; gap: 1rem; font-size: .8125rem; color: var(--ms-text-2);
  margin-top: .25rem;
}}
.ms-tile .ms-tile-site {{ font-weight: 600; color: var(--ms-text); font-size: .875rem; }}

/* -- Chip source (citations RAG), désormais aux couleurs de la marque --- */
.ms-chip {{
  display: inline-flex; align-items: center; gap: .375rem;
  padding: .25rem .55rem .25rem .35rem;
  border-radius: 8px;
  background: var(--ms-brand-subtle);
  border: 1px solid var(--ms-brand-border);
  color: var(--ms-brand-hover);
  font-size: .75rem; font-weight: 600;
  margin-right: .25rem; margin-bottom: .25rem;
}}
.ms-chip .score {{
  font-family: {TOK.font_mono}; font-size: .7rem;
  background: #FFFFFF; padding: 1px 6px; border-radius: 5px;
  color: var(--ms-brand); border: 1px solid var(--ms-brand-border);
}}

/* -- Encadré callout ------------------------------------------------------ */
.ms-callout {{
  border-radius: var(--ms-radius-md);
  padding: .85rem 1rem;
  border-left: 3px solid var(--ms-brand);
  background: var(--ms-brand-subtle);
  color: var(--ms-text);
  font-size: .9375rem; line-height: 1.55;
  /* Deux callouts qui se suivent ne doivent jamais être collés */
  margin-bottom: 1rem;
}}
.ms-callout.alert  {{ border-left-color: var(--ms-crit); background: var(--ms-alert-subtle); }}
.ms-callout.warn   {{ border-left-color: var(--ms-secondary); background: var(--ms-secondary-subtle); }}
.ms-callout.accent {{ border-left-color: var(--ms-secondary); background: var(--ms-secondary-subtle); }}
.ms-callout strong {{ color: var(--ms-text); }}

/* -- Bulle de section SBAR ------------------------------------------------ */
.ms-sbar {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: .85rem 1rem; margin-bottom: .65rem;
  position: relative;
}}
.ms-sbar .ms-sbar-tag {{
  position: absolute; top: -10px; left: 12px;
  background: var(--ms-brand); color: #FFFFFF;
  font-size: .65rem; font-weight: 700; letter-spacing: .12em;
  padding: 2px 8px; border-radius: 6px;
}}
.ms-sbar p {{ margin: 0; color: var(--ms-text); line-height: 1.55; }}

/* -- Carte médicament alternatif ----------------------------------------- */
.ms-alt {{
  background: var(--ms-bg-muted);
  border-radius: var(--ms-radius-md);
  padding: .65rem .85rem; margin-bottom: .5rem;
  border: 1px solid var(--ms-border);
}}
.ms-alt .name {{
  font-weight: 600; color: var(--ms-text);
  display: flex; gap: .5rem; align-items: baseline;
}}
.ms-alt .atc {{
  font-family: {TOK.font_mono}; font-size: .72rem;
  color: var(--ms-text-2); padding: 1px 6px; border-radius: 4px;
  background: var(--ms-surface); border: 1px solid var(--ms-border);
}}
.ms-alt .dose {{ color: var(--ms-text-2); font-size: .85rem; margin-top: .15rem; }}
.ms-alt .caveat {{
  display: flex; align-items: center; gap: .3rem;
  color: {Status.warn_fg}; font-size: .8rem; margin-top: .25rem;
}}

/* -- Carte nœud pipeline (page Architecture) ------------------------------ */
.ms-node {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: .8rem .9rem;
  text-align: center;
  box-shadow: var(--ms-shadow-sm);
}}
.ms-node .icon {{
  display: flex; align-items: center; justify-content: center;
  color: var(--ms-secondary); margin-bottom: .4rem;
}}
.ms-node .title {{ font-weight: 650; color: var(--ms-text); font-size: .875rem; }}
.ms-node .tech {{
  font-family: {TOK.font_mono}; font-size: .7rem;
  color: var(--ms-text-2); margin-top: .15rem;
}}
.ms-node-arrow {{
  display: flex; align-items: center; justify-content: center;
  height: 100%; min-height: 90px; color: var(--ms-text-3);
}}

/* -- Élément de stack (page À propos) ------------------------------------- */
.ms-stack-item {{
  background: var(--ms-surface);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: .65rem .85rem;
  display: flex; align-items: center; gap: .65rem;
  margin-bottom: .35rem;
}}
.ms-stack-item .ic {{
  width: 32px; height: 32px; border-radius: 9px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--ms-brand-subtle); color: var(--ms-brand);
}}
.ms-stack-item .name {{ font-weight: 600; color: var(--ms-text); font-size: .9rem; }}
.ms-stack-item .role {{ color: var(--ms-text-2); font-size: .8rem; }}

/* -- Carte hero (page À propos) ------------------------------------------- */
.ms-hero {{
  position: relative;
  background:
    radial-gradient(800px 280px at 100% 0%, rgba(180, 83, 9, .12), transparent 60%),
    linear-gradient(135deg, #0F766E 0%, #0B5650 60%, #0A4A45 100%);
  color: #ECFEFF;
  padding: 1.75rem 2rem;
  border-radius: var(--ms-radius-lg);
  box-shadow: var(--ms-shadow-md);
  overflow: hidden;
  margin-bottom: 1.25rem;
}}
.ms-hero .ms-eyebrow {{
  text-transform: uppercase; letter-spacing: .12em;
  font-size: .7rem; font-weight: 600;
  color: rgba(230, 245, 241, .85); margin-bottom: .25rem;
}}
.ms-hero h1 {{
  font-size: 1.75rem; color: #FFFFFF; margin: 0 0 .25rem;
  letter-spacing: -0.02em;
}}
.ms-hero p {{
  color: rgba(236, 254, 255, .85); margin: 0;
  font-size: .9375rem; max-width: 56ch; line-height: 1.55;
}}
.ms-hero .ms-hero-meta {{
  display: flex; flex-wrap: wrap; gap: 1.25rem;
  margin-top: 1rem; font-size: .8125rem;
}}
.ms-hero .ms-hero-meta .lbl {{
  text-transform: uppercase; letter-spacing: .08em;
  color: rgba(230, 245, 241, .65); margin-right: .35rem; font-weight: 600;
}}
.ms-hero .ms-hero-meta .val {{ color: #FFFFFF; font-weight: 600; }}

/* -- Flux d'alertes (Overview) -------------------------------------------- */
.ms-feed-item {{
  display: flex; gap: .65rem;
  padding: .65rem .75rem;
  background: var(--ms-bg);
  border: 1px solid var(--ms-border);
  border-radius: 10px; margin-bottom: .5rem;
  box-shadow: var(--ms-shadow-sm);
}}
.ms-feed-item .dot {{
  width: 8px; height: 8px; border-radius: 50%;
  margin-top: 5px; flex-shrink: 0;
}}
.ms-feed-item .t {{
  font-weight: 600; color: var(--ms-text); font-size: .875rem;
}}
.ms-feed-item .ts {{
  font-size: .72rem; color: var(--ms-text-3); white-space: nowrap;
}}
.ms-feed-item .m {{
  font-size: .78rem; color: var(--ms-text-2); margin-top: .1rem;
}}

/* --------------------------------------------------------------------- *
 * Plotly : modebar discrète
 * --------------------------------------------------------------------- */
.js-plotly-plot .plotly .modebar {{ opacity: .25; transition: opacity .2s ease; }}
.js-plotly-plot .plotly:hover .modebar {{ opacity: 1; }}

</style>
"""


def inject() -> None:
    """Injecte la couche CSS. À appeler une fois en haut du point d'entrée."""
    st.markdown(CSS, unsafe_allow_html=True)
