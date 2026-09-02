-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 40 · AI-generated operator summaries
-- MAGIC Regenerate `nl_summary` on the Gold table with a Databricks AI SQL
-- MAGIC function, turning the structured risk fields into an operator-readable
-- MAGIC narrative (likely cause · affected zone · delay risk · mitigation).
-- MAGIC
-- MAGIC The pipeline already writes a deterministic template `nl_summary`
-- MAGIC (`scdi.narrative`), so if AI functions are unavailable or quota-limited in
-- MAGIC Free Edition the dashboard and Genie still work — this step only upgrades
-- MAGIC the phrasing (ADR-002, risk 2).

-- COMMAND ----------

-- Parameters (set as notebook widgets or hard-code your catalog/schema).
-- USE CATALOG workspace; USE SCHEMA supply_chain;

-- COMMAND ----------

CREATE OR REPLACE TABLE disruption_risk_ai AS
SELECT
  *,
  ai_gen(
    'You are a maritime operations analyst. In ONE sentence, tell an operator ' ||
    'the disruption risk and what to do. Vessel: ' || vessel_name ||
    '. Port zone: ' || port_zone ||
    '. Risk band: ' || risk_band ||
    '. Delay score (0-100): ' || CAST(delay_score AS STRING) ||
    '. Top factor: ' || COALESCE(top_factor, 'none') ||
    '. Factor reasoning: ' || COALESCE(reasoning, '') || '.'
  ) AS ai_summary
FROM disruption_risk;

-- COMMAND ----------

-- Prefer the AI phrasing when present, else the deterministic template.
CREATE OR REPLACE VIEW disruption_risk_final AS
SELECT
  * EXCEPT (ai_summary, nl_summary),
  COALESCE(NULLIF(ai_summary, ''), nl_summary) AS operator_summary
FROM disruption_risk_ai;

-- COMMAND ----------

SELECT vessel_name, port_zone, risk_band, delay_score, operator_summary
FROM disruption_risk_final
ORDER BY delay_score DESC;
