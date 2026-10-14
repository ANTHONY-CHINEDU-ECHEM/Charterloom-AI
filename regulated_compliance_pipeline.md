# Regulated Compliance Pipeline

## When to use it
Use a regulated pipeline when software forms part of a regulated product or process and the organisation must demonstrate, to an auditor or regulator, that every requirement was specified, risk assessed, implemented, verified and validated under control. Typical contexts are FDA 21 CFR Part 11 electronic records, IEC 62304 medical device software, ISO 13485 quality systems, Sarbanes Oxley financial controls and payment systems subject to PCI DSS.

The pipeline can still be iterative internally. Many regulated teams run sprints inside the Implementation state; what changes is that release is controlled, evidence is mandatory and approvals are segregated.

## Lifecycle and states
Draft Requirement, Requirements Traceability, Design Review, Implementation, Verification, Independent Validation, Compliance Review, Release Authorisation and Released, with On Hold and Rejected as side states.

## Mandatory controls
* Traceability: every requirement links to a risk control and a verification method before design starts.
* Segregation of duties: the person who authored a change may not approve its verification, validation or release.
* Electronic signatures: release authorisation captures a signature with its meaning, the signer identity and a time stamp, which is the core of 21 CFR Part 11 compliance for electronic approvals.
* Audit trail: every state change writes an immutable, time stamped record that cannot be edited by users.
* Nonconformance and CAPA: failed verification opens a nonconformance record; failed validation opens a corrective and preventive action.

## Automation patterns
Write audit records on every transition. Block progression into Verification or Release Authorisation until mandatory evidence such as executed test protocols is attached. Open CAPA records automatically on validation failure. Schedule a monthly review of who holds approval and signature rights.

## Metrics
Traceability coverage, first pass validation rate, open CAPA count and age, and audit findings per release.

## Signals of a good fit in a charter
Named regulations with strictness such as Part 11, IEC 62304, ISO 13485, Sarbanes Oxley Section 404 or MiFID II record keeping; phrases such as audit findings, validated system, design history file, quality assurance signoff and inspection readiness.

## Common failure modes
Retrofitting evidence at the end of the project is expensive and often fails inspection. Treating compliance review as a final step rather than a continuous concern creates large batches of findings. Over controlling low risk changes slows delivery without improving safety, so risk based classification of changes is recommended.
