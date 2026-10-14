# Scrumban Hybrid Flow

## When to use it
Scrumban combines the pull system and WIP limits of Kanban with selected Scrum practices such as regular retrospectives and lightweight planning. It suits small teams, often six people or fewer, who own a live product and must balance roadmap features with a moderate, steady stream of interrupts, typically fifteen to thirty five percent of capacity.

## Lifecycle and states
Backlog, Ready, In Progress, Review, Testing and Done, with Blocked and Cancelled as side states. There are no sprint boundaries; the team pulls from Ready whenever capacity frees up.

## Planning on demand
Instead of fixed sprint planning, the team plans when the Ready queue falls below a threshold, for example three items. This keeps planning effort proportional to need and avoids planning work that interrupts will displace.

## Interrupt lane
Incidents and urgent requests enter a protected expedite lane at the top of Ready. Tracking the planned versus unplanned ratio makes the cost of interrupts visible to stakeholders.

## Automation patterns
Trigger a planning session when the ready queue runs low. Route incident typed items into the expedite lane. Flag work aging beyond its service level.

## Metrics
Throughput, cycle time, interrupt ratio and the planned versus unplanned split.

## Signals of a good fit in a charter
A small team, a live product with some support load, a mix of roadmap and operational requests, and moderate rather than extreme change in requirements.

## Common failure modes
Teams that adopt Scrumban to avoid planning altogether lose direction. Teams that allow the expedite lane to grow without limit are really running reactive support and should move to Kanban.
