# Supply Chain Disruption Intelligence Dashboard

<!-- Type: How-to Guide -->

Databricks Free Edition POC for **Builder Launchpad**. Combines a small slice of
NOAA AIS vessel movements with Open-Meteo weather to flag **vessel-slowdown +
severe-weather + port-proximity** disruption risk, and surfaces it in an AI/BI
dashboard with a Genie natural-language query layer.

- **Status:** Live (POC)
- **Last reviewed:** 2026-09-02
- **Surface:** Databricks Free Edition — Unity Catalog, Delta, AI/BI Dashboards,
  Genie. Dashboard-first (no custom app). See
  [ADR-001](docs/ADR-001-free-edition-dashboard-first.md).

## What it produces

A **Bronze → Silver → Gold** medallion, a Unity Catalog **Metric View** semantic
layer, an **AI/BI dashboard** (High Risk Vessels · Port Zone Risk · Suggested
Action), and a **Genie space** for questions like *"which vessels are at highest
risk?"* and *"why is the Los Angeles zone flagged?"*.

| Layer | Table | Contents |
|---|---|---|
| Bronze | `ais_raw` | Raw AIS records as ingested |
| Silver | `vessel_positions` | Clean positions — `mmsi, ts, lat, lon, sog, port_zone, is_slow` |
| Silver | `vessel_positions_quarantine` | Rejected rows + `quarantine_reason` |
| Gold | `disruption_risk` | `vessel, port_zone, avg_sog, weather_severity, delay_score, risk_band, top_factor, reasoning, recommended_action, factor_breakdown, nl_summary` |

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full diagram and data
flow. The design principle: **all transform/scoring logic is pure Python in
`src/scdi/`** (runs and unit-tests locally); the Databricks notebooks are thin
wrappers that read from a Unity Catalog Volume and persist Delta tables.

## Run it locally (no Databricks needed)

Proves the whole pipeline end-to-end on the bundled sample data.

```bash
uv sync --extra dev
uv run pytest -q                 # unit tests on the scoring/cleaning core
uv run python scripts/run_local.py   # Bronze -> Silver -> Gold on data/sample/
```

`run_local.py` writes the curated tables to `data/out/` and prints the ranked
`disruption_risk` table.

## Run it on Databricks

1. Upload `data/sample/` (or your pre-downloaded NOAA AIS + pre-fetched
   Open-Meteo files) to a Unity Catalog **Volume**. See
   [ADR-003](docs/ADR-003-batch-predownloaded-data.md) for why data is
   pre-staged rather than pulled at runtime.
2. Run the notebooks in order:
   `01_bronze_ingest` → `10_build_silver` → `20_enrich_weather` →
   `30_score_gold` → `40_genie_summaries`.
3. Create the Metric View from `metrics/disruption_risk.metricview.yml`.
4. Build the dashboard (`dashboards/`) and the Genie space
   (`genie/instructions.md`) on top of the Gold table / Metric View.

Or deploy the whole thing as a bundle: `databricks bundle deploy` (see
[databricks.yml](databricks.yml)).

## Assumptions, sessionization & data quality (Tier 0)

- **Sample-first (ADR-003).** The full NOAA 2024 AIS archive is 116.7 GB. This
  POC ingests 2–3 days (and the bundled sample is synthetic-but-schema-accurate
  so the repo is self-contained and deterministic).
- **Sessionization.** Gold aggregates Silver positions per `(mmsi, port_zone)`
  over the batch window: `avg_sog`, `window_start`, `window_end`. Only positions
  that fall inside a port zone contribute (open-water transit is out of scope).
- **Data quality — quarantine, don't drop.** Rows with an out-of-range lat/lon,
  a non-9-digit MMSI, or an unparseable timestamp are routed to
  `vessel_positions_quarantine` with a reason, so bad-record volume is
  observable. Valid positions are de-duplicated on `(mmsi, ts)`.
- **Weather match.** Each vessel/zone window takes the **worst** weather severity
  the zone saw during that window (wind / gust / precipitation → `[0,1]`).
- **Scoring is a configurable factor model** (ADR-004):
  `delay_score = sum(weight × contribution)` over factors declared in
  `src/scdi/factors.yml` — `slowdown (40) + weather (40) + port-proximity (20)`,
  banded low/medium/high. Every Gold row carries its `top_factor`, a human
  `reasoning` string, and the full `factor_breakdown` JSON, so the outcome
  explains itself.

## Configurable factor model

The risk model is **data, not code**. Change weights, thresholds, bands, action
text, or the per-factor `reason`, or enable/disable a factor, by editing
`src/scdi/factors.yml` — no Python changes. Adding a factor of an existing
`kind` (`slowdown`, `weather_severity`, `in_zone`, `zone_congestion`) is a YAML
entry; a brand-new `kind` adds one evaluator in `src/scdi/factors.py`. On
Databricks, point notebook `30`'s `factors_config` widget at a `factors.yml` on
the Volume to re-tune the model without rebuilding the wheel. See
[ADR-004](docs/ADR-004-configurable-factor-model.md).

## Layout

```
src/scdi/        pure, testable core (clean, zones, weather, factors, pipeline)
src/scdi/factors.yml   configurable risk-factor model (weights, thresholds, reasons)
notebooks/       thin Databricks orchestration (Bronze->Gold + ai_gen summaries)
metrics/         Unity Catalog Metric View (semantic layer for dashboard + Genie)
dashboards/      AI/BI dashboard definition
genie/           Genie space instructions, sample SQL, synonyms
scripts/         run_local.py, fetch_ais.py (real NOAA), fetch_weather.py (Open-Meteo)
data/            ports.json + synthetic sample; real fetches land in data/raw/
docs/            architecture + ADRs
tests/           pytest suite
```

## Fetching real data

The bundled `data/sample/` is synthetic but schema-accurate (deterministic for
tests). For real inputs, run these on a machine with internet, then upload the
output to the Volume (ADR-003):

```bash
# 2-3 real NOAA AIS days, filtered to the port zones, thinned to 30-min pings
uv run python scripts/fetch_ais.py --dates 2024-01-01 2024-01-02 --out data/raw/ais/ais_sample.csv
# Open-Meteo wind/gust/precip + marine wave height, per port zone
uv run python scripts/fetch_weather.py --days 3 --out data/raw/weather.csv
```
