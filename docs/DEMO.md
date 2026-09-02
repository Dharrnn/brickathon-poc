# Demo runbook — Supply Chain Disruption Intelligence

<!-- Type: How-to Guide -->

- **Status:** Live
- **Last reviewed:** 2026-09-02
- **Audience:** the person presenting the Builder Launchpad demo

Two parts: **Part A** gets the workspace demo-ready once; **Part B** is the
5–6 minute story you tell on the day. Do Part A well before you present.

## Part A — one-time setup (do before the demo)

Run these in order. Everything you upload comes from your local clone at
`/Users/dharan/Coding/supply-chain-disruption/`.

1. **Pull the latest** in the Databricks Git folder (branch button → Pull). If it
   flags local edits, Discard all changes, then Pull.
2. **Upload the final wheel** → `dist/scdi-0.1.0-py3-none-any.whl` to
   `/Volumes/workspace/supply_chain/raw/wheels/` (overwrite if present).
3. **Upload the demo data:**
   - `data/demo/ais.csv` → `raw/ais/`
   - `data/demo/weather.csv` → `raw/weather/` (overwrites the old `weather.csv`)
   - Remove the tiny sample so it doesn't mix in:
     `dbutils.fs.rm("/Volumes/workspace/supply_chain/raw/ais/ais_sample.csv")`
4. **Run the pipeline:** `01_bronze_ingest → 10_build_silver → 20_enrich_weather →
   30_score_gold → 40_genie_summaries` (Serverless, Run all each). After `30` you
   should have **`workspace.supply_chain.disruption_risk`** with ~31 vessels
   (≈11 high · 17 medium · 3 low).
5. **Create the Metric View:** Catalog Explorer → Create → Metric view → paste
   `metrics/disruption_risk.metricview.yml` → save.
6. **Build the dashboard:** New → Dashboard. Import
   `dashboards/disruption_dashboard.lvdash.json`, or add datasets from
   `dashboards/queries.sql` and let the Assistant chart them. Make sure you have:
   - a KPI counter (high-risk vessels),
   - the **High Risk Vessels** table incl. the `reasoning` column,
   - **Port Zone Risk** (bar),
   - the **risk map** — a *Symbol map* on `avg_lat` / `avg_lon`, coloured by
     `risk_band` (View 5 in `queries.sql`),
   - a **risk-band filter**.
7. **Create the Genie space:** New → Genie space → add the `disruption_risk`
   table + Metric View → paste Instructions, synonyms and trusted SQL from
   `genie/instructions.md` → seed the four sample questions.

Smoke-test it: ask Genie *"which vessels are at highest risk?"* — you should get a
ranked answer. If `40` failed (AI functions off), that's fine — the dashboard and
Genie use the `nl_summary` / `reasoning` already written by `30`.

## Part B — the demo script (5–6 min)

### 1. The problem (15s)
> "Port delays cost supply-chain teams millions. Operators need to know *which*
> vessels are about to be delayed, *why*, and *what to do* — right now, not in a
> weekly report."

### 2. The data foundation (30s)
Catalog → `workspace.supply_chain`. Point at the flow:
> "We ingest AIS vessel positions and enrich them with marine weather, in a
> Bronze→Silver→Gold medallion. Bad records are quarantined, not dropped."
Show `ais_raw` → `vessel_positions` → `disruption_risk`.

### 3. The dashboard (2 min)
Open the dashboard.
> "31 vessels across five ports. Eleven are high-risk right now."
- **High Risk Vessels** table — scroll to the `reasoning` column.
- **Risk map** — "LA and New York light up red; Oakland is calm."
- **Port Zone Risk** bar, **Suggested Action**.
- Flip the **risk-band filter** to `high`: "This is the operator's worklist."

### 4. The 'why' — explainable scoring (45s)
Point at one high-risk vessel's `reasoning`, e.g.
*"Severe marine weather (40); Vessel slowdown near port (35.6); Busy port
proximity (20)."*
> "Every score explains itself — no black box. You see exactly which factors drove
> it and by how much."

### 5. The conversational layer — Genie (1.5 min)
Open the Genie space and ask, live:
1. *"Which vessels are currently at highest disruption risk?"*
2. *"Why is the Los Angeles zone flagged?"*
3. *"Which weather factors are contributing most to delay risk?"*
4. *"What action should operations consider for the top vessel?"*
> "A non-technical operator just asks in plain English — same curated data behind
> the dashboard."

### 6. The differentiator — configurable factors (30s)
Open `src/scdi/factors.yml` (or notebook `30`'s `factors_config` widget).
> "The risk model is *data, not code*. If weather should matter more this season,
> we change a weight here and re-score — no engineering change. Add a new factor
> like port congestion the same way."

### 7. Close (15s)
> "End-to-end on Databricks Free Edition: ingest → medallion → a configurable,
> explainable risk model → an AI/BI dashboard → a Genie assistant. Built in a
> weekend, and every number is traceable."

## Reset before presenting

- Re-run notebook `30` so the Gold table is fresh.
- Open the dashboard once (warm the queries) and clear any stray filter.
- Open the Genie space and pre-run question 1 so the first answer is instant.

## Troubleshooting on the day

| Symptom | Fix |
|---|---|
| Genie answer is vague | Re-check the Instructions/synonyms are pasted; ask a more specific question. |
| `40` (ai_gen) errors | Skip it — `reasoning` + `nl_summary` from `30` already power the demo. |
| Map is empty | Confirm the dataset uses `avg_lat`/`avg_lon` and the viz is a Symbol map. |
| Dashboard import failed | Build the four widgets from `dashboards/queries.sql` — 5 minutes. |
