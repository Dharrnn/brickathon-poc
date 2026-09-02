from pathlib import Path

import pandas as pd

from scdi.clean import split
from scdi.pipeline import build_gold
from scdi.zones import load_zones

ROOT = Path(__file__).resolve().parents[1]


def _run():
    zones = load_zones(ROOT / "data" / "ports.json")
    bronze = pd.read_csv(ROOT / "data" / "sample" / "ais_sample.csv")
    weather = pd.read_csv(ROOT / "data" / "sample" / "weather_sample.csv")
    silver, _ = split(bronze, zones)
    return build_gold(silver, weather)


def test_gold_excludes_open_water_vessels():
    gold = _run()
    assert "OPEN SEA DRIFTER" not in set(gold["vessel_name"])


def test_gold_sorted_by_delay_score_desc():
    gold = _run()
    scores = list(gold["delay_score"])
    assert scores == sorted(scores, reverse=True)


def test_anchored_la_vessel_is_highest_risk():
    gold = _run()
    top = gold.iloc[0]
    assert top["vessel_name"] == "PACIFIC VOYAGER"
    assert top["risk_band"] == "high"
    assert top["port_zone"] == "la_long_beach"


def test_every_gold_row_has_a_summary():
    gold = _run()
    assert gold["nl_summary"].str.len().gt(0).all()


def test_every_gold_row_has_reasoning_and_top_factor():
    gold = _run()
    assert gold["reasoning"].str.len().gt(0).all()
    assert gold["top_factor"].notna().all()


def test_build_gold_handles_tz_naive_silver_timestamps():
    # Reproduces Databricks: Spark's toPandas() yields tz-naive silver timestamps
    # while weather ts_hour parses tz-aware. build_gold must not raise on compare.
    silver = pd.DataFrame(
        {
            "mmsi": [366000001, 366000001],
            "ts": pd.to_datetime(["2024-01-15T02:00:00", "2024-01-15T05:00:00"]),  # tz-naive
            "lat": [33.72, 33.72],
            "lon": [-118.25, -118.25],
            "sog": [0.3, 0.4],
            "vessel_name": ["ANCHORED ONE", "ANCHORED ONE"],
            "port_zone": ["la_long_beach", "la_long_beach"],
            "is_slow": [True, True],
        }
    )
    weather = pd.DataFrame(
        {
            "zone_id": ["la_long_beach"],
            "ts_hour": ["2024-01-15T03:00"],
            "wind_speed": [38.0],
            "wind_gust": [47.0],
            "precipitation": [6.0],
            "wave_height": [5.0],
        }
    )
    gold = build_gold(silver, weather)
    assert len(gold) == 1
    assert gold.iloc[0]["risk_band"] == "high"


def test_factor_breakdown_is_valid_json():
    import json

    gold = _run()
    for raw in gold["factor_breakdown"]:
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert all("points" in factor for factor in parsed)


def test_calm_oakland_vessel_is_not_high():
    gold = _run()
    golden = gold[gold["vessel_name"] == "GOLDEN HORIZON"].iloc[0]
    assert golden["risk_band"] in {"low", "medium"}
