"""À propos : profil autrice, cadrage du problème, stack, gouvernance.

Intention UX
------------
C'est la surface *portfolio*. Un visiteur qui arrive ici dans les deux
premières minutes doit voir :

1. Qui a construit ça et pourquoi (profil double data-engineer / soignante).
2. Quel problème concret ça résout (un paragraphe).
3. La stack, présentée comme une grille compacte.
4. Gouvernance & avertissements (portfolio, pas dispositif médical).
5. Où aller ensuite (CTAs vers les pages clés).
"""
from __future__ import annotations

import streamlit as st
from lib import components as C
from lib import icons as I

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------
C.hero(
    eyebrow="Projet : portfolio data engineering",
    title="Vigistock : chaîne du froid, ruptures, aide clinique",
    subtitle=(
        "Un projet de portfolio qui mêle streaming temps réel, ML "
        "(Prophet), RAG sur LLM local et orchestration Dagster, résolvant "
        "un problème hospitalier concret avec une stack 100 % open source."
    ),
    meta={
        "AUTRICE":     "Lohana Utim",
        "PARCOURS":    "Data Engineer, ex-soignante (6 ans)",
        "STACK":       "Python, Postgres, Kafka, Ollama",
        "STATUT":      "Portfolio, tourne sur un laptop",
    },
)


# ---------------------------------------------------------------------------
# Cadrage du problème
# ---------------------------------------------------------------------------
left, right = st.columns([1.6, 1], gap="large")

with left:
    C.section_header("L'histoire du projet", icon="book-open",
                     subtitle="trois lectures, du concret au technique")

    tab_pb, tab_story, tab_de = st.tabs(
        ["Le problème", "Le scénario de démo", "Ce que montre le projet"])

    with tab_pb:
        st.markdown(
            """
            > *« Lundi, un frigo de pharmacie à Lyon est monté à 14 °C pendant
            > 4 heures. Vendredi, trois hôpitaux du même réseau étaient en
            > rupture du vaccin antigrippal pédiatrique et le médecin de garde
            > a dû appeler dix services pour trouver un substitut. »*

            Les ruptures de médicaments ne sont pas une menace abstraite. La
            **FDA américaine recensait 323 pénuries actives au T1 2024**, le
            plus haut chiffre en dix ans. La **plateforme européenne de
            surveillance EMA** liste en permanence environ 250 pénuries
            actives. Les défaillances de chaîne du froid en sont une cause
            racine fréquente : **l'OMS estime à 25 % la part des vaccins
            dégradés** avant administration, majoritairement à cause
            d'excursions thermiques qui n'ont été remarquées que trop tard.

            Le ou la pharmacien(ne) qui doit aujourd'hui réagir à une rupture
            jongle entre trois outils silotés : un dashboard frigo, un
            système d'inventaire, et une pile de PDF de protocoles de
            substitution. **Vigistock rassemble les trois** en un
            seul pipeline événementiel qui détecte l'excursion, prédit la
            rupture aval, et rédige le brief clinique de substitution.
            """
        )

    with tab_story:
        st.markdown(
            """
            | Étape | Ce qui se passe | Où dans le code |
            |---|---|---|
            | **1. Sense** | Un capteur frigo à Lyon publie température + humidité toutes les 30 s sur Redpanda. | `simulator/` |
            | **2. Detect** | Un consumer Python tague une excursion >8 °C de plus de 2 h en `BREAKAGE_RISK` et marque le lot suspect. | `streaming/consumer.py` |
            | **3. Forecast** | Prophet réentraine le modèle de demande de la région, retire les doses suspectes, prédit la rupture dans 9 jours. | `ml/shortage_forecast.py` |
            | **4. Recommend** | Ollama (phi3:mini) lit les monographies FDA + ANSM via RAG ChromaDB et rédige un brief SBAR de substitution. | `llm/rag/` |
            | **5. Alert** | Grafana lève l'alerte IoT en temps réel ; Streamlit affiche le brief au pharmacien. | `dashboards/streamlit/` |

            En résumé : **une dérive de capteur devient un plan d'action
            clinique en moins d'une minute, sources à l'appui.**
            """
        )

    with tab_de:
        st.markdown(
            """
            Ce repo montre, dans un seul projet :

            - **Streaming temps réel** avec sémantique at-least-once
              (Redpanda puis consumer Python puis hypertable Timescale +
              continuous aggregates).
            - **Lambda architecture bien faite** : streaming pour la
              télémétrie, batch pour les APIs publiques lentes, les deux
              dans le même time-series store.
            - **Détection d'anomalie en flight** (rolling Z-score + seuil
              de durée), pas en post-hoc.
            - **ML production-shape** : Prophet réentraîné sur schedule
              Dagster, prédictions écrites en Postgres, évaluées via
              backtests.
            - **Pattern RAG moderne** : chunk, embed, vector store,
              retrieval, LLM, avec citations à la source PDF.
            - **Data governance santé** : patterns compatibles HIPAA &
              RGPD documentés dans `docs/governance_hipaa_rgpd.md`. Aucun
              PHI ne quitte le périmètre : le LLM est local.
            - **CI/CD avec services** (Redpanda + Timescale testcontainers
              dans GitHub Actions).
            """
        )



with right:
    C.section_header("Profil", icon="user")
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                    border-radius:var(--ms-radius-lg);padding:1.25rem;
                    box-shadow:var(--ms-shadow-sm);">
          <div style="display:flex;align-items:center;gap:.75rem;">
            {I.logo(44)}
            <div>
              <div style="font-weight:700;color:var(--ms-text);">Lohana Utim</div>
              <div style="color:var(--ms-text-2);font-size:.85rem;">Data Engineer, ex-soignante</div>
            </div>
          </div>
          <div style="margin-top:.85rem;color:var(--ms-text-2);font-size:.875rem;
                      line-height:1.8;">
            Profil double :<br/>
            <strong>Data Engineer</strong><br/>
            <strong>Project management</strong><br/>
            <strong>6 ans d'expérience terrain en milieu hospitalier</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    C.section_header("Stack technique", icon="layers")
    items = [
        ("Streaming",     "Redpanda (Kafka API)",              "zap"),
        ("Stockage",      "TimescaleDB + MinIO",               "database"),
        ("Orchestration", "Dagster (software-defined assets)", "pipeline"),
        ("ML",            "Prophet + scikit-learn",            "forecast"),
        ("LLM",           "Ollama (phi3:mini)",                "chip"),
        ("Vector store",  "ChromaDB + bge-small",              "search"),
        ("Dashboards",    "Streamlit, Plotly, Grafana",        "bar-chart"),
        ("Tests",         "pytest + testcontainers",           "check-circle"),
        ("CI",            "GitHub Actions",                    "refresh"),
    ]
    for name, role, icon_name in items:
        C.stack_item(name, role, icon_name)

    C.section_header("Conformité", icon="shield")
    C.callout(
        "<strong>HIPAA / RGPD</strong> : aucun PHI ne quitte le périmètre, "
        "LLM local, journal d'audit en ajout seul. Voir "
        "<code>docs/governance_hipaa_rgpd.md</code>.",
    )
    C.callout(
        "<strong>Avertissement</strong> : ce projet est un portfolio. "
        "Il <em>n'est pas</em> un dispositif médical, pas certifié CE/FDA, "
        "et ne doit pas être utilisé en production hospitalière.",
        variant="alert",
    )


# ---------------------------------------------------------------------------
# CTAs vers les pages clés
# ---------------------------------------------------------------------------
C.section_header("Continuer la visite", icon="arrow-right",
                 subtitle="trois angles d'entrée")

c1, c2, c3 = st.columns(3, gap="small")
with c1:
    st.markdown(
        """
        <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                    border-radius:var(--ms-radius-md);padding:1rem;height:100%;">
          <div style="font-size:.7rem;color:var(--ms-secondary);text-transform:uppercase;
                      letter-spacing:.08em;font-weight:700;">Architecture</div>
          <div style="font-weight:700;color:var(--ms-text);margin-top:.25rem;">
            L'architecture du pipeline
          </div>
          <div style="color:var(--ms-text-2);font-size:.875rem;margin:.5rem 0;">
            Pipeline détaillé, cloud-mapping, choix techniques motivés.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="link_visit_archi"):
        if st.button("Ouvrir l'architecture du pipeline", key="btn_visit_archi"):
            st.switch_page("views/06_architecture.py")

with c2:
    st.markdown(
        """
        <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                    border-radius:var(--ms-radius-md);padding:1rem;height:100%;">
          <div style="font-size:.7rem;color:var(--ms-secondary);text-transform:uppercase;
                      letter-spacing:.08em;font-weight:700;">Data engineering</div>
          <div style="font-weight:700;color:var(--ms-text);margin-top:.25rem;">
            La qualité des données
          </div>
          <div style="color:var(--ms-text-2);font-size:.875rem;margin:.5rem 0;">
            Asset checks Dagster, contrats de fraîcheur, drift RAG.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="link_visit_quality"):
        if st.button("Ouvrir la qualité des données", key="btn_visit_quality"):
            st.switch_page("views/07_data_quality.py")

with c3:
    st.markdown(
        """
        <div style="background:#FFFFFF;border:1px solid var(--ms-border);
                    border-radius:var(--ms-radius-md);padding:1rem;height:100%;">
          <div style="font-size:.7rem;color:var(--ms-brand);text-transform:uppercase;
                      letter-spacing:.08em;font-weight:700;">Clinique</div>
          <div style="font-weight:700;color:var(--ms-text);margin-top:.25rem;">
            Le brief SBAR
          </div>
          <div style="color:var(--ms-text-2);font-size:.875rem;margin:.5rem 0;">
            Brief de substitution en direct, validation 4 critères + 5B.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="link_visit_sbar"):
        if st.button("Ouvrir le brief SBAR", key="btn_visit_sbar"):
            st.switch_page("views/04_clinical_copilot.py")
