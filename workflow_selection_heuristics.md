# Workflow Selection Heuristics

## Purpose
This guide summarises how the delivery practice selects a workflow archetype from a project charter. It is the organisational standard against which automated recommendations are reviewed.

## Primary questions
* How much of the work is known before it starts? High uncertainty favours Scrum or dual track discovery; fixed, baselined scope favours a stage gate lifecycle.
* How does work arrive? Continuous, interrupt driven demand favours Kanban; a mix of roadmap and interrupts in a small team favours Scrumban.
* How many teams must integrate? Four or more teams sharing a release favour a scaled release train.
* What does a regulator need to see? Traceable, signature gated evidence favours the regulated compliance pipeline.
* What happens if a change fails in production? Severe, immediate impact on infrastructure or data favours change controlled operations.
* Is feasibility proven? If not, discovery must precede delivery.

## Decision table
* Evolving product feature, one or two teams: Agile Scrum Product Delivery.
* Maintenance or support with high unplanned load: Kanban Continuous Flow.
* Regulated module with strict evidence obligations: Regulated Compliance Pipeline.
* Hardware, firmware, package implementation or fixed price contract: Stage Gate Phased Delivery.
* Multi team programme with heavy dependencies: Scaled Agile Release Train.
* Research, machine learning feasibility or new market exploration: Dual Track Discovery and Delivery.
* Small team balancing roadmap and moderate interrupts: Scrumban Hybrid Flow.
* Infrastructure upgrade or data platform migration on critical services: Change Controlled Operations.

## Tie breaking
When two archetypes fit, choose the one that controls the largest risk. For example, a regulated machine learning feature should use the regulated pipeline for release with a discovery phase inside it, rather than a discovery workflow with compliance added at the end.

## Evidence from history
Recommendations should be grounded in the outcomes of similar historical projects. A workflow that similar projects used with high outcome scores is stronger evidence than one that was merely common. Post mortems from similar projects reveal which adjustments to the base template were needed.

## Overlays rather than new archetypes
Regulatory obligations, security and privacy reviews, accessibility, performance testing and vendor acceptance are added to any archetype as overlays: extra gates, guards and automations. Creating a bespoke workflow for each combination fragments reporting and training.
