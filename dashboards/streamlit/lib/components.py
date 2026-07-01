"""Composants UI Streamlit réutilisables : le langage que les pages parlent.

Chaque composant est un mince wrapper Python autour des classes CSS déclarées
dans ``style.py``. Les pages ne doivent jamais appeler directement
``st.markdown('<div…>')`` pour les motifs récurrents : elles demandent un
``section_header`` ou un ``alert_card`` ici pour que le rendu reste cohérent.

Principes
---------
* Zéro emoji : toutes les icônes viennent de ``icons.py`` (SVG line/stroke).
* Mot métier d'abord : le terme technique passe derrière une infobulle
  (``info_tip``), jamais en première lecture.
* Les couleurs sémantiques (rouge/ambre/vert) sont réservées au statut.
"""
from __future__ import annotations

import html
from collections.abc import Iterable
from datetime import UTC, datetime

import streamlit as st

from . import icons as I
from .theme import fridge_state, state_label


# ---------------------------------------------------------------------------
# Petits helpers
# ---------------------------------------------------------------------------
def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def render(html_str: str) -> None:
    """Injecte un fragment HTML via le canal markdown de Streamlit."""
    st.markdown(html_str, unsafe_allow_html=True)


def fmt_heure(hhmm: str) -> str:
    """Horodatage uniformisé : « à 20:18 ». Un seul format dans toute l'app."""
    return f"à {hhmm}"


# ---------------------------------------------------------------------------
# En-tête de page : eyebrow + titre + sous-titre (+ infobulle optionnelle)
# ---------------------------------------------------------------------------
def page_header(*, eyebrow: str, title: str, subtitle: str = "",
                icon: str = "", tone: str = "brand",
                tip: str = "") -> None:
    """En-tête de page normalisé.

    ``tone="secondary"`` colore l'eyebrow en ambre (pages Pipeline & données).
    ``tip`` ajoute une infobulle « Comment ça marche ? » au survol du sous-titre.
    """
    head_cls = "ms-pagehead secondary" if tone == "secondary" else "ms-pagehead"
    eyebrow_cls = "eyebrow secondary" if tone == "secondary" else "eyebrow"
    icon_html = I.icon(icon, size=13) if icon else ""
    tip_html = ""
    if tip:
        tip_html = (
            f' <span class="ms-tip" title="{_esc(tip)}">{I.icon("info", size=13)}'
            f' Comment ça marche ?</span>'
        )
    sub_html = f'<div class="sub">{subtitle}{tip_html}</div>' if subtitle else ""
    render(
        f"""
        <div class="{head_cls}">
          <div class="{eyebrow_cls}">{icon_html}{_esc(eyebrow)}</div>
          <h1>{_esc(title)}</h1>
          {sub_html}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# En-tête de section normalisé (motif obligatoire §6) :
# [icône SVG] + [LIBELLÉ EN CAPITALES gras] + [filet horizontal]
# ---------------------------------------------------------------------------
def section_header(label: str, *, icon: str = "chevron-right",
                   tone: str = "brand", subtitle: str = "",
                   right: str = "") -> None:
    """En-tête de section : crée la grille visuelle commune à toutes les pages.

    ``tone`` ∈ ``brand`` (vert, défaut) · ``secondary`` (ambre, sections
    Pipeline & données) · ``crit`` (rouge, réservé à « À traiter maintenant »).
    """
    tone_cls = {"brand": "", "secondary": "secondary", "crit": "crit"}.get(tone, "")
    sub_html = f'<span class="sub">{_esc(subtitle)}</span>' if subtitle else ""
    right_html = f'<span class="right">{_esc(right)}</span>' if right else ""
    render(
        f"""
        <div class="ms-sech {tone_cls}">
          <span class="ic">{I.icon(icon, size=16)}</span>
          <span class="lbl">{_esc(label)}</span>
          {sub_html}
          <span class="rule"></span>
          {right_html}
        </div>
        """
    )


def section_head(title: str, subtitle: str = "", right: str = "") -> None:
    """Alias rétro-compatible : redirige vers le motif normalisé."""
    section_header(title, subtitle=subtitle, right=right)


# ---------------------------------------------------------------------------
# Infobulle « mot métier d'abord, technique au survol »
# ---------------------------------------------------------------------------
def info_tip(label: str, detail: str) -> str:
    """Retourne un span infobulle : ``label`` visible, ``detail`` au survol.

    Usage : ``render(f"Fiabilité prévision : élevée {info_tip('détail', 'MAPE 7,4 %')}")``
    L'icône d'info est un vrai SVG, jamais un caractère ou un emoji.
    """
    return (
        f'<span class="ms-tip" title="{_esc(detail)}">'
        f'{I.icon("info", size=13)} {_esc(label)}</span>'
    )


# ---------------------------------------------------------------------------
# Pills & badges de statut
# ---------------------------------------------------------------------------
def pill(label: str, state: str = "muted") -> str:
    """Retourne une pill de statut (chaîne HTML, à utiliser avec ``render``).

    ``state`` ∈ ``ok`` | ``warn`` | ``crit`` | ``info`` | ``muted``.
    """
    state = state if state in {"ok", "warn", "crit", "info", "muted"} else "muted"
    return f'<span class="ms-pill {state}"><span class="dot"></span>{_esc(label)}</span>'


def badge(state: str) -> str:
    """Badge de statut à fort contraste (AA) avec libellé humain français."""
    state = state if state in {"ok", "warn", "crit"} else "ok"
    return f'<span class="ms-badge {state}">{_esc(state_label(state))}</span>'


def pill_row(items: Iterable[tuple[str, str]]) -> None:
    """Affiche une rangée horizontale de pills. ``items`` = (label, state)."""
    chunks = " ".join(pill(lbl, st_) for lbl, st_ in items)
    render(f'<div style="display:flex;gap:.5rem;flex-wrap:wrap;">{chunks}</div>')


# ---------------------------------------------------------------------------
# Carte d'alerte (états : critique / à surveiller / résolu), §7 niveau 1
# ---------------------------------------------------------------------------
def alert_card(*, level: str, title: str, body_html: str,
               icon: str = "alert-triangle", meta: str = "") -> None:
    """Carte d'alerte hiérarchisée : raconte le problème en langage humain.

    ``level`` ∈ ``crit`` (rouge, badge Critique) · ``warn`` (ambre, badge
    À surveiller) · ``resolved`` (vert, badge OK). Les boutons d'action sont
    ajoutés PAR LA PAGE juste en dessous (st.button), pour rester interactifs.
    """
    level = level if level in {"crit", "warn", "resolved"} else "warn"
    badge_state = {"crit": "crit", "warn": "warn", "resolved": "ok"}[level]
    meta_html = f'<div class="meta">{_esc(meta)}</div>' if meta else ""
    render(
        f"""
        <div class="ms-alert-card {level}">
          <div class="head">
            <div class="t">{I.icon(icon, size=19)} {_esc(title)}</div>
            {badge(badge_state)}
          </div>
          <div class="body">{body_html}</div>
          {meta_html}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Pont causal excursion vers rupture (différenciateur produit, §8)
# ---------------------------------------------------------------------------
def causal_bridge(text_html: str) -> None:
    """Encadré « pont » : relie une excursion de température à son impact
    sur les ruptures de stock. Fond vert clair, bordure pointillée verte,
    icône courbe. La page place le lien/bouton de navigation juste après.
    """
    render(
        f"""
        <div class="ms-bridge">
          {I.icon("forecast", size=17)}
          <div>{text_html}</div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Barre santé technique (Overview niveau 3) : discrète, en bas de page
# ---------------------------------------------------------------------------
def tech_bar(*, events_per_min: int, uptime_pct: float,
             source_label: str = "") -> None:
    """La fierté technique s'exprime ici, et seulement ici, sur l'Overview.

    ``source_label`` affiche honnêtement la source de données réellement
    servie (mode démo / stack live / repli), fournie par ``data.data_mode()``.
    """
    src_html = (
        f'<span class="spacer"></span>'
        f'<span style="color:var(--ms-text-3);font-size:.75rem;">{_esc(source_label)}</span>'
    ) if source_label else '<span class="spacer"></span>'
    render(
        f"""
        <div class="ms-techbar">
          <span class="dot"></span>
          <b style="color:var(--ms-text);">Système en ligne :</b>
          {events_per_min} événements/min, disponibilité {uptime_pct} %,
          pipeline à jour.
          {src_html}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Cartes KPI
# ---------------------------------------------------------------------------
def kpi_card(*, label: str, value: str | int, icon: str = "activity",
             trend: str | None = None, trend_dir: str = "",
             variant: str = "default", flag: bool = False,
             top_border: str = "", tone: str = "", frame: str = "") -> None:
    """Un bloc KPI simple : cadre couleur primaire, gros chiffre coloré
    selon l'état (vert si OK, ambre si à surveiller, rouge si problème).

    Paramètres
    ----------
    label, value
        Le contenu en deux lignes du bloc (langage humain, zéro jargon).
    icon
        Nom d'une icône SVG de ``icons.py`` (jamais un emoji).
    trend
        Ligne de pied EXPLICITE : elle dit de quoi on parle,
        ex : ``"sur 9 contrôles automatiques du pipeline"``.
    tone
        ``"ok"`` | ``"warn"`` | ``"crit"`` : couleur du chiffre.
        Vide = chiffre neutre (encre).
    frame
        ``"ok"`` | ``"warn"`` | ``"crit"`` : identité FIXE du bloc (cadre et
        icône colorés). Le cadre dit « ce bloc parle de critique », le
        chiffre dit « où on en est vraiment ». Exemple : le bloc Critiques a
        un cadre rouge en permanence, mais son chiffre est vert quand il
        vaut 0.
    variant, flag, top_border
        Conservés pour rétro-compatibilité : ``top_border`` sert de repli
        à ``tone`` si celui-ci n'est pas fourni.
    """
    tone = tone or (top_border if top_border in {"ok", "warn", "crit"} else "")
    trend_html = ""
    if trend:
        trend_html = f'<div class="ms-kpi-trend {trend_dir}">{_esc(trend)}</div>'
    # Une valeur longue (texte, durée) passe en taille réduite : seuls les
    # vrais compteurs méritent le gros chiffre.
    size_cls = "small" if len(str(value)) > 6 else ""
    frame_cls = f"f-{frame}" if frame in {"ok", "warn", "crit"} else ""
    # Ordre de lecture : titre, puis la description (de quoi on parle),
    # puis le chiffre coloré en dernier.
    render(
        f"""
        <div class="ms-kpi {frame_cls}">
          <div class="ms-kpi-row">
            <div class="ms-kpi-lbl">{_esc(label)}</div>
            <div class="ms-kpi-icon">{I.icon(icon, size=16)}</div>
          </div>
          {trend_html}
          <div class="ms-kpi-val {tone} {size_cls}">{_esc(value)}</div>
        </div>
        """
    )


def kpi_strip(items: list[dict]) -> None:
    """Affiche une rangée de cartes KPI. Les pages n'ont qu'à passer la liste."""
    cols = st.columns(len(items), gap="small")
    for col, it in zip(cols, items, strict=False):
        with col:
            kpi_card(**it)


# ---------------------------------------------------------------------------
# Tuile frigo
# ---------------------------------------------------------------------------
def fridge_tile(f: dict, *, on_click_key: str | None = None) -> bool:
    """Affiche une tuile frigo. Retourne ``True`` si le bouton de drill-down
    a été cliqué. Badge d'état en libellé humain, horodatage uniformisé.
    """
    state = fridge_state(f["temp_c"])
    render(
        f"""
        <div class="ms-tile {state}">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="ms-tile-id">{_esc(f['fridge_id'])}</div>
            <span style="color:var(--ms-text-3);">{I.icon('fridge', size=14)}</span>
          </div>
          <div class="ms-tile-site">{_esc(f['site'])}</div>
          <div class="ms-tile-temp {state}" style="margin-top:.3rem;">{_esc(f['temp_c'])} °C</div>
          <div style="margin-top:.3rem;">{badge(state)}</div>
          <div class="ms-tile-meta">
            <span>{_esc(f['lots'])} lots</span>
            <span>relevé {fmt_heure(_esc(f['last_seen']))}</span>
          </div>
        </div>
        """
    )
    if on_click_key:
        # Lien texte (gras, couleur primaire, flèche), pas un bloc bouton :
        # la clé contient « link » : style lien (voir style.py).
        with st.container(key=f"link_detail_{f['fridge_id']}"):
            return st.button("Voir le détail 24 h", key=on_click_key)
    return False


# ---------------------------------------------------------------------------
# Source chips (citations RAG)
# ---------------------------------------------------------------------------
def source_chips(citations: list[dict]) -> None:
    """Affiche les citations RAG sous forme de ligne de chips."""
    if not citations:
        render('<span class="ms-pill muted">aucune source</span>')
        return
    parts: list[str] = []
    for c in citations:
        score = c.get("score")
        score_html = f'<span class="score">{score:.2f}</span>' if score is not None else ""
        parts.append(
            f'<span class="ms-chip">{score_html} '
            f'{_esc(c["document"])}, p.{_esc(c["page"])}</span>'
        )
    render('<div style="display:flex;flex-wrap:wrap;gap:.25rem;">' + "".join(parts) + "</div>")


# ---------------------------------------------------------------------------
# Bulle de section SBAR (utilisée par le Brief SBAR)
# ---------------------------------------------------------------------------
def sbar_section(tag: str, body: str) -> None:
    render(
        f"""
        <div class="ms-sbar">
          <div class="ms-sbar-tag">{_esc(tag.upper())}</div>
          <p>{_esc(body)}</p>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Callout box
# ---------------------------------------------------------------------------
def callout(body_html: str, variant: str = "default") -> None:
    """Insère un encadré callout. ``body_html`` peut contenir du HTML inline.

    ``variant`` ∈ ``default`` (vert marque) · ``alert`` (rouge critique) ·
    ``warn``/``accent`` (ambre secondaire).
    """
    variant = variant if variant in {"default", "alert", "warn", "accent"} else "default"
    cls = "ms-callout" if variant == "default" else f"ms-callout {variant}"
    render(f'<div class="{cls}">{body_html}</div>')


# ---------------------------------------------------------------------------
# Carte médicament alternatif (Brief SBAR)
# ---------------------------------------------------------------------------
def alternative_card(name: str, atc: str, dose: str, caveat: str) -> None:
    render(
        f"""
        <div class="ms-alt">
          <div class="name">{_esc(name)} <span class="atc">{_esc(atc)}</span></div>
          <div class="dose">{_esc(dose)}</div>
          <div class="caveat">{I.icon('alert-triangle', size=13)} {_esc(caveat)}</div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Nœud pipeline (page Architecture), icône SVG, accent ambre
# ---------------------------------------------------------------------------
def pipeline_node(*, icon: str, title: str, tech: str) -> None:
    render(
        f"""
        <div class="ms-node">
          <div class="icon">{I.icon(icon, size=22)}</div>
          <div class="title">{_esc(title)}</div>
          <div class="tech">{_esc(tech)}</div>
        </div>
        """
    )


def pipeline_arrow() -> None:
    """Flèche SVG entre deux nœuds du pipeline."""
    render(f'<div class="ms-node-arrow">{I.icon("arrow-right", size=18)}</div>')


# ---------------------------------------------------------------------------
# Élément de stack (page À propos), icône SVG, couleurs marque
# ---------------------------------------------------------------------------
def stack_item(name: str, role: str, icon: str = "layers") -> None:
    render(
        f"""
        <div class="ms-stack-item">
          <div class="ic">{I.icon(icon, size=16)}</div>
          <div>
            <div class="name">{_esc(name)}</div>
            <div class="role">{_esc(role)}</div>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Bloc hero (page À propos uniquement)
# ---------------------------------------------------------------------------
def hero(*, eyebrow: str, title: str, subtitle: str, meta: dict[str, str] | None = None) -> None:
    """Bloc hero : utilisé sur la page À propos (surface portfolio)."""
    meta_html = ""
    if meta:
        items = "".join(
            f'<div><span class="lbl">{_esc(k)}</span><span class="val">{_esc(v)}</span></div>'
            for k, v in meta.items()
        )
        meta_html = f'<div class="ms-hero-meta">{items}</div>'
    render(
        f"""
        <div class="ms-hero">
          <div class="ms-eyebrow">{_esc(eyebrow)}</div>
          <h1>{_esc(title)}</h1>
          <p>{_esc(subtitle)}</p>
          {meta_html}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Item du flux d'alertes (Overview)
# ---------------------------------------------------------------------------
def feed_item(*, title: str, site: str, msg: str, ts: str,
              color: str, tech: str = "") -> None:
    """Une ligne du flux d'alertes : langage humain, détail technique
    en infobulle au survol (``tech``)."""
    tech_attr = f' title="{_esc(tech)}"' if tech else ""
    render(
        f"""
        <div class="ms-feed-item"{tech_attr}>
          <div class="dot" style="background:{color};"></div>
          <div style="flex:1;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;">
              <div class="t">{_esc(title)}</div>
              <div class="ts">{fmt_heure(_esc(ts))}</div>
            </div>
            <div class="m">
              <span style="font-weight:600;color:var(--ms-text-2);">{_esc(site)}</span> : {_esc(msg)}
            </div>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Petits utilitaires divers
# ---------------------------------------------------------------------------
def now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
