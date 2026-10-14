# State Transition Design Principles

## Purpose
Workflow configurations are state machines. Poorly designed state machines produce stuck work, confusing boards and unreliable metrics. These principles apply to every template in the library.

## Structural rules
* Exactly one initial state, so every item has an unambiguous starting point.
* At least one terminal state for successful completion and one for abandonment.
* Every state reachable from the initial state; unreachable states indicate configuration errors.
* Every non terminal state able to reach a terminal state; a state with no exit is a trap.
* No transitions out of terminal states; reopening creates a new item or uses an explicit reopen state.

## State categories
Each state belongs to one category: backlog, to do, in progress, review, blocked, done or cancelled. Categories drive cross project reporting, so a custom state must map to exactly one category. Review gates inserted by overlays belong to the review category.

## Guards
Guards are conditions evaluated before a transition. Prefer a small number of meaningful guards: required fields that downstream steps need, linked artifacts such as pull requests or test protocols, completed checklists, approvals and electronic signatures. Every approval guard needs at least one approver and should state whether the author may approve. Segregation of duties means the author may not approve.

## Failure paths
Every review gate needs a failure transition that returns work to a rework state, with the findings recorded. Without a failure path, reviewers are forced to approve or leave work in limbo.

## Side states
Blocked states should record the blocker reason and owner and return to the state the item came from. Long blocked times should escalate automatically.

## Naming
Name states after the activity or condition, not the person: Security Review rather than With Security Team. Name transitions as verbs: approve review, release, roll back.

## Change management of workflows
Workflow changes affect metrics and in flight items. Version every template, record the reason for each customisation and keep a changelog so audits can reconstruct which rules applied at any time.
