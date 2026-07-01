"""Brief SBAR : aide clinique à la substitution médicamenteuse.

Intention UX
------------
Surface *cognitive* de l'app : un formulaire compact à gauche, un brief
généré à droite. Tout est structuré autour du SBAR (Situation / Background /
Assessment / Recommendation) : le format standard de transmission
infirmier-médecin enseigné dans tous les IFSI, utilisé partout dans le monde.

Pourquoi ``st.write_stream``
-----------------------------
Un pharmacien ne va pas attendre 8 secondes pour lire 4 paragraphes d'un coup.
Le streaming lui permet de commencer à lire la *Situation* pendant que
l'*Assessment* est encore en cours de génération : latence perçue divisée
par deux.

Langage : métier pur. Le « comment c'est calculé » vit dans l'expander
« Comment ça marche ? », pas dans la surface de lecture.
"""
from __future__ import annotations

import streamlit as st
from lib import components as C
from lib import llm_logic as L
from lib.data import M
from lib.settings import get_settings
from lib.theme import TOK

# ---------------------------------------------------------------------------
# En-tête de page
# ---------------------------------------------------------------------------
C.page_header(
    eyebrow="Aide clinique",
    icon="file-text",
    title="Brief SBAR",
    subtitle=(
        "Un brief de substitution prêt à transmettre, sources cliniques à "
        "l'appui. Validation pharmacien obligatoire avant transmission."
    ),
    tip=(
        "Le brief est généré par un modèle de langage local (aucune donnée ne "
        "sort de l'hôpital), appuyé sur les protocoles ANSM / OMS / NICE "
        "indexés. Chaque affirmation est citée."
    ),
)


# ---------------------------------------------------------------------------
# Colonne formulaire / colonne sortie
# ---------------------------------------------------------------------------
form_col, output_col = st.columns([1, 1.6], gap="large")

with form_col:
    C.section_header("Contexte", icon="search",
                     subtitle="sources retrouvées automatiquement")

    # médicament par défaut issu d'une page précédente (frigos ou prévision)
    default_drug = st.session_state.get("copilot_drug", "Influenza vaccine (inactivated)|J07BB02")
    if isinstance(default_drug, str) and "|" in default_drug:
        default_drug_name, default_atc = default_drug.split("|", 1)
    else:
        default_drug_name, default_atc = default_drug, ""

    with st.form("copilot_form", border=False):
        choices = [f"{d[0]}|{d[1]}" for d in M.DRUGS]
        try:
            idx = next(i for i, c in enumerate(choices)
                       if c.startswith(default_drug_name))
        except StopIteration:
            idx = 0
        drug = st.selectbox(
            "Médicament concerné",
            choices,
            index=idx,
            format_func=lambda s: f"{s.split(chr(124))[0]} ({s.split(chr(124))[1]})",
        )

        ctx = st.selectbox(
            "Contexte clinique",
            [
                "Hospitalisation",
                "Ambulatoire / consultation",
                "Service d'urgence",
                "Pédiatrie",
                "Gériatrie",
            ],
            index=0,
        )

        horizon = st.selectbox("Horizon prévisionnel",
                               ["7 jours", "14 jours", "30 jours"], index=1)

        nurse_note = st.text_area(
            "Note infirmière (optionnel)",
            placeholder="Ex : patient allergique à l'arachide, schéma de titration en cours…",
            height=110,
        )

        submitted = st.form_submit_button("Générer le brief SBAR", type="primary",
                                          use_container_width=True)

    # Panneau latéral : comment ça marche ------------------------------------
    _s = get_settings()
    _llm_line = (
        f"3. Le modèle local ({_s.ollama_model}) rédige le brief mot à "
        "mot, en citant ses sources. *(Mode démo actif : le brief est "
        "pré-écrit et le streaming est simulé.)*"
        if _s.use_llm_mock else
        f"3. Le modèle local ({_s.ollama_model}, via Ollama) rédige le "
        "brief mot à mot, en citant ses sources."
    )
    with st.expander("Comment ça marche ?", expanded=False):
        st.markdown(
            f"""
            **Le chemin d'un brief**

            1. Votre contexte devient une consigne SBAR structurée.
            2. Les protocoles indexés (ANSM / OMS / NICE) sont interrogés :
               3 à 5 extraits pertinents sont retrouvés, avec leur score.
            {_llm_line}
            4. Le pharmacien lit, coche les 4 critères de validation puis
               transmet au prescripteur. L'infirmier(ère) effectue la
               vérification 5B au lit du patient.

            **Pourquoi SBAR ?**
            Standard mondial de transmission clinique (US Navy puis OMS puis NHS).
            Réduit l'ambiguïté, calque les transmissions infirmières.
            """
        )

# Colonne de sortie -----------------------------------------------------------
with output_col:
    if not submitted and "last_brief" not in st.session_state:
        # État vide : aucun brief encore généré
        C.callout(
            "<strong>Aucun brief généré pour l'instant.</strong> "
            "Remplissez le formulaire à gauche et cliquez sur "
            "<em>Générer le brief SBAR</em>. Le brief s'écrit mot à mot : "
            "vous pouvez commencer à le lire dès la première ligne.",
        )
        st.markdown(
            f"""
            <div style="margin-top:1rem;display:grid;grid-template-columns:repeat(2,1fr);
                        gap:.5rem;font-size:.85rem;color:{TOK.text_secondary};">
              <div><b>S</b>ituation : ce qui a déclenché l'alerte</div>
              <div><b>B</b>ackground : molécule, signal pénurie, contexte</div>
              <div><b>A</b>ssessment : risque clinique + justification</div>
              <div><b>R</b>ecommendation : décision proposée</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Si nouvelle soumission, construire un brief ; sinon réafficher le dernier
        if submitted:
            drug_name, _, atc = drug.partition("|")
            brief = L.build_brief(drug_name)
            st.session_state["last_brief"] = brief
            st.session_state["last_form"] = {
                "drug": drug_name, "atc": atc, "ctx": ctx,
                "horizon": horizon, "nurse_note": nurse_note,
            }

        brief = st.session_state["last_brief"]
        form = st.session_state["last_form"]

        # Carte d'en-tête du brief -------------------------------------------
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                        border-radius:var(--ms-radius-lg);padding:1rem 1.15rem;
                        box-shadow:var(--ms-shadow-sm);margin-bottom:1rem;">
              <div style="display:flex;justify-content:space-between;
                          align-items:flex-start;gap:.5rem;">
                <div>
                  <div style="font-size:.7rem;font-weight:700;color:var(--ms-brand);
                              letter-spacing:.12em;text-transform:uppercase;">
                    Brief de substitution SBAR
                  </div>
                  <div style="font-size:1.05rem;font-weight:700;color:var(--ms-text);
                              margin-top:.15rem;">
                    {form['drug']} <span style="font-family:{TOK.font_mono};font-size:.78rem;
                    color:var(--ms-text-2);font-weight:500;
                    background:var(--ms-bg-muted);padding:1px 6px;border-radius:5px;
                    margin-left:.35rem;">{form['atc']}</span>
                  </div>
                  <div style="color:var(--ms-text-2);font-size:.85rem;margin-top:.15rem;">
                    Contexte : <b>{form['ctx']}</b>,
                    horizon : <b>{form['horizon']}</b>
                  </div>
                </div>
                <div>
                  <span class="ms-pill info"><span class="dot"></span>{brief.model}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Texte streamé -----------------------------------------------------
        if submitted:
            with st.container(border=False):
                st.write_stream(L.stream_sbar_text(brief, tps=45))
        else:
            # réafficher le dernier brief sans re-streamer
            for tag, body in [
                ("Situation",      brief.situation),
                ("Background",     brief.background),
                ("Assessment",     brief.assessment),
                ("Recommendation", brief.recommendation),
            ]:
                st.markdown(f"\n**{tag.upper()}**  \n{body}")

        # Alternatives + redistribution + citations (termes professionnels conservés)
        st.markdown("---")

        a_tab, r_tab, c_tab = st.tabs([
            f"Alternatives ({len(brief.alternatives)})",
            f"Redistribution ({len(brief.redistribution)})",
            f"Sources ({len(brief.citations)})",
        ])

        with a_tab:
            st.caption("Substituts de même classe : proposés automatiquement, "
                       "soumis à validation pharmacien.")
            for a in brief.alternatives:
                C.alternative_card(a.name, a.atc_code, a.dosing, a.caveats)

        with r_tab:
            st.caption("Sites du réseau avec surplus utilisable, classés par distance.")
            import pandas as pd
            rdf = pd.DataFrame([{
                "Site": r.site_name,
                "Stock disponible": f"{r.stock} u.",
                "Distance": f"{r.distance_km} km",
            } for r in brief.redistribution])
            st.dataframe(rdf, hide_index=True, use_container_width=True)

        with c_tab:
            st.caption("Extraits des protocoles cliniques indexés (ANSM / OMS / NICE).")
            for c in brief.citations:
                score = f"score {c.score:.2f}" if c.score else ""
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                                border-left:3px solid var(--ms-brand);
                                border-radius:var(--ms-radius-md);padding:.7rem .9rem;
                                margin-bottom:.5rem;">
                      <div style="font-weight:600;color:var(--ms-text);font-size:.875rem;
                                  display:flex;justify-content:space-between;align-items:baseline;">
                        <span>{c.document}, p.{c.page}</span>
                        <span style="font-family:{TOK.font_mono};color:var(--ms-brand);
                                     font-size:.72rem;font-weight:600;">{score}</span>
                      </div>
                      <div style="color:var(--ms-text-2);font-size:.85rem;
                                  font-style:italic;margin-top:.2rem;">
                        « {c.quote} »
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Action : vers la validation ----------------------------------------
        st.markdown("---")
        C.callout(
            "<strong>Ce brief n'est pas dispensable en l'état.</strong> "
            "Il doit être validé par le pharmacien (4 contrôles) puis "
            "vérifié par l'infirmier(ère) au lit du patient (règle des 5B).",
            variant="alert",
        )
        if st.button("Passer à la validation pharmacien",
                     type="primary", use_container_width=True):
            st.switch_page("views/05_validation.py")
