"""Deterministic synthesis of the organisational knowledge base.

Real organisations rarely publish their project histories, so Charterloom ships
with a large, statistically coherent synthetic corpus that mirrors what a
mature PMO archive contains:

  historical project blueprints  charter, adopted workflow, configuration and outcome metrics
  post mortem analyses           blameless retrospectives with lessons and recommended adjustments
  workflow templates             the canonical state machines exported as JSON

Generative model
  1. Each project receives latent attributes (type, domain, team shape, volatility,
     interrupt load, research uncertainty, regulatory regimes, criticality and so on).
  2. A transparent utility model scores every workflow archetype against those
     attributes; Gumbel noise models genuine ambiguity. The argmax is the latent
     optimal workflow.
  3. The organisation did not always choose optimally: the adopted workflow is the
     optimum, the runner up or something else, with fixed probabilities.
  4. Outcome quality depends on workflow fit and on whether the adjustments the
     project needed were in place, plus team level noise.
  5. Charter text expresses the latent attributes only probabilistically and adds
     misleading cues, so the text is an imperfect view of the truth.

Latent labels (optimal workflow and needed adjustments) are written to a
separate ground truth file that is used for evaluation only and is never indexed.
"""

import json
from pathlib import Path

import numpy as np

from charterloom.catalog import (
    ADJUSTMENT_CODES,
    ARCHETYPE_BY_KEY,
    ARCHETYPE_KEYS,
    REGIME_BY_KEY,
    REGIME_MANDATED_ADJUSTMENTS,
)
from charterloom.knowledge import vocabulary as V
from charterloom.knowledge.templates import all_templates, describe_template
from charterloom.text import minus


def _clip(value, low=0.0, high=1.0):
    return float(min(high, max(low, value)))


class KnowledgeBaseGenerator:
    """Generate the synthetic organisational archive."""

    SIGNAL_MENTION_PROBABILITY = 0.80
    FALSE_CUE_PROBABILITY = 0.045
    OPTIMAL_ADOPTION_PROBABILITY = 0.58
    RUNNER_UP_ADOPTION_PROBABILITY = 0.27

    def __init__(self, settings):
        self.settings = settings
        self.rng = np.random.default_rng(settings.random_seed)
        self.templates = all_templates()
        self._type_keys = list(V.PROJECT_TYPES)
        weights = np.array([V.PROJECT_TYPES[k]["weight"] for k in self._type_keys], dtype=float)
        self._type_weights = weights / weights.sum()
        self._domain_keys = list(V.DOMAINS)
        self._used_codenames = set()

    # Sampling helpers

    def _choice(self, items):
        return items[int(self.rng.integers(0, len(items)))]

    def _bernoulli(self, p):
        return bool(self.rng.random() < p)

    def _int_between(self, bounds):
        low, high = bounds
        return int(self.rng.integers(low, high + 1))

    def _codename(self):
        for _ in range(50):
            name = f"{self._choice(V.CODENAME_ADJECTIVES)} {self._choice(V.CODENAME_NOUNS)}"
            if name not in self._used_codenames:
                self._used_codenames.add(name)
                return name
        return f"{self._choice(V.CODENAME_ADJECTIVES)} {self._choice(V.CODENAME_NOUNS)} {len(self._used_codenames)}"

    # Latent attributes

    def sample_attributes(self):
        project_type = self._type_keys[int(self.rng.choice(len(self._type_keys), p=self._type_weights))]
        spec = V.PROJECT_TYPES[project_type]
        preferred = spec.get("preferred_domains")
        if preferred and self._bernoulli(0.8):
            domain = self._choice(preferred)
        elif project_type == "regulatory_module" and self._bernoulli(0.45):
            domain = self._choice(["pharmaceuticals", "medical_devices", "financial_services", "insurance"])
        else:
            domain = self._choice(self._domain_keys)
        domain_spec = V.DOMAINS[domain]

        signals = {}
        for name, p in spec["signals"].items():
            signals[name] = self._bernoulli(p)
        # Mutually exclusive groups keep the attributes coherent.
        if signals.get("volatility_high"):
            signals["volatility_medium"] = False
            signals["volatility_low"] = False
        elif signals.get("volatility_medium"):
            signals["volatility_low"] = False
        if signals.get("unplanned_high"):
            signals["unplanned_medium"] = False
        for name in V.SIGNAL_PHRASES:
            signals.setdefault(name, False)

        team_size = self._int_between(spec["team"])
        teams = self._int_between(spec["teams"])
        if signals["multi_team"] and teams < 3:
            teams = int(self.rng.integers(3, 7))
            team_size = max(team_size, teams * 6)
        if teams >= 4:
            signals["multi_team"] = True
        weeks = self._int_between(spec["weeks"])

        regimes = [key for key, p in domain_spec["regimes"].items() if self._bernoulli(p)]
        if self._bernoulli(spec.get("force_strict", 0.0)) and not any(REGIME_BY_KEY[r].strictness >= 2 for r in regimes):
            strict_options = [k for k in domain_spec["regimes"] if REGIME_BY_KEY[k].strictness >= 2]
            regimes.append(self._choice(strict_options or ["sox", "dora", "pci_dss"]))
        if signals.get("personal_data") is False:
            regimes = [r for r in regimes if r not in ("gdpr", "hipaa") or self._bernoulli(0.35)]
        regimes = sorted(set(regimes))

        return {
            "project_type": project_type,
            "domain": domain,
            "business_unit": self._choice(domain_spec["units"]),
            "product": self._choice(domain_spec["products"]),
            "users": self._choice(domain_spec["users"]),
            "team_size": team_size,
            "teams": teams,
            "weeks": weeks,
            "regimes": regimes,
            "signals": signals,
            "wip_overload": self._bernoulli(0.12),
            "unplanned_pct": int(self.rng.integers(35, 70)) if signals["unplanned_high"] else int(self.rng.integers(15, 35)),
        }

    def workflow_utilities(self, attrs):
        """Transparent utility model linking latent attributes to workflow suitability."""
        s = attrs["signals"]
        pt = attrs["project_type"]
        strict = [r for r in attrs["regimes"] if REGIME_BY_KEY[r].strictness >= 2]
        very_strict = [r for r in attrs["regimes"] if REGIME_BY_KEY[r].strictness >= 3]
        u = {key: 0.0 for key in ARCHETYPE_KEYS}

        if pt in ("new_product_feature", "customer_facing_app", "internal_tooling"):
            u["scrum_product_delivery"] += 2.0
        u["scrum_product_delivery"] += 1.0 * s["volatility_high"] + 0.5 * s["volatility_medium"]
        u["scrum_product_delivery"] += 0.5 * (attrs["teams"] <= 2) + 0.3 * s["continuous_deployment"]

        if pt in ("platform_maintenance", "support_operations"):
            u["kanban_continuous_flow"] += 2.2
        u["kanban_continuous_flow"] += 1.3 * s["unplanned_high"] + 0.3 * s["unplanned_medium"]

        if pt == "regulatory_module":
            u["regulated_compliance_pipeline"] += 2.0
        u["regulated_compliance_pipeline"] += 1.5 * bool(very_strict) + 0.6 * min(2, len(strict))

        if pt in ("hardware_firmware", "systems_integration"):
            u["stage_gate_waterfall"] += 2.0
        u["stage_gate_waterfall"] += 1.1 * s["volatility_low"] + 0.7 * s["vendor_dependency"]
        u["stage_gate_waterfall"] += 0.6 * s["fixed_deadline"] + 0.5 * (attrs["weeks"] >= 40) + 0.6 * s["hardware"]

        if pt == "multi_team_programme":
            u["scaled_release_train"] += 2.2
        u["scaled_release_train"] += 1.5 * (attrs["teams"] >= 4) + 0.5 * s["dependencies_high"]

        if pt == "ml_research":
            u["dual_track_discovery"] += 2.2
        u["dual_track_discovery"] += 1.4 * s["research_high"] + 0.4 * s["ml_component"]

        if pt in ("internal_tooling", "customer_facing_app", "platform_maintenance"):
            u["scrumban_hybrid"] += 1.1
        u["scrumban_hybrid"] += 1.3 * s["unplanned_medium"] + 0.6 * (attrs["team_size"] <= 6)
        u["scrumban_hybrid"] += 0.4 * s["volatility_medium"]

        if pt in ("infrastructure_upgrade", "data_platform_migration"):
            u["incident_change_control"] += 2.2
        u["incident_change_control"] += 1.0 * s["production_critical"] * (pt not in ("new_product_feature", "ml_research"))
        u["incident_change_control"] += 0.8 * s["change_risk"]
        return u

    def optimal_workflow(self, attrs):
        utilities = self.workflow_utilities(attrs)
        noisy = {k: v + float(self.rng.gumbel(0.0, 0.35)) for k, v in utilities.items()}
        ranking = sorted(noisy, key=noisy.get, reverse=True)
        return ranking, utilities

    def needed_adjustments(self, attrs):
        s = attrs["signals"]
        regimes = set(attrs["regimes"])
        security_regimes = {"pci_dss", "iso_27001", "hipaa", "dora", "nis2"}
        needed = set()
        if s["personal_data"] and (s["public_facing"] or regimes & security_regimes):
            needed.add("ADD_SECURITY_REVIEW")
        if s["production_critical"] and attrs["domain"] in ("financial_services", "insurance", "energy_utilities"):
            needed.add("ADD_SECURITY_REVIEW")
        if s["personal_data"] and regimes & {"gdpr", "hipaa"}:
            needed.add("ADD_PRIVACY_REVIEW")
        if s["external_client"]:
            needed.add("ADD_UAT_STAGE")
        if s["data_migration"]:
            needed.add("ADD_DATA_MIGRATION_REHEARSAL")
        if s["public_facing"] and (attrs["domain"] in ("public_sector", "education") or "wcag" in regimes):
            needed.add("ADD_ACCESSIBILITY_REVIEW")
        if s["high_traffic"]:
            needed.add("ADD_PERFORMANCE_TEST")
        if attrs["teams"] >= 3 or s["dependencies_high"]:
            needed.add("ADD_DEPENDENCY_SYNC")
        if s["unplanned_high"] or attrs["wip_overload"]:
            needed.add("TIGHTEN_WIP")
        if s["research_high"]:
            needed.add("ADD_SPIKE_TIMEBOX")
        if s["production_critical"]:
            needed.add("ADD_ROLLBACK_PLAN")
        if s["vendor_dependency"]:
            needed.add("ADD_VENDOR_CHECKPOINT")
        if s["ml_component"]:
            needed.add("ADD_MODEL_VALIDATION")
        if s["continuous_deployment"] and s["public_facing"]:
            needed.add("ADD_FEATURE_FLAGS")
        if s["volatility_high"] and attrs["teams"] >= 2:
            needed.add("ADD_DEFINITION_OF_READY")
        if s["many_stakeholders"]:
            needed.add("ADD_STAKEHOLDER_DEMO")
        for regime in regimes:
            needed.update(REGIME_MANDATED_ADJUSTMENTS.get(regime, ()))
        return sorted(needed)

    # Text synthesis

    def _fill(self, template, attrs):
        return template.format(
            pct=attrs["unplanned_pct"],
            teams=attrs["teams"],
            sites=int(self.rng.integers(2, 5)),
            volume=f"{int(self.rng.integers(2, 90)) * 10000:,}",
            rto=self._choice([15, 30, 60, 120]),
            records=int(self.rng.integers(2, 60)),
            rps=int(self.rng.integers(5, 80)) * 100,
            depts=int(self.rng.integers(4, 11)),
            month=self._choice(V.MONTHS),
            year=int(self.rng.integers(2025, 2028)),
            users=attrs["users"],
            product=attrs["product"],
            csat=round(float(self.rng.uniform(4.0, 4.7)), 1),
            count=int(self.rng.integers(2, 9)),
        )

    def _signal_sentences(self, attrs):
        sentences = []
        for name, active in attrs["signals"].items():
            if active and self._bernoulli(self.SIGNAL_MENTION_PROBABILITY):
                sentences.append(self._fill(self._choice(V.SIGNAL_PHRASES[name]), attrs))
            elif not active and self._bernoulli(self.FALSE_CUE_PROBABILITY):
                sentences.append(self._fill(self._choice(V.SIGNAL_PHRASES[name]), attrs))
        order = self.rng.permutation(len(sentences))
        return [sentences[i] for i in order]

    def charter_text(self, codename, attrs):
        spec = V.PROJECT_TYPES[attrs["project_type"]]
        domain_label = V.DOMAINS[attrs["domain"]]["label"]
        purpose = self._fill(self._choice(spec["purpose"]), attrs)
        signals = self._signal_sentences(attrs)
        split = max(1, len(signals) // 2)
        background, constraints = signals[:split], signals[split:]
        neutral = [V.NEUTRAL_SENTENCES[i] for i in self.rng.choice(len(V.NEUTRAL_SENTENCES), size=3, replace=False)]
        objectives = [self._fill(V.OBJECTIVE_TEMPLATES[i], {**attrs, "unplanned_pct": int(self.rng.integers(10, 45))})
                      for i in self.rng.choice(len(V.OBJECTIVE_TEMPLATES), size=3, replace=False)]
        out_scope = [V.OUT_OF_SCOPE[i] for i in self.rng.choice(len(V.OUT_OF_SCOPE), size=2, replace=False)]

        team_lines = []
        if self._bernoulli(0.88):
            team_lines.append(f"The delivery team comprises {attrs['team_size']} people organised into {attrs['teams']} "
                              f"team{'s' if attrs['teams'] > 1 else ''}.")
        if self._bernoulli(0.85):
            team_lines.append(f"The planned duration is {attrs['weeks']} weeks from mobilisation.")
        team_lines.append(f"The sponsor sits within {attrs['business_unit']}.")

        if attrs["regimes"]:
            reg_lines = []
            for regime in attrs["regimes"]:
                if self._bernoulli(0.88):
                    phrase = self._choice([
                        "The solution falls within scope of {name}.",
                        "Compliance with {name} must be demonstrated before go live.",
                        "Controls required under {name} apply to this service.",
                    ])
                    reg_lines.append(phrase.format(name=REGIME_BY_KEY[regime].display_name))
            if not reg_lines:
                reg_lines.append("Applicable obligations will be confirmed with the compliance team.")
        else:
            reg_lines = [self._choice([
                "No specific external regulation applies beyond standard corporate policies.",
                "Standard information security and data handling policies apply.",
                "There are no sector specific regulatory requirements for this work.",
            ])]

        sections = [
            f"# Project Charter: {codename}",
            f"Domain: {domain_label}. Business unit: {attrs['business_unit']}."
            + (f" Initiative type: {spec['label']}." if self._bernoulli(0.55) else ""),
            "## Purpose",
            f"The purpose of {codename} is to {purpose}.",
            "## Background",
            " ".join(background + [neutral[0]]),
            "## Objectives",
            "\n".join(f"* {o}" for o in objectives),
            "## Scope",
            f"In scope: the {attrs['product']} and the processes used by {attrs['users']}.",
            "Out of scope: " + " ".join(out_scope),
            "## Team and Stakeholders",
            " ".join(team_lines + [neutral[1]]),
            "## Constraints and Assumptions",
            " ".join(constraints + [neutral[2]]) if constraints else neutral[2],
            "## Regulatory and Compliance Context",
            " ".join(reg_lines),
        ]
        return "\n".join(sections)

    def _state_flow(self, archetype):
        names = [s["name"] for s in self.templates[archetype]["states"] if s["category"] not in ("blocked", "cancelled")]
        return " > ".join(names)

    def blueprint_text(self, record, attrs, charter):
        meta = ARCHETYPE_BY_KEY[record["workflow_archetype"]]
        applied = record["adjustments_applied"]
        metrics = record["outcome_metrics"]
        fit_word = "good" if record["fit"] == "optimal" else ("partial" if record["fit"] == "runner_up" else "poor")
        narrative = self._choice(V.WORKFLOW_FIT_NARRATIVES[fit_word])
        adjustments = ", ".join(a.replace("_", " ").lower() for a in applied) if applied else "none"
        lines = [
            f"Historical project blueprint {record['blueprint_id']}: {record['title']}.",
            f"Workflow archetype adopted: {meta.display_name}. State flow: {self._state_flow(meta.key)}.",
            f"Workflow adjustments applied: {adjustments}.",
            f"Outcome score {record['outcome_score']:.2f} on a zero to one scale. "
            f"On time delivery {metrics['on_time_delivery_rate']:.0%}, defect escape rate {metrics['defect_escape_rate']:.1%}, "
            f"median cycle time {metrics['median_cycle_time_days']:.1f} days, stakeholder satisfaction "
            f"{metrics['stakeholder_satisfaction']:.1f} out of 5, {metrics['compliance_findings']} compliance findings.",
            narrative,
            "Charter summary follows.",
            charter,
        ]
        return "\n".join(lines)

    def post_mortem(self, record, attrs, needed):
        applied = set(record["adjustments_applied"])
        recommended = [c for c in needed if self._bernoulli(0.90)]
        for code in ADJUSTMENT_CODES:
            if code not in needed and self._bernoulli(0.025):
                recommended.append(code)
        recommended = sorted(set(recommended))

        well, poorly, lessons = [], [], []
        for code in recommended:
            pool = V.ADJUSTMENT_NARRATIVES[code]
            if code in applied:
                well.append(self._choice(pool["present"]))
            elif code in needed:
                poorly.append(self._choice(pool["missing"]))
            lessons.append(self._choice(pool["lesson"]))

        fit_word = "good" if record["fit"] == "optimal" else ("partial" if record["fit"] == "runner_up" else "poor")
        meta = ARCHETYPE_BY_KEY[record["workflow_archetype"]]
        if fit_word == "good":
            well.insert(0, self._choice(V.WORKFLOW_FIT_NARRATIVES["good"]))
        else:
            poorly.insert(0, self._choice(V.WORKFLOW_FIT_NARRATIVES[fit_word]))
        if not well:
            well.append("The team maintained good morale and collaboration throughout.")
        if not poorly:
            poorly.append("No significant delivery problems were recorded.")

        text = "\n".join([
            f"# Post Mortem: {record['title']}",
            f"Blameless review of {record['project_id']}, delivered with the {meta.display_name} workflow.",
            f"Outcome score {record['outcome_score']:.2f}.",
            "## What went well",
            " ".join(well),
            "## What did not go well",
            " ".join(poorly),
            "## Lessons and recommended workflow adjustments",
            " ".join(lessons) if lessons else "No workflow adjustments were recommended.",
        ])
        return {
            "post_mortem_id": record["blueprint_id"].replace("BP", "PM"),
            "project_id": record["project_id"],
            "title": f"Post mortem for {record['title']}",
            "workflow_archetype": record["workflow_archetype"],
            "outcome_score": record["outcome_score"],
            "recommended_adjustments": recommended,
            "text": text,
        }

    # Outcomes

    def adopt_workflow(self, ranking):
        draw = self.rng.random()
        if draw < self.OPTIMAL_ADOPTION_PROBABILITY:
            return ranking[0], "optimal"
        if draw < self.OPTIMAL_ADOPTION_PROBABILITY + self.RUNNER_UP_ADOPTION_PROBABILITY:
            return ranking[1], "runner_up"
        return self._choice(ranking[2:]), "mismatch"

    def outcome(self, fit, needed, applied, attrs):
        fit_value = {"optimal": 1.0, "runner_up": 0.55, "mismatch": 0.15}[fit]
        coverage = (len(set(needed) & set(applied)) / len(needed)) if needed else 1.0
        maturity = float(self.rng.uniform(0.0, 0.12))
        score = _clip(0.12 + 0.50 * fit_value + 0.26 * coverage + maturity + float(self.rng.normal(0.0, 0.07)))
        shortfall = minus(1.0, score)
        strict = sum(REGIME_BY_KEY[r].strictness for r in attrs["regimes"])
        metrics = {
            "on_time_delivery_rate": round(_clip(0.30 + 0.65 * score + float(self.rng.normal(0.0, 0.05))), 3),
            "defect_escape_rate": round(_clip(0.01 + 0.18 * shortfall + abs(float(self.rng.normal(0.0, 0.01)))), 4),
            "median_cycle_time_days": round(2.0 + 14.0 * shortfall + float(self.rng.gamma(2.0, 0.6)), 2),
            "stakeholder_satisfaction": round(_clip(1.2 + 3.7 * score + float(self.rng.normal(0.0, 0.2)), 1.0, 5.0), 2),
            "compliance_findings": int(self.rng.poisson(0.2 + 2.5 * shortfall * min(strict, 4) / 2)),
            "budget_variance_pct": round(abs(float(self.rng.normal(4.0 + 25.0 * shortfall, 4.0))), 1),
        }
        return round(score, 4), metrics

    # Orchestration

    def generate(self):
        projects, blueprints, post_mortems, truth = [], [], [], []
        for index in range(1, self.settings.n_projects + 1):
            attrs = self.sample_attributes()
            ranking, utilities = self.optimal_workflow(attrs)
            needed = self.needed_adjustments(attrs)
            codename = self._codename()
            charter = self.charter_text(codename, attrs)
            adopted, fit = self.adopt_workflow(ranking)
            applied = sorted({c for c in needed if self._bernoulli(0.55)} |
                             {c for c in ADJUSTMENT_CODES if c not in needed and self._bernoulli(0.04)})
            score, metrics = self.outcome(fit, needed, applied, attrs)
            year = int(self.rng.integers(self.settings.first_year, self.settings.last_year + 1))
            record = {
                "blueprint_id": f"BP{index:05d}",
                "project_id": f"PRJ{index:05d}",
                "title": f"{codename} ({attrs['product']})",
                "codename": codename,
                "domain": attrs["domain"],
                "business_unit": attrs["business_unit"],
                "project_type": attrs["project_type"],
                "year": year,
                "quarter": int(self.rng.integers(1, 5)),
                "team_size": attrs["team_size"],
                "teams": attrs["teams"],
                "duration_weeks": attrs["weeks"],
                "regimes": attrs["regimes"],
                "workflow_archetype": adopted,
                "fit": fit,
                "adjustments_applied": applied,
                "outcome_score": score,
                "outcome_metrics": metrics,
                "charter": charter,
            }
            record["text"] = self.blueprint_text(record, attrs, charter)
            post_mortems.append(self.post_mortem(record, attrs, needed))
            blueprints.append(record)
            truth.append({
                "project_id": record["project_id"],
                "optimal_workflow": ranking[0],
                "workflow_ranking": ranking,
                "utilities": {k: round(v, 3) for k, v in utilities.items()},
                "needed_adjustments": needed,
                "signals": {k: bool(v) for k, v in attrs["signals"].items()},
            })
            projects.append(record["project_id"])

        threshold = float(np.quantile([b["outcome_score"] for b in blueprints], self.settings.high_performance_quantile))
        for b in blueprints:
            b["high_performing"] = bool(b["outcome_score"] >= threshold)
        return {"blueprints": blueprints, "post_mortems": post_mortems, "ground_truth": truth,
                "high_performance_threshold": round(threshold, 4)}

    def write(self, output_dir=None):
        output_dir = Path(output_dir or self.settings.knowledge_base_dir)
        corpus = self.generate()
        (output_dir / "ground_truth").mkdir(parents=True, exist_ok=True)
        (output_dir / "workflow_templates").mkdir(parents=True, exist_ok=True)
        _write_jsonl(output_dir / "blueprints.jsonl", corpus["blueprints"])
        _write_jsonl(output_dir / "post_mortems.jsonl", corpus["post_mortems"])
        _write_jsonl(output_dir / "ground_truth" / "latent_labels.jsonl", corpus["ground_truth"])
        for key, template in self.templates.items():
            payload = dict(template)
            payload["description_text"] = describe_template(template)
            (output_dir / "workflow_templates" / f"{key}.json").write_text(json.dumps(payload, indent=2), encoding="utf8")
        stats = summarise(corpus)
        (output_dir / "manifest.json").write_text(json.dumps(stats, indent=2), encoding="utf8")
        return stats


def summarise(corpus):
    blueprints = corpus["blueprints"]
    by_archetype = {}
    by_archetype_high = {}
    for b in blueprints:
        by_archetype[b["workflow_archetype"]] = by_archetype.get(b["workflow_archetype"], 0) + 1
        if b["high_performing"]:
            by_archetype_high[b["workflow_archetype"]] = by_archetype_high.get(b["workflow_archetype"], 0) + 1
    words = sum(len(b["text"].split()) for b in blueprints) + sum(len(p["text"].split()) for p in corpus["post_mortems"])
    return {
        "projects": len(blueprints),
        "blueprints": len(blueprints),
        "post_mortems": len(corpus["post_mortems"]),
        "synthetic_words": words,
        "high_performance_threshold": corpus["high_performance_threshold"],
        "high_performing_projects": sum(b["high_performing"] for b in blueprints),
        "adopted_workflow_counts": dict(sorted(by_archetype.items())),
        "high_performing_workflow_counts": dict(sorted(by_archetype_high.items())),
        "optimal_adoption_rate": round(sum(b["fit"] == "optimal" for b in blueprints) / len(blueprints), 4),
    }


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
