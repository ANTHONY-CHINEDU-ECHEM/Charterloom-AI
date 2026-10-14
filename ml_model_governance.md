# Machine Learning Model Governance

## Purpose
Models that influence decisions about customers, patients or money need governance proportionate to their impact. Governance is applied through a model validation gate before a model is promoted to production, and through monitoring afterwards.

## Model validation gate
An independent reviewer, who did not build the model, checks:
* Data provenance, consent and representativeness.
* Leakage between training features and labels.
* Performance against agreed thresholds on a held out test set that reflects production conditions.
* Fairness across relevant groups, including disparities in error rates.
* Calibration, where scores are used as probabilities.
* Robustness to plausible shifts in inputs.
* A monitoring plan for drift in inputs, predictions and outcomes.

Validation produces a report and a model card that states intended use, limitations and owners.

## Thresholds agreed in advance
Promotion criteria must be agreed before training results are known. Moving thresholds after seeing results undermines the gate.

## Monitoring after release
Track input drift, prediction drift and, where labels arrive, realised performance. Set alerts that open review tasks when drift exceeds tolerance.

## Signals in a charter
Machine learning models, predictions, scoring, classification, drift, trained models and automated decisions.

## Common failure modes
Offline performance that does not hold in production because evaluation data was not representative; bias discovered through complaints; models retrained without revalidation.
