# ADR-004: Disruption risk as a configurable factor model

<!-- Type: Explanation -->

- **Status:** Accepted
- **Created:** 2026-09-02
- **Last reviewed:** 2026-09-02
- **Deciders:** Builder Launchpad team

## Context

The risk score must be tunable and, above all, **explainable** — an operator and
the Genie layer both need to see *why* a vessel is flagged, and the team needs to
change which signals matter without editing and re-testing Python. Hardcoding
weights and thresholds inside scoring functions (ADR-002's first cut) made every
tweak a code change and hid the reasoning.

## Decision

Model the risk as **data**: `src/scdi/factors.yml` declares an ordered list of
factors, each with an `id`, `label`, `kind`, `weight`, `params`, and a
`reason` template, plus the band thresholds and action text. A generic engine
(`scdi.factors.evaluate`) applies them:

```
delay_score = sum(weight * contribution[0..1]) for each factor, capped at 100
```

and returns a per-factor **breakdown** (contribution, points, reason), the
dominant `top_factor`, and a human `reasoning` string. These land in the Gold
table as `top_factor`, `reasoning`, and `factor_breakdown` (JSON).

Extension rules:

- Change a weight, threshold, band, action, or `reason`, or enable/disable a
  factor → edit `factors.yml` only. On Databricks, point notebook `30` at a
  `factors.yml` on the Volume (the `factors_config` widget) — no rebuild.
- Add a factor of an existing `kind` (`slowdown`, `weather_severity`, `in_zone`,
  `zone_congestion`) → add a YAML entry.
- Add a new *kind* → register one evaluator function in `scdi/factors.py`.

## Consequences

- Every outcome carries its reasoning, so Genie and the dashboard explain
  themselves and the `ai_gen` summary is grounded in real factor points.
- Tuning is a config change, unit-testable (`test_factors.py`) and reviewable in
  isolation from transform code.
- The engine is generic: the pipeline always passes the full input set
  (including `zone_slow_count`), so a disabled factor like `zone_congestion`
  becomes live by config alone.
- Trade-off: a fully arbitrary rules DSL was rejected as over-engineering for a
  POC — new signal *shapes* still need a small evaluator, which is the right
  amount of ceremony here.
