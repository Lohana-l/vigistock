"""Set d'icônes SVG vectorielles : zéro emoji dans tout le projet.

Style "line/stroke" inspiré de Lucide/Feather :
* épaisseur de trait homogène 1.8 px,
* ``stroke="currentColor"`` pour hériter de la couleur du contexte,
* ``viewBox 0 0 24 24`` partout, redimensionnable sans perte.

Trois points d'entrée :
* ``icon(name, ...)``   : fragment SVG inline (à insérer dans du HTML).
* ``css_mask(name)``    : data-URI encodée pour les masques CSS
                          (utilisée par la nav du sidebar).
* ``logo(size)``        : le logo plein « bouclier + flocon » de la marque.
"""
from __future__ import annotations

from urllib.parse import quote

# ---------------------------------------------------------------------------
# Corps des icônes : uniquement le contenu interne du <svg> (paths, lignes…).
# ---------------------------------------------------------------------------
_PATHS: dict[str, str] = {
    # -- Navigation -----------------------------------------------------------
    "tower": (  # tour de contrôle : ondes radio autour d'un point
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/>'
        '<path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/>'
        '<path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/>'
        '<path d="M19.1 4.9C23 8.8 23 15.2 19.1 19.1"/>'
    ),
    "fridge": (  # réfrigérateur
        '<rect x="5" y="2" width="14" height="20" rx="2"/>'
        '<line x1="5" y1="10" x2="19" y2="10"/>'
        '<line x1="15" y1="5" x2="15" y2="7"/>'
        '<line x1="15" y1="13" x2="15" y2="16"/>'
    ),
    "forecast": (  # courbe de prévision (tendance baissière)
        '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/>'
        '<polyline points="16 17 22 17 22 11"/>'
    ),
    "file-text": (  # fiche / brief SBAR
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/>'
        '<line x1="10" y1="9" x2="8" y2="9"/>'
    ),
    "check-circle": (  # validation
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
    ),
    "pipeline": (  # nœuds de pipeline (workflow)
        '<rect x="3" y="3" width="8" height="8" rx="2"/>'
        '<path d="M7 11v4a2 2 0 0 0 2 2h4"/>'
        '<rect x="13" y="13" width="8" height="8" rx="2"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
        '<path d="M3 12a9 3 0 0 0 18 0"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="16" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12.01" y2="8"/>'
    ),
    # -- Statuts & alertes ------------------------------------------------------
    "flag": (  # drapeau d'alerte
        '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>'
        '<line x1="4" y1="22" x2="4" y2="15"/>'
    ),
    "thermometer": (
        '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>'
    ),
    "alert-triangle": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
    ),
    "x-circle": (
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="15" y1="9" x2="9" y2="15"/>'
        '<line x1="9" y1="9" x2="15" y2="15"/>'
    ),
    "activity": (  # pouls / système vivant
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
    ),
    "eye": (  # en un coup d'œil
        '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    # -- Métier -----------------------------------------------------------------
    "package": (  # carton / lot
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<polyline points="3.29 7 12 12 20.71 7"/>'
        '<line x1="12" y1="22" x2="12" y2="12"/>'
    ),
    "pill": (  # médicament
        '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/>'
        '<path d="m8.5 8.5 7 7"/>'
    ),
    "snowflake": (  # chaîne du froid
        '<line x1="2" y1="12" x2="22" y2="12"/>'
        '<line x1="12" y1="2" x2="12" y2="22"/>'
        '<path d="m20 16-4-4 4-4"/>'
        '<path d="m4 8 4 4-4 4"/>'
        '<path d="m16 4-4 4-4-4"/>'
        '<path d="m8 20 4-4 4 4"/>'
    ),
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
    ),
    "user": (
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
        '<circle cx="12" cy="7" r="4"/>'
    ),
    "book-open": (  # protocoles / sources documentaires
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    # -- Technique / pipeline -----------------------------------------------------
    "chip": (  # puce / capteur
        '<rect x="4" y="4" width="16" height="16" rx="2"/>'
        '<rect x="9" y="9" width="6" height="6"/>'
        '<line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>'
        '<line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>'
        '<line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/>'
        '<line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>'
    ),
    "zap": (  # flux / streaming
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
    ),
    "bar-chart": (  # qualité des données
        '<line x1="12" y1="20" x2="12" y2="10"/>'
        '<line x1="18" y1="20" x2="18" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="16"/>'
    ),
    "layers": (  # stack
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
        '<polyline points="2 17 12 22 22 17"/>'
        '<polyline points="2 12 12 17 22 12"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    ),
    "refresh": (
        '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>'
        '<path d="M21 3v5h-5"/>'
        '<path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>'
        '<path d="M3 21v-5h5"/>'
    ),
    "send": (  # transmission
        '<line x1="22" y1="2" x2="11" y2="13"/>'
        '<polygon points="22 2 15 22 11 13 2 9 22 2"/>'
    ),
    # -- Flèches & liens ----------------------------------------------------------
    "arrow-right": (
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        '<polyline points="12 5 19 12 12 19"/>'
    ),
    "arrow-up-right": (
        '<line x1="7" y1="17" x2="17" y2="7"/>'
        '<polyline points="7 7 17 7 17 17"/>'
    ),
    "chevron-right": (
        '<polyline points="9 18 15 12 9 6"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
    ),
    "check": (
        '<polyline points="20 6 9 17 4 12"/>'
    ),
}


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def icon(name: str, *, size: int = 18, color: str = "currentColor",
         stroke_width: float = 1.8, cls: str = "") -> str:
    """Retourne un fragment SVG inline prêt à être injecté dans du HTML.

    ``color`` par défaut = ``currentColor`` : l'icône hérite de la couleur
    du texte qui l'entoure (règle du design system).
    """
    body = _PATHS.get(name) or _PATHS["info"]
    cls_attr = f' class="{cls}"' if cls else ""
    return (
        f'<svg{cls_attr} width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false" '
        f'style="flex-shrink:0;vertical-align:-3px;">{body}</svg>'
    )


def css_mask(name: str) -> str:
    """Retourne une data-URI encodée pour usage en ``mask-image`` CSS.

    Le masque ne garde que la forme : la couleur vient du
    ``background-color`` de l'élément (donc de ``currentColor``).
    """
    body = _PATHS.get(name) or _PATHS["info"]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="black" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return f"url(\"data:image/svg+xml,{quote(svg)}\")"


# ---------------------------------------------------------------------------
# Logo : bouclier (protection, sécurité patient) + flocon (chaîne du froid).
# Forme pleine, dégradé vert #10B981 vers #0F766E.
# « Protéger la chaîne du froid », littéralement.
# ---------------------------------------------------------------------------
_LOGO_COUNTER = 0


def logo(size: int = 38) -> str:
    """Retourne le logo plein en SVG inline.

    Un id de dégradé unique est généré à chaque appel pour éviter les
    collisions d'``id`` quand le logo apparaît plusieurs fois dans le DOM.
    """
    global _LOGO_COUNTER
    _LOGO_COUNTER += 1
    gid = f"msgrad{_LOGO_COUNTER}"
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
     xmlns="http://www.w3.org/2000/svg" aria-label="Vigistock"
     style="flex-shrink:0;">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#10B981"/>
      <stop offset="1" stop-color="#0F766E"/>
    </linearGradient>
  </defs>
  <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"
        fill="url(#{gid})"/>
  <g stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round">
    <line x1="12" y1="6.4" x2="12" y2="16.6"/>
    <line x1="7.9" y1="9" x2="16.1" y2="14"/>
    <line x1="16.1" y1="9" x2="7.9" y2="14"/>
    <path d="m10.6 7.4 1.4 1.1 1.4-1.1" fill="none"/>
    <path d="m10.6 15.6 1.4-1.1 1.4 1.1" fill="none"/>
  </g>
</svg>"""


def logo_standalone() -> str:
    """Version autonome du logo (fichier ``assets/logo.svg``)."""
    return """<svg width="96" height="96" viewBox="0 0 24 24" fill="none"
     xmlns="http://www.w3.org/2000/svg" aria-label="Vigistock">
  <defs>
    <linearGradient id="msgrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#10B981"/>
      <stop offset="1" stop-color="#0F766E"/>
    </linearGradient>
  </defs>
  <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"
        fill="url(#msgrad)"/>
  <g stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round">
    <line x1="12" y1="6.4" x2="12" y2="16.6"/>
    <line x1="7.9" y1="9" x2="16.1" y2="14"/>
    <line x1="16.1" y1="9" x2="7.9" y2="14"/>
    <path d="m10.6 7.4 1.4 1.1 1.4-1.1" fill="none"/>
    <path d="m10.6 15.6 1.4-1.1 1.4 1.1" fill="none"/>
  </g>
</svg>
"""
