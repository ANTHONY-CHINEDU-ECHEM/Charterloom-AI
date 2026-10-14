# Dual Track Discovery and Delivery

## When to use it
Dual track working separates learning what to build from building it. A discovery track tests hypotheses quickly and cheaply; only validated ideas move into a delivery track. This archetype suits machine learning research, new market exploration, data products whose feasibility is unproven, and any initiative where the biggest risk is building the wrong thing or building something that cannot work.

## Lifecycle and states
Opportunity Backlog, Hypothesis Framing, Discovery Research, Experiment Running, Evidence Review, Delivery Backlog, Building, Validation in Production and Learned and Shipped, with Blocked and Discarded as side states.

## Hypotheses and kill criteria
Every discovery item starts with a falsifiable hypothesis, a success metric and kill criteria agreed before the experiment begins. Agreeing kill criteria in advance protects the team from sunk cost reasoning when results disappoint. Discarding a hypothesis is a successful outcome when it is recorded as learning.

## Timeboxes
Research spikes and experiments carry an explicit timebox, commonly three to ten working days. When a timebox expires, the product trio must decide to continue, pivot or stop. Without timeboxes, research expands to consume the budget.

## Machine learning specifics
For model development, discovery covers data availability, label quality, baseline performance and offline evaluation. Promotion to delivery should require an independent model validation covering performance thresholds, bias across relevant groups, leakage checks and a drift monitoring plan. A model card documents intended use and limitations.

## Automation patterns
Attach experiment telemetry automatically when evidence is collected. Evaluate kill criteria daily while experiments run. Maintain a learning log of every validated and invalidated hypothesis.

## Metrics
Hypotheses tested per month, validated learning rate, time to evidence and outcome attainment for shipped items.

## Signals of a good fit in a charter
Feasibility is unproven, competing hypotheses, experiments, establishing whether data supports a solution, prototypes, research questions and predictive models.

## Common failure modes
Discovery that never feeds delivery becomes an innovation theatre. Delivery that bypasses discovery ships unvalidated ideas. Experiments without kill criteria run indefinitely.
