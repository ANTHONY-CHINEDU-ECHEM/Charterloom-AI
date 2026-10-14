# Security and Privacy Gates

## Security review gate
A security review gate places an independent security engineer between development and release. It is required when personal data is exposed to public channels, when the service falls under PCI DSS, ISO/IEC 27001, HIPAA, DORA or NIS2, and when a production critical financial or energy service changes.

The review covers threat modelling for new data flows, results of static and dynamic analysis, dependency vulnerability scanning, authentication and authorisation changes, and secrets handling. Findings return the item to rework with the findings recorded; approval requires a security engineer who did not author the change.

Teams that discover vulnerabilities through penetration testing days before launch, or through external reports after launch, almost always lacked an explicit gate.

## Privacy impact assessment gate
A privacy gate ensures that lawful basis, data minimisation, retention and data subject rights are settled before personal data processing changes go live. Under UK GDPR, a data protection impact assessment is required for processing likely to result in high risk. The data protection officer or a delegate approves the gate.

Signals in a charter: personal data, identity data, health information, contact details, account history, profiling, and named regimes such as UK GDPR or HIPAA.

## Ordering of gates
When several gates apply, performance testing precedes security review, which precedes privacy and accessibility review, followed by model validation, migration rehearsal, vendor acceptance and finally user acceptance testing. This order runs technical gates before business acceptance so the accepting party signs off the final candidate.
