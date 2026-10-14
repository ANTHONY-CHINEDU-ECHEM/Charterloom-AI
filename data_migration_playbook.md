# Data Migration Playbook

## Purpose
Migrations move live data from a legacy platform to a new one. They fail in predictable ways: incomplete mapping, poor source data quality, underestimated volumes and cutovers that were never rehearsed. A migration rehearsal stage in the workflow addresses all of them.

## Phases
* Discovery: profile source data, quantify quality issues and agree mapping rules.
* Build: develop extraction, transformation and load routines with automated reconciliation.
* Rehearsal: run the full migration end to end at production volumes in a production like environment, at least twice.
* Cutover: execute the rehearsed plan in an agreed window with go or no go checkpoints.
* Hypercare: monitor closely and keep the legacy system available read only until reconciliation is signed off.

## Reconciliation evidence
Each rehearsal produces record counts, control totals and sampled field comparisons between source and target. Reconciliation evidence is the linked artifact on the migration rehearsal gate and is often required by audit teams.

## Rollback
Every cutover needs a rollback point and a decision deadline after which rollback is no longer possible. Rehearse the rollback as well as the migration.

## Signals in a charter
Migrating millions of records, legacy platforms, cutover weekends, decommissioning old systems and reconciling historical data.
