"""Tokens de design : source unique de vérité pour le langage visuel.

Identité visuelle validée
-------------------------
* **Vert sapin / teal foncé** (primaire, `#0F766E`) : la marque, la navigation
  active, les actions positives, les liens, le lien causal. Médical sans être
  stérile, passe WCAG AA sur fond blanc.
* **Ambre brûlé** (secondaire, `#B45309`) : la chaleur, l'alerte, l'excursion
  de température, le cœur métier de l'app. Utilisé pour la section
  « Pipeline & données », les alertes « à surveiller », le chip « Mode démo »
  et les accents secondaires. Il contraste chaleureusement avec le vert
  « froid » de la marque.
* **Couleurs sémantiques** réservées au statut, jamais décoratives :
  rouge `#DC2626` STRICTEMENT réservé au critique · ambre = à surveiller ·
  vert `#16A34A` = OK / sain.

Accessibilité
-------------
Chaque paire texte/fond est vérifiée WCAG 2.1 AA (4,5:1 corps de texte,
3:1 grands textes et composants UI). Les trois couleurs sémantiques ont des
luminosités distinctes : distinguables aussi en cas de déficience rouge-vert.

Ce fichier est importé par ``style.py`` (injection des tokens en variables
CSS) et par ``components.py`` (couleurs des figures Plotly et des badges).
NE PAS hardcoder de couleurs ailleurs : toujours consommer ces tokens.
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Rampes de couleurs brutes. Le reste de l'app consomme les tokens sémantiques
# plus bas, jamais ces rampes directement.
# ---------------------------------------------------------------------------
class Teal:
    """Primaire : vert sapin / teal foncé. L'identité de l'app."""
    subtle = "#E6F5F1"   # fonds, états actifs (nav, hover)
    border = "#BFE3DA"   # bordures sur fonds verts clairs
    base   = "#0F766E"   # couleur principale de la marque
    dark   = "#0B5650"   # hover, texte sur fond clair
    grad_a = "#10B981"   # départ du dégradé du logo
    grad_b = "#0F766E"   # arrivée du dégradé du logo


class Amber:
    """Secondaire : ambre brûlé. Chaleur, alerte, excursion de température."""
    subtle = "#FEF3E2"   # fond clair associé
    border = "#FCD9A8"   # ligne / bordure associée
    base   = "#B45309"   # ambre brûlé
    dark   = "#92400E"   # texte petit corps sur fond pâle (contraste AA renforcé)


class Red:
    """Critique uniquement. Ne jamais l'utiliser pour décorer."""
    subtle = "#FEF2F2"
    border = "#FECACA"
    base   = "#DC2626"
    dark   = "#B91C1C"


class Green:
    """OK / sain."""
    subtle = "#ECFDF5"
    border = "#BBF7D0"
    base   = "#16A34A"
    dark   = "#15803D"


class Slate:
    """Neutres texte et lignes."""
    ink    = "#0F172A"   # encre
    sub    = "#475569"   # sous-texte
    faint  = "#94A3B8"   # estompé (méta, jamais pour du corps de texte)
    line   = "#E8EBEF"   # lignes / bordures
    bg     = "#F8FAFC"
    bg2    = "#F4F7F9"


class Status:
    """Couleurs sémantiques : statut uniquement, jamais décoratives."""
    ok_bg,   ok_fg,   ok_solid,   ok_border   = Green.subtle, Green.dark, Green.base, Green.border
    warn_bg, warn_fg, warn_solid, warn_border = Amber.subtle, Amber.dark, Amber.base, Amber.border
    crit_bg, crit_fg, crit_solid, crit_border = Red.subtle,   Red.dark,   Red.base,   Red.border
    # « info » est rendu en marque (vert) : plus de violet/indigo dans l'app.
    info_bg, info_fg, info_solid, info_border = Teal.subtle,  Teal.dark,  Teal.base,  Teal.border


# ---------------------------------------------------------------------------
# Tokens sémantiques : ce que le reste de l'app référence.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Tokens:
    """Tokens de design à l'échelle de l'application.

    Les composants DOIVENT consommer ces tokens plutôt que les rampes brutes,
    ce qui permet de re-skinner l'app en un seul endroit.
    """
    # Marque (primaire)
    brand:          str = Teal.base
    brand_hover:    str = Teal.dark
    brand_subtle:   str = Teal.subtle
    brand_border:   str = Teal.border

    # Secondaire (ambre brûlé) : section Pipeline & données, accents chaleur
    secondary:         str = Amber.base
    secondary_dark:    str = Amber.dark
    secondary_subtle:  str = Amber.subtle
    secondary_border:  str = Amber.border

    # Rétro-compat : « accent » pointe désormais sur le secondaire ambre.
    accent:         str = Amber.base
    accent_subtle:  str = Amber.subtle
    accent_border:  str = Amber.border

    # Alerte critique (rouge strict)
    alert:          str = Red.base
    alert_subtle:   str = Red.subtle
    alert_border:   str = Red.border

    # Neutres
    bg:             str = "#FFFFFF"
    bg_subtle:      str = Slate.bg
    bg_muted:       str = Slate.bg2
    surface:        str = "#FFFFFF"
    border:         str = Slate.line
    border_strong:  str = "#D7DDE4"
    divider:        str = Slate.line

    # Texte
    text:           str = Slate.ink
    text_secondary: str = Slate.sub
    text_tertiary:  str = Slate.faint
    text_on_brand:  str = "#FFFFFF"

    # Statuts sémantiques (ré-exportés pour commodité)
    ok:             str = Status.ok_solid
    warn:           str = Status.warn_solid
    crit:           str = Status.crit_solid

    # Typographie
    font_family:    str = (
        '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", '
        '"Roboto", "Helvetica Neue", Arial, sans-serif'
    )
    font_mono:      str = (
        '"JetBrains Mono", ui-monospace, "SF Mono", "Menlo", '
        '"Consolas", monospace'
    )

    # Rayons & élévation
    radius_sm:      str = "6px"
    radius_md:      str = "10px"
    radius_lg:      str = "14px"
    radius_xl:      str = "18px"

    shadow_sm:      str = "0 1px 2px 0 rgb(15 23 42 / 0.05)"
    shadow_md:      str = (
        "0 2px 4px -1px rgb(15 23 42 / 0.06), "
        "0 4px 6px -2px rgb(15 23 42 / 0.04)"
    )
    shadow_lg:      str = (
        "0 10px 15px -3px rgb(15 23 42 / 0.07), "
        "0 4px 6px -2px rgb(15 23 42 / 0.04)"
    )

    # Espacement : grille de 4 px
    space_1:        str = "4px"
    space_2:        str = "8px"
    space_3:        str = "12px"
    space_4:        str = "16px"
    space_5:        str = "20px"
    space_6:        str = "24px"
    space_8:        str = "32px"
    space_10:       str = "40px"


TOK = Tokens()


# ---------------------------------------------------------------------------
# Helpers : correspondance sémantique pour le domaine chaîne du froid.
# ---------------------------------------------------------------------------
TEMP_OK_LOW    = 2.0
TEMP_OK_HIGH   = 8.0
TEMP_WARN_HIGH = 10.0
TEMP_CRIT_HIGH = 12.0


def fridge_state(temp_c: float | None) -> str:
    """Traduit une température en l'un des états : ``ok`` · ``warn`` · ``crit``.

    Les seuils reflètent l'enveloppe chaîne du froid 2-8 °C utilisée pour les
    vaccins et les biologiques (spécification WHO PQS E003). Au-dessus de
    10 °C on lève *à surveiller* (excursion), au-dessus de 12 °C le lot doit
    être mis en quarantaine.
    """
    if temp_c is None:
        return "warn"
    if temp_c < TEMP_OK_LOW or temp_c > TEMP_CRIT_HIGH:
        return "crit"
    if temp_c > TEMP_OK_HIGH:
        return "warn"
    return "ok"


# Libellés humains des états : mot métier d'abord, jamais de jargon.
STATE_LABELS = {"ok": "OK", "warn": "À surveiller", "crit": "Critique", "info": "Info"}


def state_label(state: str) -> str:
    """Traduit un token d'état en libellé humain français."""
    return STATE_LABELS.get(state, state)


def state_color(state: str) -> str:
    """Traduit un token d'état en sa couleur pleine."""
    return {"ok": TOK.ok, "warn": TOK.warn, "crit": TOK.crit,
            "info": TOK.brand}.get(state, TOK.text_tertiary)


def state_bg(state: str) -> str:
    """Traduit un token d'état en sa couleur de fond subtile."""
    return {
        "ok":   Status.ok_bg,
        "warn": Status.warn_bg,
        "crit": Status.crit_bg,
        "info": Status.info_bg,
    }.get(state, Slate.bg)


def state_fg(state: str) -> str:
    """Traduit un token d'état en sa couleur de texte accessible (AA)."""
    return {
        "ok":   Status.ok_fg,
        "warn": Status.warn_fg,
        "crit": Status.crit_fg,
        "info": Status.info_fg,
    }.get(state, Slate.sub)


def state_border(state: str) -> str:
    """Traduit un token d'état en sa couleur de bordure."""
    return {
        "ok":   Status.ok_border,
        "warn": Status.warn_border,
        "crit": Status.crit_border,
        "info": Status.info_border,
    }.get(state, Slate.line)
