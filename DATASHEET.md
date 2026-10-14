# Knowledge Base Datasheet

## Purpose
This archive stands in for the confidential project history of a mature delivery organisation. It feeds the Charterloom retriever, trains the recommendation head and calibrates the customizer.

## Composition

<table>
<thead><tr><th>File or folder</th><th>Records</th><th>Description</th></tr></thead>
<tbody>
<tr><td><code>blueprints.jsonl</code></td><td>2,400</td><td>One historical project per line: charter, adopted workflow, applied adjustments, outcome score, outcome metrics, high performing flag and an indexable narrative</td></tr>
<tr><td><code>post_mortems.jsonl</code></td><td>2,400</td><td>One blameless post mortem per project with recommended workflow adjustments</td></tr>
<tr><td><code>methodologies/</code></td><td>22</td><td>Hand written methodology guidance in Markdown</td></tr>
<tr><td><code>workflow_templates/</code></td><td>8</td><td>Canonical state machines in JSON with an indexable description</td></tr>
<tr><td><code>ground_truth/latent_labels.jsonl</code></td><td>2,400</td><td>Latent optimal workflow, utility scores, needed adjustments and true signals; evaluation only, never indexed</td></tr>
<tr><td><code>manifest.json</code></td><td>1</td><td>Generation statistics</td></tr>
</tbody>
</table>

## Blueprint fields
<table>
<thead><tr><th>Field</th><th>Meaning</th></tr></thead>
<tbody>
<tr><td>blueprint_id, project_id</td><td>Identifiers, for example BP00042 and PRJ00042</td></tr>
<tr><td>title, codename</td><td>Project codename and product</td></tr>
<tr><td>domain, business_unit, project_type</td><td>One of 13 domains and 12 initiative types</td></tr>
<tr><td>year, quarter</td><td>Delivery period between 2019 and 2026</td></tr>
<tr><td>team_size, teams, duration_weeks</td><td>Team shape and planned duration</td></tr>
<tr><td>regimes</td><td>Regulatory regimes in scope</td></tr>
<tr><td>workflow_archetype, fit</td><td>Adopted workflow and whether it was the optimum, the runner up or a mismatch</td></tr>
<tr><td>adjustments_applied</td><td>Adjustments the project actually used</td></tr>
<tr><td>outcome_score, outcome_metrics</td><td>Score from zero to one plus on time delivery rate, defect escape rate, median cycle time, stakeholder satisfaction, compliance findings and budget variance</td></tr>
<tr><td>high_performing</td><td>True when the outcome score is at or above the archive median</td></tr>
<tr><td>charter, text</td><td>Charter in Markdown and the indexable blueprint narrative</td></tr>
</tbody>
</table>

## Generative process
1. Sample an initiative type (weighted), a domain, delivery signals conditional on the type, team shape, duration and regimes conditional on the domain.
2. Score each workflow archetype with a transparent additive utility model, add Gumbel noise with scale 0.35 and take the argmax as the latent optimal workflow.
3. Derive the needed adjustments from the signals and regimes with explicit rules, including regime mandated controls.
4. Write the charter: each true signal is mentioned with probability 0.80 using varied phrasing, false cues appear with probability 0.045 each, the initiative type is stated with probability 0.55, team facts with probability 0.85 to 0.88 and each regime with probability 0.88.
5. Adopt the optimal workflow with probability 0.58, the runner up with probability 0.27 and a random other archetype otherwise. Apply each needed adjustment with probability 0.55.
6. Compute the outcome score from workflow fit, adjustment coverage, team maturity and noise, then derive the outcome metrics.
7. Write the post mortem: each needed adjustment is recommended with probability 0.90 and spurious recommendations appear with probability 0.025 each.

## Reproducibility
Generation is fully deterministic for a given seed (1014 by default). Regenerate with `charterloom kb`.

## Intended use and limitations
The archive is designed for developing and evaluating workflow recommendation methods. It is not a record of real projects, organisations or people; codenames are invented. Relationships between attributes and outcomes are simplified, so absolute metric values should not be read as forecasts for a real organisation.
