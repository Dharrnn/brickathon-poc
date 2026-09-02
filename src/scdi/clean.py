"""Bronze -> Silver cleaning with quarantine (pandas).

Validates AIS rows at the boundary (ArcAI "validate at system boundaries"):
rows with out-of-range lat/lon, a non-9-digit MMSI, or an unparseable timestamp
are not silently dropped — they are routed to a quarantine frame with a reason,
so data quality is observable (Tier 0 requirement). Valid rows are de-duplicated
on (mmsi, ts) and enriched with port zone + slowdown flag. Returns new frames;
never mutates the input.
"""

from __future__ import annotations

import pandas as pd

from scdi.constants import (
    LAT_MAX,
    LAT_MIN,
    LON_MAX,
    LON_MIN,
    MMSI_MAX,
    MMSI_MIN,
    SLOW_SOG_KNOTS,
)
from scdi.schema import AIS_FIELD_MAP, SILVER_COLUMNS
from scdi.zones import PortZone, assign_zone


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    present = {src: dst for src, dst in AIS_FIELD_MAP.items() if src in raw.columns}
    df = raw.rename(columns=present).copy()
    if "vessel_name" not in df.columns:
        df["vessel_name"] = None
    df["mmsi"] = pd.to_numeric(df["mmsi"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["sog"] = pd.to_numeric(df["sog"], errors="coerce")
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    return df


def _reason(row: pd.Series) -> str | None:
    if pd.isna(row["mmsi"]) or not (MMSI_MIN <= row["mmsi"] <= MMSI_MAX):
        return "invalid_mmsi"
    if pd.isna(row["lat"]) or not (LAT_MIN <= row["lat"] <= LAT_MAX):
        return "invalid_lat"
    if pd.isna(row["lon"]) or not (LON_MIN <= row["lon"] <= LON_MAX):
        return "invalid_lon"
    if pd.isna(row["sog"]):
        return "missing_sog"
    if pd.isna(row["ts"]):
        return "invalid_timestamp"
    return None


def split(raw: pd.DataFrame, zones: list[PortZone]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (silver, quarantine). Silver is clean + enriched; quarantine keeps
    the offending prepared rows plus a `quarantine_reason` column."""
    df = _prepare(raw)
    reasons = df.apply(_reason, axis=1) if not df.empty else pd.Series([], dtype="object")

    quarantine = df.loc[reasons.notna()].copy()
    quarantine["quarantine_reason"] = reasons[reasons.notna()]

    good = df.loc[reasons.isna()].copy()
    if good.empty:
        return pd.DataFrame(columns=SILVER_COLUMNS), quarantine

    good["mmsi"] = good["mmsi"].astype("int64")
    good = good.drop_duplicates(subset=["mmsi", "ts"]).reset_index(drop=True)
    good["port_zone"] = [
        assign_zone(lat, lon, zones) for lat, lon in zip(good["lat"], good["lon"], strict=True)
    ]
    good["is_slow"] = good["port_zone"].notna() & (good["sog"] < SLOW_SOG_KNOTS)
    return good[SILVER_COLUMNS], quarantine


def to_silver(raw: pd.DataFrame, zones: list[PortZone]) -> pd.DataFrame:
    """Convenience: just the clean Silver frame (drops the quarantine side)."""
    silver, _ = split(raw, zones)
    return silver
