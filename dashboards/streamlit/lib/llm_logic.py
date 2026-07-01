"""Logique LLM synchrone : adaptée au modèle d'exécution Streamlit.

On conserve la structure SBAR (Situation / Background / Assessment /
Recommendation) de la version FastAPI, mais le streamer est réécrit en
générateur *synchrone* pour s'insérer directement dans ``st.write_stream``.

Streamlit réexécute tout le script à chaque interaction ; bloquer sur un
générateur est la façon idiomatique de diffuser les tokens. Pas de
plomberie SSE nécessaire.

Le chemin live appelle toujours Ollama pour les utilisateurs qui veulent
un vrai LLM ; le chemin mock émet les trois cas pré-enregistrés utilisés
dans la version FastAPI, à une cadence réaliste pour que l'UX de streaming
soit testable hors ligne.
"""
from __future__ import annotations

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

try:
    import httpx  # optional: only needed for the live Ollama path
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from .settings import get_settings


# ---------------------------------------------------------------------------
# Modèle de données
# ---------------------------------------------------------------------------
@dataclass
class Citation:
    document: str
    page: int | str
    quote: str
    score: float | None = None


@dataclass
class Alternative:
    name: str
    atc_code: str
    dosing: str
    caveats: str


@dataclass
class Redistribution:
    site_name: str
    stock: int
    distance_km: int


@dataclass
class SBARBrief:
    drug_name:      str
    situation:      str
    background:     str
    assessment:     str
    recommendation: str

    alternatives:   list[Alternative]    = field(default_factory=list)
    citations:      list[Citation]       = field(default_factory=list)
    redistribution: list[Redistribution] = field(default_factory=list)

    model:        str       = ""
    generated_at: datetime  = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Corpus mock : trois scénarios de substitution réalistes
# ---------------------------------------------------------------------------
_MOCK_CORPUS: dict[str, dict] = {
    "vaccine": dict(
        situation=(
            "BREAKAGE_RISK F-01-03 (CHU Lyon-Sud) : sortie de zone 2-8 °C pendant "
            "72 min, pic à 9.4 °C. Lot VAX-2026-0142 (640 doses) potentiellement "
            "compromis."
        ),
        background=(
            "Vaccin antigrippal inactivé Influvac Tetra, ATC J07BB02. Campagne "
            "saisonnière en cours. Signal FDA shortage 2026-04 actif sur le "
            "J07BB02 jusque Q3 2026."
        ),
        assessment=(
            "Stabilité documentée jusqu'à 25 °C × 24 h (ANSM 2024-03), donc le "
            "lot reste théoriquement utilisable. Mais alerte BREAKAGE_RISK + "
            "pénurie active = quarantaine prudente recommandée. Substitution "
            "intra-classe disponible sur site partenaire."
        ),
        recommendation=(
            "1) Mettre VAX-2026-0142 en quarantaine, ne pas administrer. "
            "2) Demander 420 doses Influvac Tetra à CHU Lyon-Nord (12 km). "
            "3) Si refus, basculer sur Vaxigrip Tetra (même ATC). "
            "4) Prescripteur : confirmer avant retour en stock dispensable."
        ),
        alternatives=[
            Alternative("Influvac Tetra", "J07BB02",
                        "0.5 mL IM dose unique ≥18 ans",
                        "Allergie protéines œuf · différer si fébrile."),
            Alternative("Vaxigrip Tetra", "J07BB02",
                        "0.5 mL IM ≥6 mois (schéma pédiatrique adapté)",
                        "Latex dans le bouchon : vérifier dossier allergies."),
        ],
        citations=[
            Citation("ANSM_FluVax_2024-03.pdf", 3,
                     "Stabilité immunogénique acceptable jusqu'à 25 °C / 24 h.", 0.91),
            Citation("WHO_VVM_Guidance.pdf", 12,
                     "VVM grade 3 = exposition cumulée proche du seuil de rejet.", 0.84),
            Citation("Hospital_SOP_Vaccines_v4.docx", 7,
                     "Mise en quarantaine de tout lot ayant déclenché une alerte.", 0.78),
        ],
        redistribution=[
            Redistribution("CHU Lyon-Nord", 420, 12),
            Redistribution("Pharmacie Centrale Grenoble", 180, 104),
        ],
    ),
    "insulin": dict(
        situation=(
            "Stock insuline glargine A10AE04 à J-7 sur Hôpital Cochin "
            "(320 unités restantes). Probabilité rupture 14 j : 61 %."
        ),
        background=(
            "Insuline basale longue durée. Instabilité thermique >30 °C. "
            "Patients diabétiques de type 1 et type 2 insulino-dépendants."
        ),
        assessment=(
            "Risque de rupture concret à 14 jours. Substitution par un autre "
            "analogue basal (detemir / degludec) avec ratio 0.8× possible "
            "selon NICE NG28 (2023). Nécessite ajustement individuel."
        ),
        recommendation=(
            "1) Rebascule programmée vers Levemir (detemir) ou Tresiba (degludec). "
            "2) Ratio initial 0.8 × dose glargine, puis titration sur 3 jours. "
            "3) Surveillance glycémique renforcée x4/j. "
            "4) Médecin : valider la conversion par patient avant ordonnance."
        ),
        alternatives=[
            Alternative("Insuline detemir (Levemir)", "A10AE05",
                        "0.8 × dose glargine actuelle, OD ou BID",
                        "~30 % des patients passent à 2 inj/jour."),
            Alternative("Insuline degludec (Tresiba)", "A10AE06",
                        "0.8 × dose glargine, OD",
                        "Demi-vie longue : prudence en insuffisance rénale."),
        ],
        citations=[
            Citation("NICE_NG28_2023.pdf", 44,
                     "Detemir ou degludec sont des substituts basaux acceptables si glargine indisponible.", 0.93),
            Citation("EMA_Insulin_StorageGuide.pdf", 9,
                     "Éviter températures >30 °C ; rejeter si exposition ≥24 h.", 0.88),
        ],
        redistribution=[Redistribution("Hôpital de la Croix-Rousse", 96, 4)],
    ),
    "antibiotic": dict(
        situation=(
            "Signal pénurie FDA 2026-04 sur amoxicilline/clavulanate (J01CR02). "
            "Stock CHU Bordeaux à 1450 unités, projection rupture J+23."
        ),
        background=(
            "Antibiotique de première ligne en infection respiratoire "
            "communautaire et infections cutanées. Beta-lactamine + inhibiteur "
            "de β-lactamases."
        ),
        assessment=(
            "Pénurie modérée, fenêtre de réapprovisionnement Q3 2026. "
            "Désescalade vers PO si infection non sévère, ou bascule "
            "céphalosporine 2G en IV."
        ),
        recommendation=(
            "1) Désescalade IV vers PO dès J3 si critères Quick Switch remplis. "
            "2) Alternative IV : céfuroxime 750 mg × 3/j. "
            "3) Vérifier allergie pénicilline avant chaque substitution. "
            "4) Antibiogramme si disponible avant tout changement."
        ),
        alternatives=[
            Alternative("Amoxicilline/clavulanate (PO)", "J01CR02",
                        "875 mg / 125 mg PO × 2/j × 7 jours",
                        "À éviter si allergie pénicilline (~10 % cohorte)."),
            Alternative("Céfuroxime IV", "J01DC02",
                        "750 mg IV × 3/j",
                        "Cross-réactivité allergie pénicilline ~2 %."),
        ],
        citations=[
            Citation("IDSA_Sepsis_2021.pdf", 22,
                     "Désescalade empirique recommandée dès cultures disponibles.", 0.86),
            Citation("FDA_Shortage_Bulletin_2026-04.json", 1,
                     "Pénurie sur la classe béta-lactamine X, résolution prévue Q3 2026.", 0.79),
        ],
        redistribution=[Redistribution("CHU Saint-Étienne", 240, 78)],
    ),
}


def _pick_corpus(drug_name: str) -> dict:
    n = (drug_name or "").lower()
    if any(k in n for k in ("vac", "flu", "influ", "mmr")):
        return _MOCK_CORPUS["vaccine"]
    if any(k in n for k in ("insulin", "glargine", "detemir")):
        return _MOCK_CORPUS["insulin"]
    if any(k in n for k in ("amox", "ceftri", "antib", "clav")):
        return _MOCK_CORPUS["antibiotic"]
    return _MOCK_CORPUS[random.Random(n).choice(list(_MOCK_CORPUS.keys()))]


def build_brief(drug_name: str) -> SBARBrief:
    """Retourne le brief structuré (non streamé) : utilisé pour rendre les
    panneaux alternatives / citations / redistribution.

    ``USE_LLM_MOCK=false`` emprunte le vrai chemin RAG (ChromaDB + Ollama +
    validation d'ancrage, llm/rag/brief.py) ; toute erreur retombe sur le
    corpus mock, en loggant la bascule : la démo ne casse jamais.
    """
    s = get_settings()
    if not s.use_llm_mock:
        try:
            return _build_brief_live(drug_name)
        except Exception as exc:
            import logging
            logging.getLogger("vigistock.llm").warning(
                "brief RAG live indisponible pour %s, repli mock : %s",
                drug_name, exc,
            )
    c = _pick_corpus(drug_name)
    return SBARBrief(
        drug_name=drug_name,
        situation=c["situation"],
        background=c["background"],
        assessment=c["assessment"],
        recommendation=c["recommendation"],
        alternatives=c["alternatives"],
        citations=c["citations"],
        redistribution=c["redistribution"],
        model=s.ollama_model + " (mock)",
    )


def _build_brief_live(drug_name: str) -> SBARBrief:
    """Chemin RAG réel : contexte tiré du pipeline, génération par
    llm/rag/brief.generate_substitution_brief, mapping vers le format SBAR.

    Le contexte (lot affecté, site, jours avant rupture) provient des mêmes
    fonctions live que le reste du dashboard : le brief parle des MÊMES
    excursions et des MÊMES stocks que les pages Overview et Prévision.
    """
    import uuid as _uuid

    from llm.rag.brief import generate_substitution_brief

    from . import live_data

    # 1. Contexte : lot affecté par une excursion en cours pour ce médicament.
    affected = live_data.excursion_affected_drugs()
    entry = next(
        ((atc, a) for atc, a in affected.items()
         if a["drug_name"].lower() == (drug_name or "").lower()),
        None,
    )
    if entry is None:
        raise ValueError(f"aucune excursion en cours n'affecte {drug_name!r}")
    atc, aff = entry

    overview = live_data.shortage_overview()
    fc = next((d for d in overview if d["atc_code"] == atc), None)
    days_left = fc["horizon_days"] if fc else 30
    severity = "BREAKAGE_RISK"

    brief = generate_substitution_brief(
        alert_id=f"ui-{_uuid.uuid4().hex[:12]}",
        drug_id=atc,
        drug_name=drug_name,
        site_id=_site_id_of(aff["site"]),
        site_name=aff["site"],
        lot_id=aff["lot"],
        suspect_doses=aff["doses"],
        days_to_stockout=days_left,
        severity=severity,
    )

    # 2. Mapping Brief (validé, llm/rag/validator) vers SBARBrief (contrat UI).
    s = get_settings()
    alternatives = [
        Alternative(
            name=a.name, atc_code=a.atc,
            dosing=a.posology_note or "se référer au protocole cité",
            caveats="; ".join(f"{c.doc} p.{c.page}" for c in a.citations)
                    or "voir protocole source",
        )
        for a in brief.alternatives
    ]
    citations = [
        Citation(document=c.doc, page=c.page,
                 quote="citation ancrée dans le protocole indexé", score=None)
        for a in brief.alternatives for c in a.citations
    ]
    redistribution = [
        Redistribution(
            site_name=_site_name_of(r.site),
            stock=r.surplus_doses,
            distance_km=_distance_km(_site_id_of(aff["site"]), r.site),
        )
        for r in brief.redistribution_candidates
    ]

    prob_txt = (f"probabilité de rupture {int(fc['shortage_prob'] * 100)} % "
                f"sous {days_left} j" if fc else "stock sous tension")
    return SBARBrief(
        drug_name=drug_name,
        situation=(f"{severity} sur {aff['fridge']} ({aff['site']}) : lot "
                   f"{aff['lot']} ({aff['doses']} doses) potentiellement compromis."),
        background=f"{drug_name}, ATC {atc}. Signaux pénurie : {prob_txt}.",
        assessment=brief.reasoning_brief
        or "Contexte documentaire insuffisant : décision au prescripteur.",
        recommendation=(
            "Quarantaine du lot, demande de redistribution prioritaire, "
            "substitution intra-classe selon les alternatives ci-dessous. "
            f"Confiance modèle : {brief.confidence}."
        ),
        alternatives=alternatives,
        citations=citations,
        redistribution=redistribution,
        model=s.ollama_model,
    )


def _site_id_of(site_name: str) -> str:
    """site_name vers site_id via le référentiel (repli : le nom lui-même)."""
    from .live_data import _query
    rows = _query("SELECT site_id FROM silver.dim_sites WHERE site_name = %s",
                  (site_name,))
    return rows[0]["site_id"] if rows else site_name


def _site_name_of(site_id: str) -> str:
    from .live_data import _query
    rows = _query("SELECT site_name FROM silver.dim_sites WHERE site_id = %s",
                  (site_id,))
    return rows[0]["site_name"] if rows else site_id


def _distance_km(site_a: str, site_b: str) -> int:
    """Distance haversine entre deux sites du référentiel (0 si inconnue)."""
    import math

    from .live_data import _query
    rows = _query(
        "SELECT site_id, latitude, longitude FROM silver.dim_sites "
        "WHERE site_id IN (%s, %s)", (site_a, site_b),
    )
    coords = {r["site_id"]: (r["latitude"], r["longitude"]) for r in rows}
    if len(coords) < 2 or any(v[0] is None for v in coords.values()):
        return 0
    (la1, lo1), (la2, lo2) = coords[site_a], coords[site_b]
    rla1, rla2 = math.radians(la1), math.radians(la2)
    dla, dlo = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dla / 2) ** 2 + math.cos(rla1) * math.cos(rla2) * math.sin(dlo / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)))


# ---------------------------------------------------------------------------
# Flux synchrone : consommé directement par st.write_stream(...)
# ---------------------------------------------------------------------------
def stream_sbar_text(brief: SBARBrief, *, tps: float = 40.0) -> Iterator[str]:
    """Émet le brief SBAR mot par mot sous forme d'un flux de texte unique.

    Les sections sont séparées par une petite ligne d'en-tête pour que le
    lecteur puisse parcourir la Situation pendant que le reste est encore
    en cours de streaming.
    """
    delay = 1.0 / tps
    for tag, body in [
        ("SITUATION",      brief.situation),
        ("BACKGROUND",     brief.background),
        ("ASSESSMENT",     brief.assessment),
        ("RECOMMENDATION", brief.recommendation),
    ]:
        yield f"\n\n**{tag}**  \n"
        for w in body.split():
            yield w + " "
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Sondes de santé : synchrones
# ---------------------------------------------------------------------------
def ollama_health() -> dict:
    s = get_settings()
    if s.use_llm_mock or httpx is None:
        return {"ok": True, "mode": "mock", "model": s.ollama_model, "latency_ms": 0}
    try:
        t0 = time.time()
        r = httpx.get(f"{s.ollama_host}/api/tags", timeout=2.0)
        r.raise_for_status()
        latency_ms = int((time.time() - t0) * 1000)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"ok": s.ollama_model in models, "mode": "live",
                "model": s.ollama_model, "available": models,
                "latency_ms": latency_ms}
    except Exception as exc:
        return {"ok": False, "mode": "unreachable", "error": str(exc)}


def kafka_health() -> dict:
    s = get_settings()
    if s.use_llm_mock:
        return {"ok": True, "mode": "mock", "broker": "mock"}
    host, _, port = s.redpanda_brokers.partition(":")
    import socket
    try:
        with socket.create_connection((host, int(port or 9092)), timeout=1.5):
            return {"ok": True, "mode": "live", "broker": s.redpanda_brokers}
    except Exception as exc:
        return {"ok": False, "mode": "unreachable", "error": str(exc)}
