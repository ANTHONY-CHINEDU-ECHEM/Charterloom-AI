# Project Charter: Granite Ledger Sustainment

Domain: Energy and Utilities. Business unit: Customer Billing.

## Purpose
The purpose of Granite Ledger Sustainment is to keep the domestic billing engine secure, patched and performant while working down a defect backlog of roughly 600 tickets.

## Background
Roughly 55 percent of team capacity is consumed by unplanned tickets and urgent fixes raised through the service desk. Demand is interrupt driven, with priority one incidents expected to be picked up within the hour because billing failures delay payments for 1.8 million customers.

## Objectives
* Reduce the open defect backlog by 50 percent within nine months.
* Resolve priority one incidents within four hours in 95 percent of cases.
* Retire 3 unsupported batch components.

## Scope
In scope: the billing engine, tariff tables, payment file interfaces and the associated batch schedule.
Out of scope: Replacement of the billing platform. Changes to the customer portal.

## Team and Stakeholders
The delivery team comprises 6 people organised into 1 team, supported by a service owner in Customer Billing. The engagement is ongoing with an initial horizon of 52 weeks.

## Constraints and Assumptions
The platform is classified as a critical service with a recovery time objective of 60 minutes. Customer identity and financial data flow through the service. Changes to production must respect the monthly billing run freeze.

## Regulatory and Compliance Context
The solution falls within scope of UK GDPR and the Data Protection Act 2018. Standard information security and data handling policies apply.
