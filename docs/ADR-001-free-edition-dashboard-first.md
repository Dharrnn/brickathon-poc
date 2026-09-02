# ADR-001: Free Edition dashboard-first, no custom app

<!-- Type: Explanation -->

- **Status:** Accepted
- **Created:** 2026-09-02
- **Last reviewed:** 2026-09-02
- **Deciders:** Builder Launchpad team

## Context

The idea was originally framed as a real-time supply-chain routing platform. The
event target is Databricks Free Edition, which is serverless-only, quota-limited,
restricts outbound internet to trusted domains, and is not for production use.
The internal guidance already preferred a dashboard over an app for this idea.

## Decision

Build a compact analytical prototype: a Bronze→Silver→Gold medallion feeding an
AI/BI dashboard and a Genie natural-language layer. Do not build a custom
application (Tier 3) for the MVP, and do not integrate into the ArcAI Platform.

## Consequences

- The build fits a weekend and the Free Edition quotas.
- The GenAI value is still explicit and user-facing through Genie plus
  AI-generated operator summaries.
- If a custom UI is later required, it will be a Databricks App with its own
  Databricks-native design — not a reuse of the ArcAI frontend, which is a
  production platform on a different stack and would be over-engineering here.
- Tier 3 (an operator console app) is documented as a future option, not built.
