"""Human readable, evidence grounded rationale for a recommendation."""

from charterloom.catalog import ARCHETYPE_BY_KEY, REGIME_BY_KEY

SIGNAL_DESCRIPTIONS = {
    "requirements_volatility": "requirements are expected to change",
    "scope_fixed": "scope is fixed and baselined",
    "unplanned_work": "a large share of work arrives unplanned",
    "research_uncertainty": "feasibility is uncertain and needs experimentation",
    "multi_team": "delivery spans several teams",
    "dependencies": "cross team dependencies are significant",
    "production_critical": "the service is production critical",
    "change_risk": "production change risk is high",
    "data_migration": "a data migration is involved",
    "ml_component": "a machine learning model is part of the solution",
    "vendor_dependency": "external vendors supply key components",
    "public_facing": "the service is used directly by the public",
    "personal_data": "personal data is processed",
    "high_traffic": "peak traffic is high",
    "many_stakeholders": "the stakeholder group is broad",
    "fixed_deadline": "the deadline is fixed",
    "continuous_deployment": "the team deploys continuously",
    "external_client": "an external client must accept deliverables",
    "hardware": "hardware or firmware constraints apply",
}


def build_rationale(recommendation, profile, methodology_hits, adjustments):
    """Compose a structured explanation that cites the knowledge base."""
    archetype = ARCHETYPE_BY_KEY[recommendation["workflow"]]
    signals = [SIGNAL_DESCRIPTIONS[name] for name, value in sorted(profile.signals.items(), key=lambda x: x[1], reverse=True)
               if value >= 0.5 and name in SIGNAL_DESCRIPTIONS][:6]
    precedents = recommendation["precedents"]
    agreeing = [p for p in precedents if p["workflow_archetype"] == archetype.key]
    summary = (
        f"{archetype.display_name} is recommended with {recommendation['confidence']:.0%} confidence. "
        + (f"The charter indicates that {', '.join(signals[:4])}. " if signals else "")
        + f"{len(agreeing)} of the {len(precedents)} most similar high performing historical projects used this workflow."
    )
    if recommendation["needs_human_review"]:
        summary += " Confidence is below the review threshold, so a delivery lead should confirm the choice."
    alternatives = [
        {"workflow": r["workflow"], "display_name": ARCHETYPE_BY_KEY[r["workflow"]].display_name,
         "probability": r["probability"]}
        for r in recommendation["ranking"][1:]
    ]
    return {
        "summary": summary,
        "charter_signals": signals,
        "regimes": [REGIME_BY_KEY[r].display_name for r in profile.regimes],
        "feature_drivers": recommendation["feature_drivers"],
        "precedent_agreement": round(len(agreeing) / max(1, len(precedents)), 3),
        "alternatives": alternatives,
        "methodology_citations": [
            {"doc_id": h.doc_id, "title": h.title, "section": h.section, "passage": h.to_dict(360)["passage"]}
            for h in methodology_hits
        ],
        "applied_adjustments": [
            {"code": a["code"], "title": a["title"], "score": a["score"],
             "mandated_by_regime": a["mandated_by_regime"], "evidence": a["evidence"][:3]}
            for a in adjustments if a["applied"]
        ],
    }
