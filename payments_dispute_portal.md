# Project Charter: Clearwater Disputes

Domain: Financial Services. Business unit: Payments.

## Purpose
The purpose of Clearwater Disputes is to deliver a self service card dispute portal that lets retail customers raise, evidence and track chargeback claims in the mobile app without calling the contact centre. Disputes currently generate 41,000 calls a month and the average claim takes 19 days to resolve.

## Background
Customer research shows strong demand, but we do not yet know which dispute types customers will be comfortable resolving digitally, so requirements are expected to evolve as we learn from early customer feedback. Competitors launched similar features last year and priorities are likely to shift every few weeks as their offerings are assessed. Product analytics will shape the roadmap after the first release.

## Objectives
* Move 60 percent of dispute claims to the digital channel within twelve months.
* Reduce average resolution time from 19 days to 8 days.
* Achieve a customer satisfaction score above 4.4 out of 5 for the dispute journey.

## Scope
In scope: the dispute journey in the mobile app and web banking, evidence upload, case status tracking and integration with the card processor dispute API.
Out of scope: Changes to the fraud operations case management system. Business card disputes.

## Team and Stakeholders
The delivery team comprises 9 people organised into 1 team, with a dedicated product owner from Payments. The planned duration is 28 weeks from mobilisation. Stakeholders include representatives from 6 departments, including fraud operations, complaints, legal and the contact centre, so a broad stakeholder group must stay informed.

## Constraints and Assumptions
The team deploys to production several times per day behind feature flags. Customers will access the service from their own devices without assistance. Peak load is forecast at 2,400 requests per second when card statements are issued at month end. Customer identity and financial data flow through the service, including card numbers and transaction history.

## Regulatory and Compliance Context
Compliance with PCI DSS v4.0 must be demonstrated before go live because cardholder data is displayed and transmitted. The journey falls within scope of the FCA Consumer Duty and must evidence good customer outcomes. The solution falls within scope of UK GDPR and the Data Protection Act 2018.
