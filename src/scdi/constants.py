"""Data-cleaning and weather-severity constants.

The disruption-risk model (factor weights, thresholds, bands, actions) is NOT
here — it is configurable data in `factors.yml` / `scdi.factors`. This module
holds only the AIS validity ranges used for cleaning and the weather-severity
sub-model used to turn raw wind/gust/precip/wave into a [0,1] factor input.
"""

from __future__ import annotations

# --- Slowdown flag (Silver labelling) --------------------------------------
# Also the default `slow_sog_knots` for the slowdown factor in factors.yml;
# keep the two in agreement.
SLOW_SOG_KNOTS: float = 3.0

# --- Weather severity buckets (wind in knots) ------------------------------
# Beaufort-ish bands. Values are the severity contribution in [0, 1].
WIND_SEVERITY_BANDS: list[tuple[float, float]] = [
    (34.0, 1.00),  # gale and above
    (22.0, 0.60),  # strong / near gale
    (11.0, 0.30),  # moderate breeze
    (0.0, 0.05),   # calm-ish
]
GUST_SEVERITY_KNOTS: float = 40.0
PRECIP_SEVERITY_MM: float = 4.0
PRECIP_SEVERITY_BONUS: float = 0.15
# Significant wave height (metres) that meaningfully adds marine disruption.
WAVE_SEVERITY_M: float = 4.0
WAVE_SEVERITY_BONUS: float = 0.20

# --- Data validity ---------------------------------------------------------
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0
# MMSI is a 9-digit maritime identity.
MMSI_MIN, MMSI_MAX = 100_000_000, 999_999_999
