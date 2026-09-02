"""Pre-fetch Open-Meteo weather for each port zone into a normalized CSV.

Run this on a dev machine BEFORE the event, then upload the output to the
Databricks Unity Catalog Volume. Databricks Free Edition restricts outbound
internet to trusted domains, so the pipeline itself never calls Open-Meteo —
weather is pre-staged (ADR-003).

    uv run python scripts/fetch_weather.py --days 3 --out data/raw/weather.csv

Uses the Open-Meteo forecast API for wind + precipitation, and the marine API
for wave height. No API key required. https://open-meteo.com/en/docs
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import requests

from scdi.zones import load_zones

ROOT = Path(__file__).resolve().parents[1]
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
MARINE_API = "https://marine-api.open-meteo.com/v1/marine"


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_zone(lat: float, lon: float, days: int) -> list[dict]:
    """Return per-hour rows merging wind/precip (forecast) with wave (marine)."""
    forecast = _get(
        FORECAST_API,
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wind_speed_10m,wind_gusts_10m,precipitation",
            "wind_speed_unit": "kn",  # knots, matching the scoring thresholds
            "forecast_days": days,
        },
    ).get("hourly", {})

    waves_by_time: dict[str, float] = {}
    try:
        marine = _get(
            MARINE_API,
            {"latitude": lat, "longitude": lon, "hourly": "wave_height", "forecast_days": days},
        ).get("hourly", {})
        waves_by_time = dict(zip(marine.get("time", []), marine.get("wave_height", []), strict=False))
    except requests.RequestException:
        pass  # marine API not available for this point — wave defaults to 0

    times = forecast.get("time", [])
    winds = forecast.get("wind_speed_10m", [])
    gusts = forecast.get("wind_gusts_10m", [])
    precip = forecast.get("precipitation", [])
    return [
        {
            "ts_hour": t,
            "wind_speed": winds[i],
            "wind_gust": gusts[i],
            "precipitation": precip[i],
            "wave_height": waves_by_time.get(t, 0.0) or 0.0,
        }
        for i, t in enumerate(times)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--out", default=str(ROOT / "data" / "raw" / "weather.csv"))
    args = parser.parse_args()

    zones = load_zones(ROOT / "data" / "ports.json")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["zone_id", "ts_hour", "wind_speed", "wind_gust", "precipitation", "wave_height"])
        for z in zones:
            for row in fetch_zone(z.center_lat, z.center_lon, args.days):
                writer.writerow(
                    [z.zone_id, row["ts_hour"], row["wind_speed"], row["wind_gust"],
                     row["precipitation"], row["wave_height"]]
                )
            print(f"fetched {z.zone_id}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
