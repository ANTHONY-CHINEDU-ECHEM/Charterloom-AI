# Post Mortem Practice

## Purpose
Every project closes with a blameless post mortem. Post mortems turn experience into reusable knowledge: they are indexed in the organisational archive and retrieved when new projects with similar characteristics start.

## Blameless principles
Focus on systems, processes and decisions rather than individuals. Assume people acted reasonably given the information they had. Ask what made the problem possible and what would have caught it earlier.

## Structure
* Summary and outcome score.
* What went well.
* What did not go well.
* Root causes.
* Lessons and recommended workflow adjustments, written so that they can be applied to a future workflow configuration.

## Writing useful recommendations
A useful recommendation names a concrete change to the workflow: add a security review gate before release, require a rollback plan on the release transition, add a migration rehearsal stage, tighten WIP limits, add a weekly dependency sync. Vague recommendations such as communicate better cannot be acted upon.

## Outcome scoring
Projects are scored from zero to one using on time delivery, defect escape rate, cycle time, stakeholder satisfaction, compliance findings and budget variance. Projects at or above the median outcome score of the archive are labelled high performing, and their workflows are treated as positive precedents.

## Using post mortems for new projects
When a new charter arrives, the post mortems of the most similar historical projects are retrieved. Recommendations that recur across several similar projects carry more weight than a single mention, and their weight increases with the similarity of the source project.
