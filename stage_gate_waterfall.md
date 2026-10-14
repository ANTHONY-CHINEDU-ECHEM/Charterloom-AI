# Stage Gate Phased Delivery

## When to use it
Phased delivery separated by governance gates is appropriate when the cost of change rises steeply over time and scope can be fixed early. Hardware and firmware programmes, commercial package implementations, fixed price supplier contracts and infrastructure procurements all share this property. Once tooling is cut, hardware is ordered or a contract is signed, changing direction is expensive, so decisions are made deliberately at gates.

## Lifecycle and states
Initiation, Requirements Definition, Solution Design, Build, System Testing, Deployment Readiness and Closed, with Change Control and Cancelled as side states.

## Gates
Each gate is a decision point owned by a steering committee: continue, continue with conditions, recycle to the previous phase or stop. A gate review pack typically includes the business case refresh, risk register, schedule and cost performance, quality evidence and readiness for the next phase. Five gates are common: requirements, design, build, readiness and go live.

## Change control
Changes to the baseline scope, budget or end date are raised as change requests and assessed by a change board for impact before they are accepted. Automatic detection of baseline changes in the planning tool should route them into Change Control rather than allowing silent drift.

## Automation patterns
Book a gate review when a gate transition is requested. Route baseline changes to change control. Alert the sponsor when milestones slip beyond tolerance.

## Metrics
Schedule performance index, cost performance index, change request volume and defect density in system testing.

## Signals of a good fit in a charter
Contractually fixed scope, baselined specifications, hardware prototypes, firmware certification, fixed price vendors, long durations beyond forty weeks and immovable deadlines.

## Combining with agile practice
Phased governance does not forbid iterative work inside phases. Build can run in short iterations with frequent integration, provided the gate criteria remain explicit. This hybrid is often called agile within a stage gate.

## Common failure modes
Applying stage gates to work with high uncertainty produces long phases of speculative documentation. Gate reviews that only check paperwork, rather than evidence of working outcomes, add delay without reducing risk.
