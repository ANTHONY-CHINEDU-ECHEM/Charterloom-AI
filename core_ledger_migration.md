# Project Charter: Tidal Cutover

Domain: Financial Services. Business unit: Treasury Operations. Initiative type: data platform migration.

## Purpose
The purpose of Tidal Cutover is to migrate the reconciliation ledger from the legacy data centre to the strategic cloud data platform and decommission the legacy store.

## Background
The work includes migrating approximately 48 million records from the legacy platform, and historical data must be reconciled before the old system is switched off. Previous infrastructure changes caused two major incidents last year, so change control is under scrutiny from the operational risk team.

## Objectives
* Complete the migration with zero unreconciled records.
* Exit the legacy data centre by the end of the financial year.
* Reduce hosting cost of the ledger by 40 percent.

## Scope
In scope: data extraction, transformation, reconciliation, the cutover runbook and decommissioning.
Out of scope: Replacement of the finance general ledger. New reporting features.

## Team and Stakeholders
The delivery team comprises 8 people organised into 1 team, working with a cloud platform team and an external migration vendor. The planned duration is 30 weeks from mobilisation.

## Constraints and Assumptions
The service processes about 350,000 transactions per day and outages have immediate customer impact. All changes require an approved implementation plan and a defined change window, and the quarterly change freeze applies. A cutover weekend is planned to move live data to the new platform. An external vendor supplies the migration tooling under a fixed price contract.

## Regulatory and Compliance Context
Controls required under Sarbanes Oxley Section 404 internal controls apply to this service. Compliance with the EU Digital Operational Resilience Act must be demonstrated before go live.
