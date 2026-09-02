"""NOAA AIS field mapping and the curated column contract.

The raw NOAA AIS CSV uses PascalCase headers (MMSI, BaseDateTime, LAT, LON, SOG,
...). We map only the fields the POC needs into a stable snake_case Silver
schema. Marine Cadastre AIS schema reference:
https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf
"""

from __future__ import annotations

# Raw NOAA AIS column -> Silver column. Only the columns we actually use.
AIS_FIELD_MAP: dict[str, str] = {
    "MMSI": "mmsi",
    "BaseDateTime": "ts",
    "LAT": "lat",
    "LON": "lon",
    "SOG": "sog",
    "VesselName": "vessel_name",
}

# Silver `vessel_positions` columns, in order.
SILVER_COLUMNS: list[str] = [
    "mmsi",
    "ts",
    "lat",
    "lon",
    "sog",
    "vessel_name",
    "port_zone",
    "is_slow",
]

# Gold `disruption_risk` columns, in order.
GOLD_COLUMNS: list[str] = [
    "mmsi",
    "vessel_name",
    "port_zone",
    "window_start",
    "window_end",
    "avg_sog",
    "avg_lat",
    "avg_lon",
    "slowdown_flag",
    "weather_severity",
    "delay_score",
    "risk_band",
    "top_factor",
    "reasoning",
    "recommended_action",
    "factor_breakdown",
    "nl_summary",
]
