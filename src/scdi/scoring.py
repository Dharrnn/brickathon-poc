"""Thin scalar entry point over the configurable factor engine.

The real model lives in `scdi.factors` (declared in `factors.yml`). This wrapper
just builds the inputs dict for one vessel/window and delegates, so callers that
have plain scalars (tests, ad-hoc checks) don't need to assemble a dict.
"""

from __future__ import annotations

from scdi.factors import RiskModel, RiskResult, evaluate


def score(
    avg_sog: float,
    weather_severity: float,
    in_zone: bool,
    zone_slow_count: float = 0.0,
    model: RiskModel | None = None,
) -> RiskResult:
    return evaluate(
        {
            "avg_sog": avg_sog,
            "weather_severity": weather_severity,
            "in_zone": in_zone,
            "zone_slow_count": zone_slow_count,
        },
        model,
    )
