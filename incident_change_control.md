# Change Controlled Operations

## When to use it
A change controlled lifecycle governs modifications to production infrastructure, platforms and data where a failed change has immediate customer, financial or regulatory impact. Infrastructure upgrades, data centre exits, database migrations, network changes and platform replatforming fall into this category. The lifecycle is aligned with ITIL change enablement practice.

## Lifecycle and states
Change Request, Risk Assessment, Change Advisory Board Review, Scheduled, Implementing, Post Implementation Review and Closed, with Rolled Back and Rejected as side states. An emergency path moves an approved emergency change directly to Implementing, followed by a mandatory retrospective review.

## Change types
* Standard changes are pre approved, low risk and repeatable, and can bypass the board.
* Normal changes are assessed and approved by the change advisory board.
* Emergency changes restore service urgently and are reviewed after the fact.

## Risk assessment
Each change documents its impact, blast radius, dependencies, implementation plan, test evidence and a tested rollback plan, and receives a risk rating that determines the approval route.

## Change windows and freezes
Implementation happens only in agreed change windows. Freeze periods, such as peak trading or financial year end, block normal changes. The workflow enforces freezes automatically rather than relying on memory.

## Automation patterns
Reject implementation requests during a declared freeze. Roll back automatically and page the on call engineer when error budget burn spikes during implementation. Chase overdue post implementation reviews. Create a retrospective review task for every emergency change.

## Metrics
Change failure rate, mean time to restore, emergency change ratio and change lead time. These align with the delivery performance measures popularised by the DORA research programme on software delivery, which is distinct from the EU Digital Operational Resilience Act.

## Signals of a good fit in a charter
Production critical services, recovery time objectives, change freezes, change advisory boards, previous major incidents, migrations with cutover weekends and infrastructure end of life.

## Common failure modes
Sending every low risk change to the board creates queues that encourage large, risky batches. Post implementation reviews that are skipped lose the learning that reduces future failures.
