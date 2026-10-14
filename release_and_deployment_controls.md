# Release and Deployment Controls

## Purpose
Release controls reduce the probability and impact of failed changes. They are applied as guards and triggers on the release transition of any workflow archetype.

## Rollback plans
Every production release on a critical service needs a rollback plan that has been rehearsed. The plan states the trigger for rollback, the steps, the owner and the expected time to restore. In the workflow, the rollback plan is a required field and rehearsal evidence is a linked artifact on the release transition.

## Feature flags and progressive delivery
Feature flags decouple deployment from release. Customer facing changes ship dark, then exposure ramps through stages such as one, ten, fifty and one hundred percent while guardrail metrics are watched. A flag also provides an instant kill switch. In the workflow, a feature flag reference is required on release and a progressive rollout automation starts when the release completes.

## Performance testing
Services with high or spiky traffic need load and soak testing against forecast peak demand before release. Results are attached as a load test report to a performance testing gate.

## Change windows
Critical services release only within agreed windows and never during freezes. Freezes are enforced by automation rather than memory.

## Separation of deployment approval
For regulated systems, the person who wrote a change may not approve its release. This segregation is enforced by an approval guard with the author excluded.

## Measuring release health
Change failure rate and time to restore are the primary release health measures. Release frequency and lead time for changes show whether controls are proportionate or have become a bottleneck.
