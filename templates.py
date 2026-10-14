"""Canonical workflow template library.

Each template is a complete, valid state machine for one workflow archetype:
states, transitions with guards and actions, automated triggers, ceremonies,
roles and flow metrics. The customizer starts from these templates and
tailors them to an individual project charter.

Template anatomy
  states       ordered list; exactly one initial state, at least one terminal state
  transitions  directed edges between states, each optionally guarded
  triggers     event driven automations evaluated by the project management backend
  anchors      named positions the customizer uses to splice in extra gates
"""

import copy

from charterloom.catalog import ARCHETYPE_BY_KEY


def state(key, name, category, wip=None, sla=None, initial=False, terminal=False,
          entry_criteria=(), exit_criteria=()):
    return {
        "key": key,
        "name": name,
        "category": category,
        "initial": initial,
        "terminal": terminal,
        "wip_limit": wip,
        "sla_hours": sla,
        "entry_criteria": list(entry_criteria),
        "exit_criteria": list(exit_criteria),
    }


def transition(key, source, target, name=None, guards=(), actions=()):
    return {
        "key": key,
        "name": name or key.replace("_", " ").capitalize(),
        "from": source,
        "to": target,
        "guards": list(guards),
        "actions": list(actions),
    }


def guard(kind, **params):
    return {"type": kind, **params}


def action(kind, **params):
    return {"type": kind, **params}


def trigger(key, event, condition, response, description, **params):
    return {
        "key": key,
        "event": event,
        "condition": condition,
        "action": response,
        "description": description,
        "params": params,
    }


def ceremony(name, cadence, minutes, participants):
    return {"name": name, "cadence": cadence, "duration_minutes": minutes, "participants": list(participants)}


def _scrum():
    return {
        "states": [
            state("product_backlog", "Product Backlog", "backlog", initial=True,
                  exit_criteria=["Story written in user voice", "Acceptance criteria agreed"]),
            state("sprint_backlog", "Sprint Backlog", "todo",
                  entry_criteria=["Estimated in story points", "Committed in sprint planning"]),
            state("in_progress", "In Progress", "in_progress", wip=6, sla=72),
            state("code_review", "Code Review", "review", wip=4, sla=24,
                  entry_criteria=["Pull request linked", "Unit tests passing"]),
            state("qa_verification", "QA Verification", "review", wip=4, sla=48),
            state("ready_for_release", "Ready for Release", "review",
                  entry_criteria=["Definition of done satisfied"]),
            state("done", "Done", "done", terminal=True),
            state("blocked", "Blocked", "blocked", sla=48),
            state("cancelled", "Cancelled", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("plan_into_sprint", "product_backlog", "sprint_backlog",
                       guards=[guard("field_required", field="story_points"),
                               guard("field_required", field="acceptance_criteria")]),
            transition("return_to_backlog", "sprint_backlog", "product_backlog"),
            transition("start_work", "sprint_backlog", "in_progress",
                       guards=[guard("field_required", field="assignee"), guard("wip_available")]),
            transition("submit_for_review", "in_progress", "code_review",
                       guards=[guard("linked_artifact", artifact="pull_request")]),
            transition("request_changes", "code_review", "in_progress"),
            transition("approve_review", "code_review", "qa_verification",
                       guards=[guard("approval", role="engineer", min_approvals=1, distinct_from_author=True)]),
            transition("fail_verification", "qa_verification", "in_progress",
                       actions=[action("increment_counter", field="reopen_count")]),
            transition("pass_verification", "qa_verification", "ready_for_release",
                       guards=[guard("checklist_complete", checklist="test_plan")]),
            transition("release", "ready_for_release", "done",
                       guards=[guard("approval", role="product_owner", min_approvals=1, distinct_from_author=False)],
                       actions=[action("stamp_field", field="released_at"), action("notify", audience="stakeholders")]),
            transition("block", "in_progress", "blocked", guards=[guard("field_required", field="blocker_reason")]),
            transition("unblock", "blocked", "in_progress"),
            transition("cancel", "product_backlog", "cancelled", guards=[guard("field_required", field="cancellation_reason")]),
        ],
        "triggers": [
            trigger("auto_submit_on_pull_request", "external_webhook", "pull_request.opened and item.state == 'in_progress'",
                    "transition:submit_for_review", "Moves an item to code review when its pull request is opened."),
            trigger("stale_review_alert", "time_in_state_exceeded", "state == 'code_review' and hours_in_state > 24",
                    "notify:reviewers", "Nudges reviewers when a review has waited longer than a working day."),
            trigger("blocked_escalation", "time_in_state_exceeded", "state == 'blocked' and hours_in_state > 48",
                    "notify:scrum_master", "Escalates blockers that have not cleared within two days."),
            trigger("sprint_close_carryover", "sprint_closed", "item.state not in ['done', 'cancelled']",
                    "move:sprint_backlog;label:carryover", "Carries unfinished work into the next sprint and labels it."),
        ],
        "ceremonies": [
            ceremony("Sprint planning", "per_sprint", 120, ["product_owner", "scrum_master", "engineer"]),
            ceremony("Daily scrum", "daily", 15, ["engineer", "scrum_master"]),
            ceremony("Backlog refinement", "weekly", 60, ["product_owner", "engineer"]),
            ceremony("Sprint review", "per_sprint", 60, ["product_owner", "engineer", "stakeholder"]),
            ceremony("Retrospective", "per_sprint", 60, ["scrum_master", "engineer", "product_owner"]),
        ],
        "roles": ["product_owner", "scrum_master", "engineer", "qa_engineer", "stakeholder"],
        "cadence": {"type": "sprint", "sprint_length_days": 14},
        "metrics": ["velocity", "sprint_goal_success_rate", "escaped_defects", "cycle_time"],
        "anchors": {"intake": "product_backlog", "rework": "in_progress", "release_transition": "release",
                    "done": "done", "blocked": "blocked", "build_states": ["in_progress"],
                    "review_states": ["code_review", "qa_verification"]},
    }


def _kanban():
    return {
        "states": [
            state("intake", "Intake", "backlog", initial=True),
            state("triage", "Triage", "todo", sla=8, exit_criteria=["Class of service assigned", "Impact assessed"]),
            state("ready", "Ready", "todo", wip=10),
            state("in_progress", "In Progress", "in_progress", wip=5, sla=48),
            state("peer_review", "Peer Review", "review", wip=3, sla=12),
            state("deploy_verification", "Deploy and Verify", "review", wip=3, sla=24),
            state("done", "Done", "done", terminal=True),
            state("blocked", "Blocked", "blocked", sla=24),
            state("rejected", "Rejected", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("triage_item", "intake", "triage"),
            transition("reject", "triage", "rejected", guards=[guard("field_required", field="rejection_reason")]),
            transition("accept_into_ready", "triage", "ready",
                       guards=[guard("field_required", field="class_of_service")]),
            transition("pull", "ready", "in_progress", guards=[guard("wip_available"), guard("field_required", field="assignee")]),
            transition("submit_review", "in_progress", "peer_review"),
            transition("rework", "peer_review", "in_progress"),
            transition("approve", "peer_review", "deploy_verification",
                       guards=[guard("approval", role="engineer", min_approvals=1, distinct_from_author=True)]),
            transition("verification_failed", "deploy_verification", "in_progress"),
            transition("verify", "deploy_verification", "done", actions=[action("stamp_field", field="resolved_at")]),
            transition("block", "in_progress", "blocked", guards=[guard("field_required", field="blocker_reason")]),
            transition("unblock", "blocked", "in_progress"),
        ],
        "triggers": [
            trigger("expedite_jump_queue", "field_changed", "class_of_service == 'expedite'",
                    "move:ready;priority:top;notify:service_owner", "Places expedite items at the head of the ready queue."),
            trigger("wip_limit_guard", "wip_limit_exceeded", "target_state.wip > target_state.wip_limit",
                    "reject_transition;notify:team", "Refuses pulls that would breach a WIP limit."),
            trigger("aging_work_alert", "time_in_state_exceeded", "hours_in_state > sla_hours",
                    "notify:service_owner;label:aging", "Flags items that exceed the service level for their state."),
            trigger("fixed_date_reminder", "scheduled", "class_of_service == 'fixed_date' and days_to_due < 5",
                    "notify:assignee", "Reminds owners of approaching fixed date commitments."),
        ],
        "ceremonies": [
            ceremony("Replenishment", "weekly", 45, ["service_owner", "engineer"]),
            ceremony("Daily flow review", "daily", 15, ["engineer", "service_owner"]),
            ceremony("Service delivery review", "biweekly", 60, ["service_owner", "stakeholder"]),
        ],
        "roles": ["service_owner", "engineer", "support_analyst", "stakeholder"],
        "cadence": {"type": "continuous", "replenishment_days": 7,
                    "classes_of_service": ["expedite", "fixed_date", "standard", "intangible"]},
        "metrics": ["throughput", "cycle_time_p85", "work_item_age", "flow_efficiency"],
        "anchors": {"intake": "intake", "rework": "in_progress", "release_transition": "verify",
                    "done": "done", "blocked": "blocked", "build_states": ["in_progress"],
                    "review_states": ["peer_review", "deploy_verification"]},
    }


def _regulated():
    return {
        "states": [
            state("draft_requirement", "Draft Requirement", "backlog", initial=True),
            state("requirements_traceability", "Requirements Traceability", "todo",
                  exit_criteria=["Requirement linked to risk control", "Verification method defined"]),
            state("design_review", "Design Review", "review", sla=72),
            state("implementation", "Implementation", "in_progress", wip=4, sla=120),
            state("verification", "Verification", "review", wip=4, sla=72,
                  exit_criteria=["Executed test protocol attached", "Deviations recorded"]),
            state("independent_validation", "Independent Validation", "review", sla=96),
            state("compliance_review", "Compliance Review", "review", sla=72),
            state("release_authorisation", "Release Authorisation", "review", sla=48),
            state("released", "Released", "done", terminal=True),
            state("on_hold", "On Hold", "blocked"),
            state("rejected", "Rejected", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("establish_traceability", "draft_requirement", "requirements_traceability",
                       guards=[guard("field_required", field="risk_reference")]),
            transition("submit_design", "requirements_traceability", "design_review",
                       guards=[guard("linked_artifact", artifact="design_specification")]),
            transition("approve_design", "design_review", "implementation",
                       guards=[guard("approval", role="design_authority", min_approvals=1, distinct_from_author=True)]),
            transition("revise_design", "design_review", "requirements_traceability"),
            transition("submit_verification", "implementation", "verification",
                       guards=[guard("linked_artifact", artifact="test_protocol")]),
            transition("verification_failed", "verification", "implementation",
                       actions=[action("create_record", record="nonconformance")]),
            transition("verification_passed", "verification", "independent_validation",
                       guards=[guard("checklist_complete", checklist="verification_protocol")]),
            transition("validation_failed", "independent_validation", "implementation",
                       actions=[action("create_record", record="capa")]),
            transition("validation_passed", "independent_validation", "compliance_review",
                       guards=[guard("approval", role="validation_lead", min_approvals=1, distinct_from_author=True)]),
            transition("compliance_findings", "compliance_review", "implementation"),
            transition("compliance_cleared", "compliance_review", "release_authorisation",
                       guards=[guard("approval", role="compliance_officer", min_approvals=1, distinct_from_author=True)]),
            transition("authorise_release", "release_authorisation", "released",
                       guards=[guard("approval", role="quality_assurance_lead", min_approvals=2, distinct_from_author=True),
                               guard("electronic_signature", meaning="release approval")],
                       actions=[action("stamp_field", field="released_at"), action("freeze_record")]),
            transition("place_on_hold", "implementation", "on_hold", guards=[guard("field_required", field="hold_reason")]),
            transition("resume", "on_hold", "implementation"),
            transition("reject_requirement", "draft_requirement", "rejected",
                       guards=[guard("field_required", field="rejection_rationale")]),
        ],
        "triggers": [
            trigger("audit_trail_every_transition", "transition_completed", "true",
                    "append_audit_log", "Writes an immutable, time stamped audit record for every state change.",
                    retain_years=10),
            trigger("evidence_completeness_check", "transition_requested", "target_state in ['verification', 'release_authorisation']",
                    "validate_attachments", "Blocks progression until mandatory evidence is attached."),
            trigger("capa_on_failure", "transition_completed", "transition in ['verification_failed', 'validation_failed']",
                    "create_record:capa;notify:quality_assurance_lead", "Opens a corrective and preventive action automatically."),
            trigger("periodic_access_review", "scheduled", "cron == 'monthly'",
                    "create_task:access_review", "Schedules a monthly review of who can approve and sign."),
        ],
        "ceremonies": [
            ceremony("Design review board", "per_design", 90, ["design_authority", "engineer", "quality_assurance_lead"]),
            ceremony("Change impact assessment", "weekly", 60, ["compliance_officer", "engineer"]),
            ceremony("Quality review", "biweekly", 60, ["quality_assurance_lead", "validation_lead"]),
        ],
        "roles": ["engineer", "design_authority", "validation_lead", "compliance_officer", "quality_assurance_lead"],
        "cadence": {"type": "controlled_release", "release_window_days": 28},
        "metrics": ["traceability_coverage", "first_pass_validation_rate", "open_capa_count", "audit_findings"],
        "anchors": {"intake": "draft_requirement", "rework": "implementation", "release_transition": "authorise_release",
                    "done": "released", "blocked": "on_hold", "build_states": ["implementation"],
                    "review_states": ["verification", "independent_validation", "compliance_review"]},
    }


def _stage_gate():
    gate_guard = [guard("approval", role="steering_committee", min_approvals=1, distinct_from_author=True),
                  guard("linked_artifact", artifact="gate_review_pack")]
    return {
        "states": [
            state("initiation", "Initiation", "backlog", initial=True, exit_criteria=["Business case approved"]),
            state("requirements_definition", "Requirements Definition", "todo", sla=480),
            state("solution_design", "Solution Design", "in_progress", sla=480),
            state("build", "Build", "in_progress", wip=12),
            state("system_testing", "System Testing", "review", sla=240),
            state("deployment_readiness", "Deployment Readiness", "review", sla=120),
            state("closed", "Closed", "done", terminal=True),
            state("change_control", "Change Control", "blocked"),
            state("cancelled", "Cancelled", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("gate_one_requirements", "initiation", "requirements_definition", guards=gate_guard),
            transition("gate_two_design", "requirements_definition", "solution_design", guards=gate_guard),
            transition("gate_three_build", "solution_design", "build", guards=gate_guard),
            transition("gate_four_test", "build", "system_testing",
                       guards=[guard("checklist_complete", checklist="build_completion")]),
            transition("defects_found", "system_testing", "build"),
            transition("gate_five_readiness", "system_testing", "deployment_readiness", guards=gate_guard),
            transition("go_live", "deployment_readiness", "closed",
                       guards=[guard("approval", role="sponsor", min_approvals=1, distinct_from_author=True)],
                       actions=[action("stamp_field", field="go_live_at"), action("notify", audience="stakeholders")]),
            transition("raise_change_request", "build", "change_control",
                       guards=[guard("field_required", field="change_request_reference")]),
            transition("change_approved", "change_control", "build",
                       guards=[guard("approval", role="change_board", min_approvals=1, distinct_from_author=True)]),
            transition("terminate", "initiation", "cancelled", guards=[guard("field_required", field="termination_reason")]),
        ],
        "triggers": [
            trigger("gate_review_scheduler", "transition_requested", "transition.startswith('gate')",
                    "create_meeting:gate_review", "Books a gate review with the steering committee."),
            trigger("baseline_change_detection", "field_changed", "field in ['scope', 'budget', 'end_date']",
                    "transition:raise_change_request", "Routes any baseline change through change control."),
            trigger("milestone_slippage_alert", "scheduled", "days_behind_baseline > 5",
                    "notify:sponsor;label:at_risk", "Alerts the sponsor when a milestone slips beyond tolerance."),
        ],
        "ceremonies": [
            ceremony("Gate review", "per_phase", 120, ["steering_committee", "project_manager", "sponsor"]),
            ceremony("Weekly status", "weekly", 45, ["project_manager", "workstream_lead"]),
            ceremony("Change board", "weekly", 60, ["change_board", "project_manager"]),
        ],
        "roles": ["sponsor", "project_manager", "workstream_lead", "steering_committee", "change_board", "engineer"],
        "cadence": {"type": "phased", "gate_count": 5},
        "metrics": ["schedule_performance_index", "cost_performance_index", "change_request_volume", "defect_density"],
        "anchors": {"intake": "initiation", "rework": "build", "release_transition": "go_live",
                    "done": "closed", "blocked": "change_control", "build_states": ["build", "solution_design"],
                    "review_states": ["system_testing", "deployment_readiness"]},
    }


def _scaled():
    return {
        "states": [
            state("programme_backlog", "Programme Backlog", "backlog", initial=True),
            state("feature_analysis", "Feature Analysis", "todo", wip=12,
                  exit_criteria=["Benefit hypothesis written", "WSJF score calculated"]),
            state("increment_committed", "Committed to Increment", "todo"),
            state("feature_in_progress", "Feature In Progress", "in_progress", wip=10),
            state("system_demo", "System Demo", "review", sla=72),
            state("integration_testing", "Integration Testing", "review", wip=6, sla=96),
            state("release_ready", "Release Ready", "review"),
            state("released", "Released", "done", terminal=True),
            state("dependency_blocked", "Dependency Blocked", "blocked", sla=48),
            state("deferred", "Deferred", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("analyse", "programme_backlog", "feature_analysis"),
            transition("commit_in_planning", "feature_analysis", "increment_committed",
                       guards=[guard("field_required", field="wsjf_score"), guard("field_required", field="owning_team")]),
            transition("start_feature", "increment_committed", "feature_in_progress", guards=[guard("wip_available")]),
            transition("demo", "feature_in_progress", "system_demo"),
            transition("demo_feedback", "system_demo", "feature_in_progress"),
            transition("accept_demo", "system_demo", "integration_testing",
                       guards=[guard("approval", role="product_manager", min_approvals=1, distinct_from_author=True)]),
            transition("integration_failed", "integration_testing", "feature_in_progress"),
            transition("integration_passed", "integration_testing", "release_ready",
                       guards=[guard("checklist_complete", checklist="end_to_end_suite")]),
            transition("release_on_demand", "release_ready", "released",
                       guards=[guard("approval", role="release_train_engineer", min_approvals=1, distinct_from_author=True)],
                       actions=[action("stamp_field", field="released_at")]),
            transition("blocked_on_dependency", "feature_in_progress", "dependency_blocked",
                       guards=[guard("field_required", field="dependency_owner")]),
            transition("dependency_cleared", "dependency_blocked", "feature_in_progress"),
            transition("defer", "programme_backlog", "deferred"),
        ],
        "triggers": [
            trigger("increment_boundary_carryover", "increment_closed", "item.state not in ['released', 'deferred']",
                    "move:programme_backlog;label:carryover", "Returns uncompleted features for replanning."),
            trigger("dependency_aging_alert", "time_in_state_exceeded", "state == 'dependency_blocked' and hours_in_state > 48",
                    "notify:release_train_engineer;notify:dependency_owner", "Escalates aging cross team dependencies."),
            trigger("risk_roam_capture", "field_changed", "label == 'risk'",
                    "create_record:roam_risk", "Captures programme risks on the ROAM board."),
        ],
        "ceremonies": [
            ceremony("Increment planning", "per_increment", 960, ["release_train_engineer", "product_manager", "team_lead"]),
            ceremony("Coordination sync", "weekly", 60, ["release_train_engineer", "team_lead"]),
            ceremony("System demo", "biweekly", 60, ["product_manager", "team_lead", "stakeholder"]),
            ceremony("Inspect and adapt", "per_increment", 180, ["release_train_engineer", "team_lead", "product_manager"]),
        ],
        "roles": ["release_train_engineer", "product_manager", "system_architect", "team_lead", "engineer", "stakeholder"],
        "cadence": {"type": "programme_increment", "increment_weeks": 10, "iteration_days": 14},
        "metrics": ["increment_predictability", "feature_cycle_time", "dependency_count", "release_frequency"],
        "anchors": {"intake": "programme_backlog", "rework": "feature_in_progress", "release_transition": "release_on_demand",
                    "done": "released", "blocked": "dependency_blocked", "build_states": ["feature_in_progress"],
                    "review_states": ["system_demo", "integration_testing"]},
    }


def _dual_track():
    return {
        "states": [
            state("opportunity_backlog", "Opportunity Backlog", "backlog", initial=True),
            state("hypothesis_framing", "Hypothesis Framing", "todo",
                  exit_criteria=["Falsifiable hypothesis", "Success metric and kill criteria agreed"]),
            state("discovery_research", "Discovery Research", "in_progress", wip=4, sla=120),
            state("experiment_running", "Experiment Running", "in_progress", wip=3),
            state("evidence_review", "Evidence Review", "review", sla=48),
            state("delivery_backlog", "Delivery Backlog", "todo"),
            state("building", "Building", "in_progress", wip=5),
            state("validation_in_production", "Validation in Production", "review"),
            state("learned_and_shipped", "Learned and Shipped", "done", terminal=True),
            state("blocked", "Blocked", "blocked"),
            state("discarded", "Discarded", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("frame_hypothesis", "opportunity_backlog", "hypothesis_framing"),
            transition("begin_discovery", "hypothesis_framing", "discovery_research",
                       guards=[guard("field_required", field="success_metric"), guard("field_required", field="kill_criteria")]),
            transition("launch_experiment", "discovery_research", "experiment_running",
                       guards=[guard("linked_artifact", artifact="experiment_design")]),
            transition("collect_evidence", "experiment_running", "evidence_review"),
            transition("iterate_research", "evidence_review", "discovery_research"),
            transition("discard_hypothesis", "evidence_review", "discarded",
                       guards=[guard("field_required", field="learning_summary")]),
            transition("promote_to_delivery", "evidence_review", "delivery_backlog",
                       guards=[guard("approval", role="product_trio", min_approvals=2, distinct_from_author=False)]),
            transition("start_build", "delivery_backlog", "building", guards=[guard("wip_available")]),
            transition("ship_for_validation", "building", "validation_in_production"),
            transition("outcome_missed", "validation_in_production", "building"),
            transition("confirm_outcome", "validation_in_production", "learned_and_shipped",
                       guards=[guard("field_required", field="measured_outcome")]),
            transition("block", "building", "blocked"),
            transition("unblock", "blocked", "building"),
        ],
        "triggers": [
            trigger("experiment_metrics_attach", "transition_completed", "transition == 'collect_evidence'",
                    "attach:experiment_dashboard", "Attaches experiment telemetry to the evidence review."),
            trigger("kill_criteria_check", "scheduled", "state == 'experiment_running'",
                    "evaluate:kill_criteria;notify:product_trio", "Evaluates kill criteria daily while experiments run."),
            trigger("learning_log", "transition_completed", "transition in ['discard_hypothesis', 'confirm_outcome']",
                    "append_learning_log", "Records every validated or invalidated hypothesis."),
        ],
        "ceremonies": [
            ceremony("Discovery sync", "twice_weekly", 30, ["product_trio", "researcher"]),
            ceremony("Evidence review", "weekly", 60, ["product_trio", "data_scientist"]),
            ceremony("Delivery planning", "biweekly", 60, ["product_trio", "engineer"]),
        ],
        "roles": ["product_trio", "researcher", "data_scientist", "engineer", "stakeholder"],
        "cadence": {"type": "dual_track", "discovery_cycle_days": 7, "delivery_iteration_days": 14},
        "metrics": ["hypotheses_tested", "validated_learning_rate", "time_to_evidence", "outcome_attainment"],
        "anchors": {"intake": "opportunity_backlog", "rework": "building", "release_transition": "confirm_outcome",
                    "done": "learned_and_shipped", "blocked": "blocked", "build_states": ["building", "discovery_research"],
                    "review_states": ["evidence_review", "validation_in_production"]},
    }


def _scrumban():
    return {
        "states": [
            state("backlog", "Backlog", "backlog", initial=True),
            state("ready", "Ready", "todo", wip=8),
            state("in_progress", "In Progress", "in_progress", wip=5, sla=72),
            state("review", "Review", "review", wip=3, sla=24),
            state("testing", "Testing", "review", wip=3, sla=48),
            state("done", "Done", "done", terminal=True),
            state("blocked", "Blocked", "blocked", sla=48),
            state("cancelled", "Cancelled", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("make_ready", "backlog", "ready", guards=[guard("field_required", field="priority")]),
            transition("pull", "ready", "in_progress", guards=[guard("wip_available")]),
            transition("submit_review", "in_progress", "review"),
            transition("rework", "review", "in_progress"),
            transition("approve", "review", "testing",
                       guards=[guard("approval", role="engineer", min_approvals=1, distinct_from_author=True)]),
            transition("test_failed", "testing", "in_progress"),
            transition("accept", "testing", "done", actions=[action("stamp_field", field="completed_at")]),
            transition("block", "in_progress", "blocked"),
            transition("unblock", "blocked", "in_progress"),
            transition("cancel", "backlog", "cancelled"),
        ],
        "triggers": [
            trigger("planning_on_demand", "transition_completed", "count(state == 'ready') < 3",
                    "create_meeting:planning;notify:team_lead", "Triggers a planning session when the ready queue runs low."),
            trigger("interrupt_lane", "field_changed", "type == 'incident'",
                    "move:ready;priority:top", "Routes interrupts into a protected expedite lane."),
            trigger("aging_wip_alert", "time_in_state_exceeded", "hours_in_state > sla_hours",
                    "notify:team_lead", "Flags work items that are aging beyond their service level."),
        ],
        "ceremonies": [
            ceremony("Planning on demand", "triggered", 60, ["team_lead", "engineer"]),
            ceremony("Daily standup", "daily", 15, ["engineer", "team_lead"]),
            ceremony("Retrospective", "biweekly", 45, ["team_lead", "engineer"]),
        ],
        "roles": ["team_lead", "engineer", "product_owner", "stakeholder"],
        "cadence": {"type": "hybrid", "review_days": 14},
        "metrics": ["throughput", "cycle_time", "interrupt_ratio", "planned_vs_unplanned"],
        "anchors": {"intake": "backlog", "rework": "in_progress", "release_transition": "accept",
                    "done": "done", "blocked": "blocked", "build_states": ["in_progress"],
                    "review_states": ["review", "testing"]},
    }


def _change_control():
    return {
        "states": [
            state("change_request", "Change Request", "backlog", initial=True),
            state("risk_assessment", "Risk Assessment", "todo", sla=24,
                  exit_criteria=["Impact and blast radius documented", "Risk rating assigned"]),
            state("cab_review", "Change Advisory Board Review", "review", sla=72),
            state("scheduled", "Scheduled", "todo"),
            state("implementing", "Implementing", "in_progress", wip=3),
            state("post_implementation_review", "Post Implementation Review", "review", sla=72),
            state("closed", "Closed", "done", terminal=True),
            state("rolled_back", "Rolled Back", "blocked"),
            state("rejected", "Rejected", "cancelled", terminal=True),
        ],
        "transitions": [
            transition("assess", "change_request", "risk_assessment"),
            transition("submit_to_cab", "risk_assessment", "cab_review",
                       guards=[guard("field_required", field="risk_rating"), guard("linked_artifact", artifact="implementation_plan")]),
            transition("cab_rejects", "cab_review", "rejected", guards=[guard("field_required", field="rejection_reason")]),
            transition("cab_requests_rework", "cab_review", "risk_assessment"),
            transition("schedule", "cab_review", "scheduled",
                       guards=[guard("approval", role="change_advisory_board", min_approvals=2, distinct_from_author=True)]),
            transition("emergency_change", "change_request", "implementing",
                       guards=[guard("approval", role="emergency_change_authority", min_approvals=1, distinct_from_author=True),
                               guard("field_required", field="incident_reference")]),
            transition("begin_implementation", "scheduled", "implementing",
                       guards=[guard("change_window_open")]),
            transition("complete_implementation", "implementing", "post_implementation_review"),
            transition("roll_back", "implementing", "rolled_back", actions=[action("notify", audience="service_owner")]),
            transition("replan_after_rollback", "rolled_back", "risk_assessment"),
            transition("close_change", "post_implementation_review", "closed",
                       guards=[guard("field_required", field="pir_outcome")]),
        ],
        "triggers": [
            trigger("freeze_window_enforcement", "transition_requested", "transition == 'begin_implementation' and calendar.freeze_active",
                    "reject_transition;notify:change_manager", "Prevents implementation during declared change freezes."),
            trigger("health_check_auto_rollback", "external_webhook", "monitoring.error_budget_burn > 2.0 and state == 'implementing'",
                    "transition:roll_back;page:on_call", "Rolls back automatically when error budget burn spikes."),
            trigger("pir_reminder", "time_in_state_exceeded", "state == 'post_implementation_review' and hours_in_state > 72",
                    "notify:change_manager", "Chases overdue post implementation reviews."),
            trigger("emergency_change_retro_review", "transition_completed", "transition == 'emergency_change'",
                    "create_task:retrospective_cab_review", "Forces retrospective CAB review of emergency changes."),
        ],
        "ceremonies": [
            ceremony("Change advisory board", "weekly", 60, ["change_advisory_board", "change_manager", "service_owner"]),
            ceremony("Operational readiness review", "per_change", 30, ["service_owner", "engineer"]),
        ],
        "roles": ["change_manager", "change_advisory_board", "emergency_change_authority", "service_owner", "engineer", "on_call"],
        "cadence": {"type": "change_windows", "standard_window": "weekday_evening", "freeze_calendar": True},
        "metrics": ["change_failure_rate", "mean_time_to_restore", "emergency_change_ratio", "change_lead_time"],
        "anchors": {"intake": "change_request", "rework": "risk_assessment", "release_transition": "schedule",
                    "done": "closed", "blocked": "rolled_back", "build_states": ["implementing"],
                    "review_states": ["cab_review", "post_implementation_review"]},
    }


_BUILDERS = {
    "scrum_product_delivery": _scrum,
    "kanban_continuous_flow": _kanban,
    "regulated_compliance_pipeline": _regulated,
    "stage_gate_waterfall": _stage_gate,
    "scaled_release_train": _scaled,
    "dual_track_discovery": _dual_track,
    "scrumban_hybrid": _scrumban,
    "incident_change_control": _change_control,
}


def build_template(archetype_key):
    """Return a fresh, deep copied template for ``archetype_key``."""
    if archetype_key not in _BUILDERS:
        raise KeyError(f"Unknown workflow archetype: {archetype_key}")
    meta = ARCHETYPE_BY_KEY[archetype_key]
    body = _BUILDERS[archetype_key]()
    template = {
        "archetype": archetype_key,
        "display_name": meta.display_name,
        "family": meta.family,
        "summary": meta.summary,
        "template_version": "2026.10",
    }
    template.update(body)
    return copy.deepcopy(template)


def all_templates():
    return {key: build_template(key) for key in _BUILDERS}


def describe_template(template):
    """Render a template as plain prose so it can be indexed by the retriever."""
    lines = [
        f"Workflow template: {template['display_name']} ({template['archetype']}).",
        template["summary"],
        "States in order: " + ", ".join(s["name"] for s in template["states"]) + ".",
    ]
    for t in template["transitions"]:
        guard_text = "; ".join(_guard_text(g) for g in t["guards"]) or "no guard"
        lines.append(f"Transition {t['name']} moves work from {t['from']} to {t['to']} with {guard_text}.")
    for trig in template["triggers"]:
        lines.append(f"Automation {trig['key']}: {trig['description']}")
    lines.append("Ceremonies: " + ", ".join(c["name"] for c in template["ceremonies"]) + ".")
    lines.append("Primary metrics: " + ", ".join(m.replace("_", " ") for m in template["metrics"]) + ".")
    return "\n".join(lines)


def _guard_text(g):
    kind = g["type"]
    if kind == "approval":
        return f"approval by {g['min_approvals']} {g['role'].replace('_', ' ')}"
    if kind == "field_required":
        return f"required field {g['field'].replace('_', ' ')}"
    if kind == "linked_artifact":
        return f"linked {g['artifact'].replace('_', ' ')}"
    if kind == "checklist_complete":
        return f"completed {g['checklist'].replace('_', ' ')} checklist"
    if kind == "electronic_signature":
        return f"electronic signature meaning {g['meaning']}"
    return kind.replace("_", " ")
