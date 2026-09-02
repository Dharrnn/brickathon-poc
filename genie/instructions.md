# Genie space — Supply Chain Disruption Intelligence

<!-- Type: Reference -->

Configuration for the Databricks **Genie space** (Tier 2). Paste the instructions
into the Genie space **Instructions** box, add the sample SQL as **trusted
queries / example SQL**, and register the synonyms. Genie sits on the same
`disruption_risk` Gold table and `disruption_risk` Metric View as the dashboard,
so answers stay consistent (ADR-002).

- **Last reviewed:** 2026-09-02

## Curated assets to expose

- Table `workspace.supply_chain.disruption_risk` (Gold).
- Metric View `workspace.supply_chain.disruption_risk` (semantic layer).
- Optionally `workspace.supply_chain.vessel_positions` (Silver) for drill-down.

## Instructions (paste into Genie)

```
This space answers questions about maritime supply-chain disruption risk. Each
row in disruption_risk is one vessel observed inside a port zone over a time
window.

Definitions:
- delay_score: 0-100 rule-based disruption risk. Higher = more likely delay. It
  is the weighted sum of contributing factors.
- risk_band: 'high' (score >= 60), 'medium' (30-59), 'low' (< 30).
- top_factor: the single factor contributing the most to this vessel's score
  (e.g. 'Severe marine weather', 'Vessel slowdown near port').
- reasoning: a human-readable breakdown of every contributing factor and its
  points, e.g. "Severe marine weather (40); Vessel slowdown near port (35.6)".
- factor_breakdown: the same breakdown as JSON (id, weight, contribution, points).
- slowdown_flag: true when the vessel was moving below 3 knots inside a port
  zone (a congestion / waiting-for-berth signal).
- weather_severity: 0-1 marine weather factor from wind, gusts, precipitation and
  wave height.
- port_zone: the port area the vessel was in (e.g. la_long_beach, oakland).
- recommended_action / operator_summary: the suggested operator response.

Rules for answering:
- "at risk" / "flagged" means risk_band = 'high' unless the user says otherwise.
- When asked WHY something is flagged, return its top_factor and reasoning
  (they already spell out each factor's contribution).
- Default to ordering by delay_score DESC and returning the operator_summary.
- If a port is named in plain English (e.g. "Los Angeles"), map it to the
  matching port_zone.
```

## Synonyms

```
vessel        -> vessel_name, mmsi, ship, boat
at risk       -> risk_band = 'high'
flagged       -> risk_band = 'high'
risk level    -> risk_band
delay risk    -> delay_score
congestion    -> slowdown_flag = true
slowdown      -> slowdown_flag = true
weather       -> weather_severity
port          -> port_zone
Los Angeles   -> la_long_beach
Long Beach    -> la_long_beach
Oakland       -> oakland
San Francisco -> oakland
Seattle       -> seattle_tacoma
New York      -> ny_nj
Houston       -> houston
action        -> recommended_action, operator_summary
```

## Sample questions (seed these in the space)

1. Which vessels are currently at highest disruption risk?
2. Why is the Los Angeles zone flagged?
3. Which weather factors are contributing most to delay risk?
4. What action should operations consider for the top vessel?

## Trusted example SQL

```sql
-- Q1: highest-risk vessels
SELECT vessel_name, port_zone, delay_score, risk_band, operator_summary
FROM disruption_risk_final
ORDER BY delay_score DESC
LIMIT 10;
```

```sql
-- Q2: why is a given port zone flagged
SELECT vessel_name, avg_sog, slowdown_flag, weather_severity, delay_score, risk_band
FROM disruption_risk
WHERE port_zone = 'la_long_beach'
ORDER BY delay_score DESC;
```

```sql
-- Q3: weather contribution across flagged zones
SELECT port_zone,
       ROUND(AVG(weather_severity), 2) AS avg_weather_severity,
       COUNT_IF(risk_band = 'high')    AS high_risk_vessels
FROM disruption_risk
GROUP BY port_zone
ORDER BY avg_weather_severity DESC;
```

```sql
-- Q4: recommended action for the single highest-risk vessel
SELECT vessel_name, port_zone, risk_band, operator_summary
FROM disruption_risk_final
ORDER BY delay_score DESC
LIMIT 1;
```
