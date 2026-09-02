"""Open-Meteo parsing and marine weather severity.

`parse_open_meteo` flattens one Open-Meteo `hourly` response (forecast API for
wind + precipitation, optionally the marine API for wave height) into per-hour
observations. `severity` maps wind / gust / precipitation / wave into a single
[0, 1] disruption factor that the scoring layer weights. Both are pure; the
network calls live in scripts/fetch_weather.py so the pipeline itself has no
outbound dependency (ADR-003).
"""

from __future__ import annotations

from dataclasses import dataclass

from scdi.constants import (
    GUST_SEVERITY_KNOTS,
    PRECIP_SEVERITY_BONUS,
    PRECIP_SEVERITY_MM,
    WAVE_SEVERITY_BONUS,
    WAVE_SEVERITY_M,
    WIND_SEVERITY_BANDS,
)


@dataclass(frozen=True)
class WeatherObs:
    zone_id: str
    ts_hour: str  # ISO hour, e.g. "2024-01-15T14:00"
    wind_speed: float  # knots
    wind_gust: float  # knots
    precipitation: float  # mm
    wave_height: float = 0.0  # metres (marine API; 0 when unavailable)

    @property
    def severity(self) -> float:
        return severity(self.wind_speed, self.wind_gust, self.precipitation, self.wave_height)


def severity(
    wind_speed: float, wind_gust: float, precipitation: float, wave_height: float = 0.0
) -> float:
    """Combine wind, gust, precipitation and wave height into a [0, 1] factor."""
    base = next(sev for threshold, sev in WIND_SEVERITY_BANDS if wind_speed >= threshold)
    if wind_gust >= GUST_SEVERITY_KNOTS:
        base = 1.0
    if precipitation >= PRECIP_SEVERITY_MM:
        base += PRECIP_SEVERITY_BONUS
    if wave_height >= WAVE_SEVERITY_M:
        base += WAVE_SEVERITY_BONUS
    return min(base, 1.0)


def parse_open_meteo(payload: dict, zone_id: str) -> list[WeatherObs]:
    """Flatten one Open-Meteo response into WeatherObs rows.

    Expects `hourly` with `time`, `wind_speed_10m`, `wind_gusts_10m`,
    `precipitation`, and optionally `wave_height`. Missing series default to
    zeros of the right length.
    """
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    winds = hourly.get("wind_speed_10m") or [0.0] * len(times)
    gusts = hourly.get("wind_gusts_10m") or [0.0] * len(times)
    precip = hourly.get("precipitation") or [0.0] * len(times)
    waves = hourly.get("wave_height") or [0.0] * len(times)
    return [
        WeatherObs(
            zone_id=zone_id,
            ts_hour=t,
            wind_speed=float(winds[i]),
            wind_gust=float(gusts[i]),
            precipitation=float(precip[i]),
            wave_height=float(waves[i]),
        )
        for i, t in enumerate(times)
    ]
