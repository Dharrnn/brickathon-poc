-- Backing SQL for the AI/BI dashboard (Tier 1). One query per widget.
-- Runs against the Gold table workspace.supply_chain.disruption_risk (or the
-- disruption_risk_final view once 40_genie_summaries has run). Paste each into an
-- AI/BI dataset, or let Genie/Assistant generate the visuals from these.

-- KPI: High risk vessels ------------------------------------------------------
SELECT COUNT_IF(risk_band = 'high') AS high_risk_vessels
FROM disruption_risk;

-- KPI: Port zones flagged -----------------------------------------------------
SELECT COUNT(DISTINCT port_zone) AS zones_flagged
FROM disruption_risk
WHERE risk_band = 'high';

-- KPI: Average delay score ----------------------------------------------------
SELECT ROUND(AVG(delay_score), 1) AS avg_delay_score
FROM disruption_risk;

-- View 1: High Risk Vessels (table) -------------------------------------------
SELECT vessel_name, port_zone, ROUND(avg_sog, 1) AS avg_sog,
       weather_severity, delay_score, risk_band, top_factor, reasoning,
       recommended_action
FROM disruption_risk
ORDER BY delay_score DESC;

-- View 1b: Risk by contributing factor (bar) ----------------------------------
SELECT top_factor, COUNT(*) AS vessels, ROUND(AVG(delay_score), 1) AS avg_delay_score
FROM disruption_risk
GROUP BY top_factor
ORDER BY vessels DESC;

-- View 2: Port Zone Risk (bar) ------------------------------------------------
SELECT port_zone,
       COUNT(DISTINCT mmsi)            AS vessels,
       COUNT_IF(risk_band = 'high')    AS high_risk_vessels,
       ROUND(AVG(delay_score), 1)      AS avg_delay_score,
       ROUND(AVG(weather_severity), 2) AS avg_weather_severity
FROM disruption_risk
GROUP BY port_zone
ORDER BY avg_delay_score DESC;

-- View 3: Suggested Action (grouped) ------------------------------------------
SELECT recommended_action, risk_band, COUNT(*) AS vessels
FROM disruption_risk
GROUP BY recommended_action, risk_band
ORDER BY vessels DESC;

-- View 4: Slowdown vs weather scatter (optional) ------------------------------
SELECT vessel_name, port_zone, avg_sog, weather_severity, delay_score, risk_band
FROM disruption_risk;

-- View 5: Vessel risk MAP (symbol map on avg_lat/avg_lon, colour by risk_band) -
SELECT vessel_name, port_zone, avg_lat, avg_lon, risk_band, delay_score, top_factor
FROM disruption_risk;
