"""Silver -> Gold: aggregate vessel behaviour per zone, join weather, score.

Kept in pandas so the whole pipeline runs locally on the sample data AND inside a
Databricks notebook (the sample is small by design — ADR-003). Scoring goes
through the configurable factor engine (`scdi.factors`), so each Gold row carries
its `delay_score`, the dominant `top_factor`, a human `reasoning` string, and the
full `factor_breakdown` (ADR-004).
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd

from scdi.factors import RiskModel, evaluate
from scdi.narrative import build_summary
from scdi.schema import GOLD_COLUMNS
from scdi.weather import severity as weather_severity_fn


def _weather_with_severity(weather: pd.DataFrame) -> pd.DataFrame:
    w = weather.copy()
    w["ts_hour"] = pd.to_datetime(w["ts_hour"], errors="coerce", utc=True)
    waves = w["wave_height"] if "wave_height" in w.columns else [0.0] * len(w)
    w["severity"] = [
        weather_severity_fn(ws, wg, pr, wv)
        for ws, wg, pr, wv in zip(
            w["wind_speed"], w["wind_gust"], w["precipitation"], waves, strict=True
        )
    ]
    return w


def _worst_severity(weather: pd.DataFrame, zone_id: str, start, end) -> float:
    z = weather[weather["zone_id"] == zone_id]
    if z.empty:
        return 0.0
    in_window = z[(z["ts_hour"] >= start) & (z["ts_hour"] <= end)]
    pool = in_window if not in_window.empty else z
    return float(pool["severity"].max())


def build_gold(
    silver: pd.DataFrame, weather: pd.DataFrame, model: RiskModel | None = None
) -> pd.DataFrame:
    """Produce the Gold `disruption_risk` table from Silver positions + weather.

    Pass a custom `model` (from `scdi.factors.load_model`) to score with a
    different factor configuration without changing this code.
    """
    in_zone = silver[silver["port_zone"].notna()]
    if in_zone.empty:
        return pd.DataFrame(columns=GOLD_COLUMNS)

    weather = _weather_with_severity(weather)

    # Zone-level congestion signal (number of slow vessels sharing a zone) so the
    # optional `zone_congestion` factor works purely from config.
    slow_counts = (
        in_zone[in_zone["is_slow"]].groupby("port_zone")["mmsi"].nunique().to_dict()
    )

    grouped = in_zone.groupby(["mmsi", "port_zone"], as_index=False).agg(
        vessel_name=("vessel_name", "first"),
        avg_sog=("sog", "mean"),
        window_start=("ts", "min"),
        window_end=("ts", "max"),
    )

    rows: list[dict] = []
    for r in grouped.itertuples(index=False):
        sev = _worst_severity(weather, r.port_zone, r.window_start, r.window_end)
        result = evaluate(
            {
                "avg_sog": float(r.avg_sog),
                "weather_severity": sev,
                "in_zone": True,
                "zone_slow_count": float(slow_counts.get(r.port_zone, 0)),
            },
            model,
        )
        vessel_name = r.vessel_name if pd.notna(r.vessel_name) else f"MMSI {r.mmsi}"
        rows.append(
            {
                "mmsi": r.mmsi,
                "vessel_name": vessel_name,
                "port_zone": r.port_zone,
                "window_start": r.window_start,
                "window_end": r.window_end,
                "avg_sog": round(float(r.avg_sog), 2),
                "slowdown_flag": result.slowdown_flag,
                "weather_severity": round(sev, 2),
                "delay_score": result.delay_score,
                "risk_band": result.risk_band,
                "top_factor": result.top_factor,
                "reasoning": result.reasoning,
                "recommended_action": result.recommended_action,
                "factor_breakdown": json.dumps([asdict(b) for b in result.breakdown]),
                "nl_summary": build_summary(
                    vessel_name=vessel_name,
                    port_zone=r.port_zone,
                    risk_band=result.risk_band,
                    delay_score=result.delay_score,
                    reasoning=result.reasoning,
                    recommended_action=result.recommended_action,
                ),
            }
        )

    gold = pd.DataFrame(rows, columns=GOLD_COLUMNS)
    return gold.sort_values("delay_score", ascending=False).reset_index(drop=True)
