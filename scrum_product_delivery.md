# Agile Scrum Product Delivery

## When to use it
Scrum suits product work where the problem is understood well enough to start but the solution will be discovered through delivery. It works best for a single cross functional team of roughly three to eleven people that can own a product goal end to end. Typical fits are new customer facing features, internal tools with engaged users and rebuilds of existing journeys where feedback from real users will change priorities every few weeks.

Scrum is a poor fit when most work is unplanned, when scope is contractually fixed, or when a regulator requires formal verification and validation records for each requirement. Interrupt heavy work breaks the sprint commitment, fixed scope removes the value of reprioritisation, and regulated release evidence needs a controlled lifecycle on top of the sprint rhythm.

## Lifecycle and states
A canonical Scrum board moves items through Product Backlog, Sprint Backlog, In Progress, Code Review, QA Verification, Ready for Release and Done, with Blocked and Cancelled as side states. Items enter the sprint only during sprint planning and only when they satisfy the definition of ready. Work that does not finish returns to the sprint backlog at the sprint boundary with a carryover label so the team can see chronic overcommitment.

## Guards that matter
* Planning into a sprint requires a story point estimate and agreed acceptance criteria.
* Starting work requires an assignee and available WIP capacity.
* Submitting for review requires a linked pull request.
* Approving review requires an engineer who is not the author.
* Release requires product owner acceptance against the definition of done.

## Automation patterns
Link the version control system so opening a pull request moves the item to Code Review. Alert reviewers when a review waits longer than a working day, because review queues are the most common hidden bottleneck in Scrum teams. Escalate blockers older than two days to the Scrum Master. Run a carryover automation when the sprint closes.

## Cadence and ceremonies
Two week sprints are the default. One week sprints help very small teams with highly volatile priorities; three or four week sprints suit teams with heavier integration overhead but slow down feedback. Ceremonies are sprint planning, a fifteen minute daily scrum, weekly backlog refinement, the sprint review with stakeholders and the retrospective.

## Signals of a good fit in a charter
Language about learning from customers, evolving requirements, prototypes, frequent reprioritisation and a single accountable product owner. A team size below twelve and a delivery horizon of one to nine months.

## Common failure modes
Teams that accept large volumes of support work into sprints miss their goals repeatedly and lose trust. Teams that skip refinement pull unclear stories and reopen them. Teams that treat the sprint review as a status meeting lose the stakeholder feedback loop that justifies Scrum in the first place.
