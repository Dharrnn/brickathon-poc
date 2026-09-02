# ADR-002: Rule-based disruption scoring for the MVP

<!-- Type: Explanation -->

- **Status:** Accepted
- **Created:** 2026-09-02
- **Last reviewed:** 2026-09-02
- **Deciders:** Builder Launchpad team

## Context

Disruption risk could be modelled with machine learning, but the event is a
weekend POC on quota-limited compute, there is no labelled delay outcome to train
on, and the Genie layer must be able to explain *why* a vessel is flagged.

## Decision

Score disruption risk with a transparent weighted rule:
`slowdown (0-40) + weather severity (0-40) + port proximity (0-20)`, banded into
low / medium / high. Keep every threshold and weight in one module
(`src/scdi/constants.py`). Generate the operator narrative with the `ai_gen` SQL
function, but write a deterministic template summary (`scdi.narrative`) first so
the dashboard and Genie still work if AI functions are unavailable or
quota-limited in Free Edition.

## Consequences

- Every score is inspectable and easy for Genie to explain in natural language.
- The logic is pure Python, unit-tested locally with no Databricks dependency.
- The model is not predictive of true delay; it flags conditions correlated with
  disruption. A learned model over historical outcomes is a documented future
  step, not part of the MVP.
- Thresholds are tunable in review without touching transform code.
