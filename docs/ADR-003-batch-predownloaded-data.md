# ADR-003: Batch, pre-staged data instead of runtime fetching

<!-- Type: Explanation -->

- **Status:** Accepted
- **Created:** 2026-09-02
- **Last reviewed:** 2026-09-02
- **Deciders:** Builder Launchpad team

## Context

Databricks Free Edition restricts outbound internet access to a limited set of
trusted domains, so a notebook cannot rely on reaching NOAA or Open-Meteo at
runtime. The full NOAA 2024 AIS archive is also 116.7 GB — far too large to
ingest live for a weekend event.

## Decision

Pre-stage all inputs into a Unity Catalog Volume and treat the pipeline as batch:

- Download 2–3 days of NOAA AIS externally and upload the files to the Volume.
- Pre-fetch Open-Meteo weather on a dev machine with
  `scripts/fetch_weather.py` (a small batch, one call per port zone) and upload
  the normalized CSV.
- The pipeline itself makes no outbound calls.

## Consequences

- The build is robust to Free Edition's network restrictions — the top demo
  risk is removed by design, not mitigated at runtime.
- Weather is a reference table, not a live dependency; scoring is reproducible.
- The trade-off is freshness: data is only as current as the last upload. Real-
  time ingestion (Structured Streaming / Auto Loader) is a documented future
  step outside Free Edition.
- The repository bundles synthetic, schema-accurate sample data so it runs
  end-to-end with no downloads at all.
