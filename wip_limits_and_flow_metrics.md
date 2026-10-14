# WIP Limits and Flow Metrics

## Why limit work in progress
Starting work is easy; finishing it is what delivers value. When too much work is in progress, items wait in queues, context switching consumes capacity and cycle times lengthen. Little's Law states that average cycle time equals average work in progress divided by average throughput, so at constant throughput, halving WIP halves cycle time.

## Sizing initial limits
* Active development states: about 0.6 items per person, rounded up, with a minimum of two.
* Review and test states: about 0.35 items per person, with a minimum of two.
* Programme level feature states on a release train: about two features per team.
Treat these as starting points and lower limits until a small amount of slack appears.

## When to tighten
Tighten limits by around a quarter when unplanned work exceeds a third of capacity, when cycle time at the eighty fifth percentile is rising, or when retrospectives repeatedly mention juggling too many items. Tighter limits make bottlenecks visible quickly.

## Service levels
Each active state can carry a service level expressed in hours. Items that exceed the service level are aging and should be swarmed or escalated. Production critical services typically use tighter service levels, for example three quarters of the default.

## Flow metrics
* Throughput: items completed per week.
* Cycle time: elapsed time from start to done, reported at the median and the eighty fifth percentile.
* Work item age: elapsed time for items still in progress, the earliest warning of trouble.
* Flow efficiency: active time divided by total elapsed time; values below fifteen percent are common and show how much time is spent waiting.

## Anti patterns
Limits set so high they never bind; limits ignored by managers who push work in; measuring utilisation of people rather than flow of work.
