# Kanban Continuous Flow

## When to use it
Kanban is the default for maintenance, sustaining engineering and operational support. Work arrives continuously, priorities change daily and the unit of planning is the individual work item rather than a time boxed batch. Charters that describe incident queues, service desk demand, patching, technical debt reduction or a large share of unplanned capacity point strongly towards Kanban.

## Lifecycle and states
Intake, Triage, Ready, In Progress, Peer Review, Deploy and Verify and Done, with Blocked and Rejected as side states. Triage assigns a class of service and an impact assessment within a short service level, typically eight working hours.

## Classes of service
* Expedite: critical incidents and security fixes that bypass the queue and may exceed WIP limits by one.
* Fixed date: work with an external deadline, scheduled backwards from that date.
* Standard: the bulk of the work, pulled first in first out within priority.
* Intangible: debt reduction and improvement work that protects future flow.

## WIP limits
WIP limits are the defining control in Kanban. Start with roughly 0.6 items per person in active development and 0.35 per person in review states, then lower limits until a small amount of idle time appears. Limits that are never reached are not limits. When unplanned work is very high, lower limits further so the team finishes urgent items rather than starting more.

## Automation patterns
Place expedite items at the head of the ready queue and notify the service owner. Refuse transitions that would breach a WIP limit. Flag aging items whose time in state exceeds the service level for that state. Remind owners of approaching fixed date commitments.

## Metrics
Throughput per week, cycle time at the eighty fifth percentile, work item age and flow efficiency. Little's Law links average WIP, throughput and cycle time, so reducing WIP at stable throughput reduces cycle time.

## Signals of a good fit in a charter
Percentages of capacity consumed by unplanned tickets, priority one incident expectations, service level commitments, the phrase business as usual and a long or open ended duration.

## Common failure modes
Boards without WIP limits become to do lists. Teams that never triage let low value requests crowd out urgent work. Kanban adopted for a new product with uncertain scope loses the discipline of a product goal and drifts.
