"""Customizer: turns a recommended archetype into a tailored state machine.

The customizer starts from the canonical template of the recommended archetype
and applies four layers of tailoring, recording every change in a changelog
with its reason and the knowledge base evidence behind it:

  1. Parameter tuning      WIP limits, cadence and service levels sized to the team
  2. Regulatory overlays   guards and automations that detected regimes demand
  3. Evidence adjustments  gates, guards, triggers and ceremonies recommended by the
                           post mortems of the most similar historical projects,
                           blended with priors read directly from the charter
  4. Validation            the result must pass the state machine validator
"""

import copy
import math

from charterloom.catalog import ADJUSTMENT_BY_CODE, ADJUSTMENTS, REGIME_BY_KEY, REGIME_MANDATED_ADJUSTMENTS
from charterloom.config import SCHEMA_VERSION
from charterloom.knowledge.templates import build_template, ceremony, guard, trigger
from charterloom.state_machine import StateMachineEditor, validate
from charterloom.text import minus

GATE_SPECS = {
    "ADD_PERFORMANCE_TEST": ("performance_testing", "Performance Testing", "performance_engineer", "load_test_report"),
    "ADD_SECURITY_REVIEW": ("security_review", "Security Review", "security_engineer", "security_assessment"),
    "ADD_PRIVACY_REVIEW": ("privacy_impact_assessment", "Privacy Impact Assessment", "data_protection_officer", "dpia_record"),
    "ADD_ACCESSIBILITY_REVIEW": ("accessibility_review", "Accessibility Review", "accessibility_specialist", "accessibility_audit"),
    "ADD_MODEL_VALIDATION": ("model_validation", "Model Validation", "model_risk_reviewer", "model_validation_report"),
    "ADD_DATA_MIGRATION_REHEARSAL": ("migration_rehearsal", "Migration Rehearsal", "data_migration_lead", "reconciliation_report"),
    "ADD_VENDOR_CHECKPOINT": ("vendor_acceptance", "Vendor Acceptance", "supplier_manager", "vendor_conformance_certificate"),
    "ADD_UAT_STAGE": ("user_acceptance_testing", "User Acceptance Testing", "client_acceptance_lead", "uat_signoff"),
}
GATE_ORDER = tuple(GATE_SPECS)


class WorkflowCustomizer:
    """Generate a tailored, validated workflow configuration."""

    def __init__(self, settings):
        self.settings = settings
        self.threshold = settings.adjustment_threshold
        self.calibration = {}

    def calibrate_threshold(self, samples):
        """Choose the application threshold that best reproduces observed post mortem recommendations.

        ``samples`` holds ``(priors, post_mortem_hits, regimes, observed_codes)`` tuples for
        training projects, where the hits exclude the project itself and the observed codes
        come from that project's own post mortem. Only information that a real organisation
        records is used, so the calibration is leakage free.
        """
        grid = [round(0.20 + 0.02 * i, 2) for i in range(26)]
        scored = [(self.score_adjustments(p, h, r), set(obs)) for p, h, r, obs in samples]
        best_t, best_f1, curve = self.threshold, None, []
        for t in grid:
            tp = fp = fn = 0
            for adjustments, observed in scored:
                chosen = {a["code"] for a in adjustments if a["mandated_by_regime"] or a["score"] >= t}
                tp += len(chosen & observed)
                fp += len(minus(chosen, observed))
                fn += len(minus(observed, chosen))
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            curve.append({"threshold": t, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)})
            if best_f1 is None or f1 > best_f1:
                best_t, best_f1 = t, f1
        self.threshold = best_t
        self.calibration = {"threshold": best_t, "f1_on_observed_post_mortems": round(best_f1, 4),
                            "projects": len(samples), "curve": curve}
        return self.calibration

    # Adjustment scoring

    def score_adjustments(self, priors, post_mortem_hits, regimes):
        """Blend charter priors with similarity weighted post mortem evidence."""
        weights = [max(0.0, hit.dense_score) for hit in post_mortem_hits]
        total = sum(weights) or 1.0
        mandated = {code for r in regimes for code in REGIME_MANDATED_ADJUSTMENTS.get(r, ())}
        scored = []
        for adj in ADJUSTMENTS:
            supporters = [(hit, w) for hit, w in zip(post_mortem_hits, weights)
                          if adj.code in hit.metadata.get("recommended_adjustments", [])]
            support = sum(w for _, w in supporters) / total
            prior = priors.get(adj.code, 0.0)
            score = self.settings.adjustment_evidence_weight * support + self.settings.adjustment_prior_weight * prior
            is_mandated = adj.code in mandated
            scored.append({
                "code": adj.code,
                "title": adj.title,
                "kind": adj.kind,
                "score": round(score, 4),
                "evidence_support": round(support, 4),
                "charter_prior": round(prior, 4),
                "mandated_by_regime": is_mandated,
                "applied": bool(is_mandated or score >= self.threshold),
                "evidence": [hit.doc_id for hit, _ in sorted(supporters, key=lambda x: x[1], reverse=True)[:5]],
            })
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored

    # Main entry point

    def customise(self, archetype, profile, priors, post_mortem_hits, project_name="Untitled project",
                  confidence=None, charter_fingerprint=None):
        template = build_template(archetype)
        config = {
            "schema_version": SCHEMA_VERSION,
            "generated_by": "Charterloom AI",
            "project": {"name": project_name, "charter_fingerprint": charter_fingerprint},
            "workflow": {"archetype": archetype, "display_name": template["display_name"],
                         "family": template["family"], "template_version": template["template_version"],
                         "recommendation_confidence": confidence},
            "cadence": copy.deepcopy(template["cadence"]),
            "states": template["states"],
            "transitions": template["transitions"],
            "triggers": template["triggers"],
            "ceremonies": template["ceremonies"],
            "roles": template["roles"],
            "metrics": template["metrics"],
            "anchors": template["anchors"],
            "compliance": {"regimes": list(profile.regimes),
                           "regime_names": [REGIME_BY_KEY[r].display_name for r in profile.regimes]},
        }
        editor = StateMachineEditor(config)
        self._tune_parameters(editor, profile)
        adjustments = self.score_adjustments(priors, post_mortem_hits, profile.regimes)
        self._apply_adjustments(editor, adjustments)
        self._apply_regime_overlays(editor, profile)
        editor.mark_release()
        report = validate(config)
        config["adjustments"] = adjustments
        config["changelog"] = editor.changelog
        config["validation"] = report.to_dict()
        return config

    # Layer 1: parameters

    def _tune_parameters(self, editor, profile):
        config = editor.config
        anchors = config["anchors"]
        team = profile.team_size
        teams = max(1, profile.teams or 1)
        if team:
            if config["workflow"]["archetype"] == "scaled_release_train":
                build_limit = max(4, teams * 2)
            else:
                build_limit = min(30, max(2, math.ceil(team * 0.6)))
            review_limit = min(15, max(2, math.ceil(team * 0.35)))
            reason = f"Sized to a team of {team} people across {teams} team{'s' if teams > 1 else ''}"
            for key in anchors["build_states"]:
                editor.set_wip(key, build_limit, reason)
            for key in anchors["review_states"]:
                state = editor._state(key)
                if state and state.get("wip_limit"):
                    editor.set_wip(key, review_limit, reason)
        cadence = config["cadence"]
        if cadence.get("type") == "sprint":
            length = profile.sprint_length_days or (7 if profile.signal("requirements_volatility") >= 1.0 and (team or 0) <= 5 else 14)
            if length != cadence["sprint_length_days"]:
                cadence["sprint_length_days"] = length
                editor.log(f"Sprint length set to {length} days", "Matched to charter cadence and volatility")
        if profile.signal("production_critical") >= 1.0:
            editor.scale_sla(0.75, "Production critical service: tighter service levels")

    # Layer 3: evidence driven adjustments

    def _apply_adjustments(self, editor, adjustments):
        applied = {a["code"]: a for a in adjustments if a["applied"]}
        for code in GATE_ORDER:
            if code in applied:
                key, name, role, artifact = GATE_SPECS[code]
                editor.insert_gate(key, name, role, artifact, self._reason(applied[code]), applied[code]["evidence"])
        anchors = editor.config["anchors"]
        release_key = anchors["release_transition"]

        if "ADD_ROLLBACK_PLAN" in applied:
            a = applied["ADD_ROLLBACK_PLAN"]
            editor.add_guard(release_key, guard("field_required", field="rollback_plan"), self._reason(a), a["evidence"])
            editor.add_guard(release_key, guard("linked_artifact", artifact="rollback_rehearsal_evidence"), self._reason(a))
        if "ADD_FEATURE_FLAGS" in applied:
            a = applied["ADD_FEATURE_FLAGS"]
            editor.add_guard(release_key, guard("field_required", field="feature_flag"), self._reason(a), a["evidence"])
            editor.add_trigger(trigger("progressive_rollout", "transition_completed", f"transition == '{release_key}'",
                                       "start_rollout:feature_flag", "Ramps exposure 1, 10, 50 then 100 percent with guardrail metrics.",
                                       stages=[1, 10, 50, 100]), self._reason(a))
        if "ADD_DEFINITION_OF_READY" in applied:
            a = applied["ADD_DEFINITION_OF_READY"]
            intake = anchors["intake"]
            terminal = {s["key"] for s in editor.config["states"] if s["category"] == "cancelled"}
            for t in list(editor.config["transitions"]):
                if t["from"] == intake and t["to"] not in terminal:
                    editor.add_guard(t["key"], guard("checklist_complete", checklist="definition_of_ready"),
                                     self._reason(a), a["evidence"])
        if "TIGHTEN_WIP" in applied:
            a = applied["TIGHTEN_WIP"]
            for s in editor.config["states"]:
                if s["category"] in ("in_progress", "review") and s.get("wip_limit"):
                    editor.set_wip(s["key"], math.floor(s["wip_limit"] * 0.75), self._reason(a))
        if "ADD_DEPENDENCY_SYNC" in applied:
            a = applied["ADD_DEPENDENCY_SYNC"]
            blocked = anchors["blocked"]
            editor.add_trigger(trigger("dependency_escalation", "time_in_state_exceeded",
                                       f"state == '{blocked}' and blocker_type == 'dependency' and hours_in_state > 24",
                                       "notify:dependency_owner;notify:delivery_lead",
                                       "Escalates work blocked on another team after one day."),
                               self._reason(a), a["evidence"])
            editor.add_ceremony(ceremony("Cross team dependency sync", "weekly", 30, ["team_lead", "dependency_owner"]),
                                self._reason(a), a["evidence"])
        if "ADD_SPIKE_TIMEBOX" in applied:
            a = applied["ADD_SPIKE_TIMEBOX"]
            editor.add_trigger(trigger("spike_timebox_expiry", "time_in_state_exceeded",
                                       "item.type == 'spike' and days_in_state > timebox_days",
                                       "notify:owner;label:decision_required",
                                       "Forces a continue or stop decision when a research spike exceeds its timebox.",
                                       timebox_days=5), self._reason(a), a["evidence"])
        if "ADD_STAKEHOLDER_DEMO" in applied:
            a = applied["ADD_STAKEHOLDER_DEMO"]
            editor.add_ceremony(ceremony("Stakeholder demonstration", "monthly", 60, ["product_owner", "stakeholder"]),
                                self._reason(a), a["evidence"])

    # Layer 2: regulatory overlays (applied after gates so they bind to the final release edge)

    def _apply_regime_overlays(self, editor, profile):
        anchors = editor.config["anchors"]
        release_key = anchors["release_transition"]
        regimes = set(profile.regimes)

        def audit_trail(years, regime):
            editor.add_trigger(trigger("audit_trail_every_transition", "transition_completed", "true", "append_audit_log",
                                       "Writes an immutable, time stamped audit record for every state change.",
                                       retain_years=years), f"Required by {REGIME_BY_KEY[regime].display_name}")

        if "sox" in regimes:
            audit_trail(7, "sox")
            editor.add_guard(release_key, guard("approval", role="control_owner", min_approvals=1, distinct_from_author=True),
                             "Segregation of duties under Sarbanes Oxley Section 404")
        if "cfr_part_11" in regimes:
            audit_trail(10, "cfr_part_11")
            editor.add_guard(release_key, guard("electronic_signature", meaning="release approval"),
                             "Electronic signatures under FDA 21 CFR Part 11")
        if regimes & {"iec_62304", "iso_13485"}:
            editor.add_guard(release_key, guard("linked_artifact", artifact="design_history_file"),
                             "Design history evidence for medical device software")
            editor.add_trigger(trigger("traceability_matrix_update", "transition_completed", "true",
                                       "update:traceability_matrix",
                                       "Keeps requirement, risk control and verification links current."),
                               "Traceability required by IEC 62304 and ISO 13485")
        if "dora" in regimes:
            editor.add_trigger(trigger("ict_incident_classification", "external_webhook", "incident.opened",
                                       "classify:major_ict_incident;notify:resilience_office",
                                       "Classifies ICT incidents against DORA major incident criteria."),
                               "Incident classification under DORA")
        if "nis2" in regimes:
            editor.add_trigger(trigger("significant_incident_early_warning", "external_webhook",
                                       "incident.significant == true", "create_task:early_warning_report;notify:ciso",
                                       "Starts the 24 hour early warning clock for significant incidents.",
                                       deadline_hours=24), "Incident reporting under the NIS2 Directive")
        if "fca_consumer_duty" in regimes:
            editor.add_guard(release_key, guard("linked_artifact", artifact="customer_outcome_assessment"),
                             "Evidence of good customer outcomes under the FCA Consumer Duty")
        if "mifid" in regimes:
            editor.add_trigger(trigger("record_retention", "transition_completed", "true", "retain:records",
                                       "Retains communication and decision records.", retain_years=5),
                               "Record keeping under MiFID II")
        if "hipaa" in regimes:
            editor.add_trigger(trigger("phi_access_audit", "scheduled", "cron == 'monthly'", "create_task:phi_access_review",
                                       "Reviews who accessed protected health information."),
                               "Access review under the HIPAA Security Rule")
        if "pci_dss" in regimes:
            editor.add_trigger(trigger("cardholder_scope_review", "scheduled", "cron == 'quarterly'",
                                       "create_task:pci_scope_review",
                                       "Confirms the cardholder data environment boundary each quarter."),
                               "Scope management under PCI DSS v4.0")
        if "gdpr" in regimes:
            editor.add_trigger(trigger("data_retention_review", "scheduled", "cron == 'quarterly'",
                                       "create_task:retention_review", "Checks personal data against retention rules."),
                               "Storage limitation under UK GDPR")
        if any(REGIME_BY_KEY[r].strictness >= 2 for r in regimes):
            release = editor._transition(release_key)
            segregated = any(g["type"] == "approval" and g.get("distinct_from_author") for g in release["guards"])
            if not segregated:
                editor.add_guard(release_key, guard("approval", role="release_approver", min_approvals=1,
                                                    distinct_from_author=True),
                                 "Strict regimes require segregation of duties at release")

    @staticmethod
    def _reason(adjustment):
        if adjustment["mandated_by_regime"]:
            return f"{adjustment['title']} mandated by detected regulatory regime"
        return (f"{adjustment['title']}: evidence support {adjustment['evidence_support']:.0%} "
                f"from similar post mortems, charter prior {adjustment['charter_prior']:.2f}")


def adjustment_title(code):
    return ADJUSTMENT_BY_CODE[code].title
