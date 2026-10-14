# Automation Trigger Patterns

## Purpose
Automated triggers remove routine coordination from people and make process rules enforceable. Each trigger has an event, a condition and an action. This catalogue lists the patterns approved for use in workflow templates.

## Events
* transition_completed: fires after a state change.
* transition_requested: fires before a state change and may reject it.
* time_in_state_exceeded: fires when an item has stayed in a state longer than a threshold.
* field_changed: fires when a field such as class of service or label changes.
* scheduled: fires on a calendar schedule.
* external_webhook: fires on events from version control, monitoring or incident tools.
* sprint_closed and increment_closed: fire at cadence boundaries.
* wip_limit_exceeded: fires when a pull would breach a limit.

## Approved patterns
* Pull request linkage: move work to review when a pull request opens.
* Stale review alert: notify reviewers after a working day in review.
* Blocker escalation: escalate blocked items after a defined period.
* Carryover: return unfinished work to the backlog at a cadence boundary with a label.
* WIP guard: reject pulls that breach a limit.
* Expedite routing: move expedite items to the head of the queue.
* Audit trail: write an immutable record on every transition.
* Evidence completeness: block transitions until mandatory attachments exist.
* CAPA creation: open corrective action records on validation failure.
* Freeze enforcement: reject implementation during change freezes.
* Health based rollback: roll back automatically when monitoring shows error budget burn.
* Timebox expiry: force a decision when a spike exceeds its timebox.
* Dependency escalation: notify the dependency owner when cross team work is blocked.
* Progressive rollout: ramp feature flag exposure in stages with guardrail metrics.
* Incident early warning: start regulatory reporting clocks when significant incidents open.

## Design rules
Keep conditions simple and observable. Every automation should be explainable in one sentence. Avoid chains of triggers that fire each other, which make behaviour hard to predict. Log every automated action with the trigger key so that audits can distinguish human and automated changes.
