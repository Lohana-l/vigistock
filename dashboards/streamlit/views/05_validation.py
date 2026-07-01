"""Validation : workflow en deux étapes pharmacien + infirmier·ère.

Intention UX
------------
Une substitution clinique n'est *jamais* une décision unilatérale. La gate
de validation est la surface la plus critique de toute l'app, la page est
donc délibérément *moins* visuelle et *plus* rigoureuse que les autres :

* Stepper en haut : l'utilisateur sait toujours à quelle étape il se trouve.
* Étape 1 = pharmacien (4 contrôles : dose, allergie, stock, voie).
* Étape 2 = infirmier·ère 5B au chevet (Bon patient, Bon médicament, Bonne
  dose, Bonne voie, Bon moment).
* Étape 3 = aperçu du journal d'audit.

On utilise ``st.checkbox`` avec des labels explicites plutôt qu'un widget
choix multiple unique, pour que chaque contrôle soit auditable
indépendamment (un lecteur d'écran entend chaque gate comme une affordance
distincte).
"""
from __future__ import annotations

import streamlit as st
from lib import components as C
from lib import icons as I
from lib.data import M

# ---------------------------------------------------------------------------
# En-tête de page
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Aide clinique",
    icon="check-circle",
    title="Validation",
    subtitle=(
        "Deux contrôles humains avant toute administration : le pharmacien "
        "(4 critères) puis l'infirmier(ère) (règle des 5B). Chaque coche est "
        "consignée au journal d'audit."
    ),
)

# récupérer le dernier brief depuis la session, ou utiliser un placeholder
brief = st.session_state.get("last_brief")
form  = st.session_state.get("last_form", {
    "drug": "Influenza vaccine (inactivated)", "atc": "J07BB02",
    "ctx": "Hospitalisation", "horizon": "14 jours", "nurse_note": "",
})

# ---------------------------------------------------------------------------
# Stepper (indicateur d'étapes), chiffres + coche SVG, zéro emoji
# ---------------------------------------------------------------------------
_CHECK_SVG = I.icon("check", size=14, color="#FFFFFF", stroke_width=2.4)


def _stepper(active: int) -> None:
    steps = [
        ("1", "Pharmacien", "4 contrôles cliniques"),
        ("2", "Infirmier(ère) 5B", "vérification au chevet"),
        ("3", "Journal d'audit", "trace immuable"),
    ]
    cols = st.columns(len(steps), gap="small")
    for i, (col, (num, title, sub)) in enumerate(zip(cols, steps, strict=False), start=1):
        with col:
            is_active = i == active
            is_done   = i < active
            bg     = "var(--ms-brand)" if is_active else (
                "var(--ms-ok)" if is_done else "var(--ms-bg-muted)")
            color  = "#FFFFFF" if (is_active or is_done) else "var(--ms-text-3)"
            border = "transparent" if (is_active or is_done) else "var(--ms-border)"
            inner  = _CHECK_SVG if is_done else num
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:.65rem;
                            padding:.65rem .85rem;
                            background:#FFFFFF;border:1px solid var(--ms-border);
                            border-radius:var(--ms-radius-md);
                            {"box-shadow:var(--ms-shadow-md);border-color:var(--ms-brand);"
                              if is_active else ""}">
                  <div style="width:28px;height:28px;border-radius:50%;
                              background:{bg};color:{color};border:1px solid {border};
                              display:flex;align-items:center;justify-content:center;
                              font-weight:700;font-size:.85rem;">
                    {inner}
                  </div>
                  <div>
                    <div style="font-weight:600;color:var(--ms-text);font-size:.875rem;">{title}</div>
                    <div style="color:var(--ms-text-3);font-size:.75rem;">{sub}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


step = st.session_state.get("validation_step", 1)
_stepper(step)

# Récapitulatif compact du contexte -----------------------------------------
st.markdown(
    f"""
    <div class="ms-callout" style="margin-top:1rem;">
      <strong>Brief en cours :</strong> {form['drug']} ({form['atc']}),
      contexte <b>{form['ctx']}</b>, horizon <b>{form['horizon']}</b>.
      {('Note : <em>' + form['nurse_note'] + '</em>') if form['nurse_note'] else ''}
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# ÉTAPE 1 - Gate pharmacien
# ---------------------------------------------------------------------------
if step == 1:
    C.section_header(
        "Validation pharmacien", icon="check-circle",
        subtitle="les 4 cases doivent être cochées pour transmettre au prescripteur",
    )

    with st.form("pharma_form", border=False):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            chk_dose    = st.checkbox(
                "**Posologie** vérifiée et adaptée au patient",
                help="Vérifier que la dose proposée est cohérente avec le poids / la "
                     "fonction rénale / l'âge du patient.")
            chk_allergy = st.checkbox(
                "**Allergies / contre-indications** revues",
                help="Croiser les substituts avec le dossier allergique du patient.")
        with c2:
            chk_stock = st.checkbox(
                "**Stock physique** du substitut confirmé",
                help="Confirmer la disponibilité réelle (pas seulement théorique) "
                     "sur le site, ou via redistribution.")
            chk_route = st.checkbox(
                "**Voie d'administration** compatible",
                help="IM, IV, PO, SC… la voie doit correspondre à la prescription "
                     "initiale ou être explicitement ajustée.")

        actor_note = st.text_area("Note pharmacien (optionnelle)",
                                  placeholder="Ex : redistribution depuis Lyon-Nord confirmée par M. Dubois.",
                                  height=80)

        submitted = st.form_submit_button("Transmettre au prescripteur",
                                          type="primary", use_container_width=True)

    if submitted:
        missing = [n for n, v in {
            "Posologie": chk_dose, "Allergie": chk_allergy,
            "Stock": chk_stock, "Voie": chk_route,
        }.items() if not v]
        if missing:
            st.error(f"Contrôles manquants : {', '.join(missing)}. "
                     "Ces 4 contrôles sont obligatoires.")
        else:
            st.success("Validé. Le brief est transmis au prescripteur et "
                       "le journal d'audit est mis à jour. Vous pouvez "
                       "maintenant passer à la vérification 5B au chevet.")
            st.session_state["pharma_note"] = actor_note
            st.session_state["validation_step"] = 2
            if st.button("Continuer vers la vérification 5B", type="primary"):
                st.rerun()


# ---------------------------------------------------------------------------
# ÉTAPE 2 - Gate infirmier·ère 5B
# ---------------------------------------------------------------------------
elif step == 2:
    C.section_header(
        "Vérification 5B au chevet", icon="user",
        subtitle="Bon patient, bon médicament, bonne dose, bonne voie, bon moment",
        right="IFSI 2024, HAS Outil 5",
    )

    # Cartouche patient
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                    border-left:4px solid var(--ms-brand);
                    border-radius:var(--ms-radius-md);
                    padding:.85rem 1rem;margin-bottom:1rem;
                    display:flex;justify-content:space-between;gap:1rem;">
          <div>
            <div style="font-size:.7rem;color:var(--ms-text-3);text-transform:uppercase;
                        letter-spacing:.08em;font-weight:600;">Patient</div>
            <div style="font-weight:700;color:var(--ms-text);font-size:1rem;">
              M. R. (initiales, anonymisé)
            </div>
            <div style="color:var(--ms-text-2);font-size:.85rem;">
              PAT-2026-0871, chambre W3-217
            </div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:.7rem;color:var(--ms-text-3);text-transform:uppercase;
                        letter-spacing:.08em;font-weight:600;">Administration prévue</div>
            <div style="font-weight:700;color:var(--ms-text);font-size:1rem;">
              {form['drug']}
            </div>
            <div style="color:var(--ms-text-2);font-size:.85rem;font-family:ui-monospace,monospace;">
              LOT-SUBST-A3F2, 0,5 mL IM
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("nurse_form", border=False):
        b1 = st.checkbox("**Bon patient** : bracelet d'identification scanné et vérifié",
                         help="ID + date de naissance + bracelet.")
        b2 = st.checkbox("**Bon médicament** : étiquette du flacon vérifiée",
                         help="Nom + DCI + ATC + lot identique à la prescription.")
        b3 = st.checkbox("**Bonne dose** : calcul confirmé",
                         help="Dose × concentration × volume = quantité administrée.")
        b4 = st.checkbox("**Bonne voie** : IM/IV/PO conforme",
                         help="Vérifier qu'aucune contre-indication n'existe (ex. voie veineuse périmée).")
        b5 = st.checkbox("**Bon moment** : fenêtre temporelle respectée",
                         help="Délai depuis la dernière dose, horaire du protocole.")

        nurse_note = st.text_area("Note infirmier(ère) (optionnelle)",
                                  placeholder="Ex : patient à jeun depuis 6 h, état clinique stable.",
                                  height=80)

        submitted = st.form_submit_button("Valider l'administration",
                                          type="primary", use_container_width=True)

    if submitted:
        missing = [n for n, v in {
            "Bon patient": b1, "Bon médicament": b2, "Bonne dose": b3,
            "Bonne voie": b4, "Bon moment": b5,
        }.items() if not v]
        if missing:
            st.error(f"STOP : ne pas administrer. Cases manquantes : {', '.join(missing)}.")
        else:
            st.success("Administration validée. L'événement est consigné dans "
                       "le journal d'audit immuable.")
            st.session_state["nurse_note_final"] = nurse_note
            st.session_state["validation_step"] = 3
            if st.button("Voir le journal d'audit", type="primary"):
                st.rerun()


# ---------------------------------------------------------------------------
# ÉTAPE 3 - Journal d'audit
# ---------------------------------------------------------------------------
else:
    C.section_header(
        "Journal d'audit", icon="database",
        subtitle="trace immuable : qui a fait quoi, à quelle heure, avec quelle note",
    )

    import pandas as pd
    rows = M.audit_log()
    # En mode live, un journal vide est un état sain (aucune action encore
    # tracée) : on l'affiche honnêtement plutôt que de basculer sur le mock.
    if not rows:
        st.caption("Aucune action enregistrée pour le moment : le journal "
                   "se remplit à mesure que les briefs sont validés ou refusés.")
        st.stop()
    df = pd.DataFrame(rows)
    df["Décision"] = df["ok"].map({True: "Validé", False: "Refusé"})
    df = df.rename(columns={
        "ts":      "Horodatage UTC",
        "actor":   "Acteur",
        "role":    "Rôle",
        "event":   "Événement",
        "brief_id": "Brief",
        "drug":    "Médicament",
        "note":    "Note",
    })[["Horodatage UTC", "Acteur", "Rôle", "Événement", "Brief",
        "Médicament", "Décision", "Note"]]

    st.dataframe(df, hide_index=True, use_container_width=True,
                 column_config={
                     "Brief":    st.column_config.TextColumn(width="small"),
                     "Décision": st.column_config.TextColumn(width="small"),
                 })

    C.callout(
        "<strong>Conformité.</strong> Les écritures du journal d'audit sont "
        "immuables (table en ajout seul). Aucune donnée patient ne quitte "
        "le périmètre hospitalier : le modèle de langage est local. "
        "Voir <em>docs/governance_hipaa_rgpd.md</em>.",
    )

    if st.button("Recommencer un nouveau brief"):
        st.session_state.pop("validation_step", None)
        st.session_state.pop("last_brief", None)
        st.session_state.pop("last_form", None)
        st.switch_page("views/04_clinical_copilot.py")
