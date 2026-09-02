import pandas as pd

from scdi.clean import split, to_silver
from scdi.zones import PortZone

ZONES = [PortZone("la_long_beach", "Los Angeles / Long Beach", 33.74, -118.22, 40.0)]


def _raw(rows):
    return pd.DataFrame(rows)


def test_valid_row_becomes_silver_with_zone_and_slow_flag():
    raw = _raw(
        [{"MMSI": 636019825, "BaseDateTime": "2024-01-15T02:00:00",
          "LAT": 33.72, "LON": -118.25, "SOG": 0.2, "VesselName": "PACIFIC VOYAGER"}]
    )
    silver = to_silver(raw, ZONES)
    assert len(silver) == 1
    assert silver.iloc[0]["port_zone"] == "la_long_beach"
    assert bool(silver.iloc[0]["is_slow"]) is True


def test_bad_mmsi_is_quarantined_not_dropped():
    raw = _raw(
        [{"MMSI": 999, "BaseDateTime": "2024-01-15T04:00:00",
          "LAT": 33.70, "LON": -118.20, "SOG": 5.0, "VesselName": "BAD"}]
    )
    silver, quarantine = split(raw, ZONES)
    assert len(silver) == 0
    assert len(quarantine) == 1
    assert quarantine.iloc[0]["quarantine_reason"] == "invalid_mmsi"


def test_out_of_range_lat_is_quarantined():
    raw = _raw(
        [{"MMSI": 566123000, "BaseDateTime": "2024-01-15T10:00:00",
          "LAT": 999.0, "LON": -122.30, "SOG": 3.0, "VesselName": "X"}]
    )
    _, quarantine = split(raw, ZONES)
    assert quarantine.iloc[0]["quarantine_reason"] == "invalid_lat"


def test_duplicate_positions_deduped():
    row = {"MMSI": 636019825, "BaseDateTime": "2024-01-15T02:00:00",
           "LAT": 33.72, "LON": -118.25, "SOG": 0.2, "VesselName": "PV"}
    silver = to_silver(_raw([row, dict(row)]), ZONES)
    assert len(silver) == 1


def test_moving_vessel_in_zone_not_slow():
    raw = _raw(
        [{"MMSI": 477553000, "BaseDateTime": "2024-01-15T03:00:00",
          "LAT": 33.75, "LON": -118.20, "SOG": 12.4, "VesselName": "EASTERN STAR"}]
    )
    silver = to_silver(raw, ZONES)
    assert bool(silver.iloc[0]["is_slow"]) is False
