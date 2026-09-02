"""Tests for the configurable factor engine — the heart of the risk model."""

from scdi.factors import default_model, evaluate, model_from_dict

ANCHORED = {"avg_sog": 0.3, "weather_severity": 1.0, "in_zone": True, "zone_slow_count": 0}


def test_default_model_loads_three_factors():
    ids = {f.id for f in default_model().factors}
    assert ids == {"slowdown", "weather", "proximity"}


def test_breakdown_lists_active_factors_with_points():
    r = evaluate(ANCHORED)
    ids = {b.id for b in r.breakdown}
    assert {"slowdown", "weather", "proximity"} <= ids
    assert all(b.points > 0 for b in r.breakdown)
    assert "weather" in r.reasoning.lower() or "Severe marine weather" in r.reasoning


def test_breakdown_sorted_by_points_desc():
    r = evaluate(ANCHORED)
    pts = [b.points for b in r.breakdown]
    assert pts == sorted(pts, reverse=True)


def test_reweighting_changes_the_outcome():
    """Changing weights in the model data structure changes the result — no code."""
    weather_heavy = model_from_dict(
        {
            "bands": {"high": 60, "medium": 30},
            "factors": [
                {"id": "slowdown", "label": "Slowdown", "kind": "slowdown", "weight": 10,
                 "params": {"slow_sog_knots": 3.0}},
                {"id": "weather", "label": "Weather", "kind": "weather_severity", "weight": 80},
                {"id": "proximity", "label": "Proximity", "kind": "in_zone", "weight": 10},
            ],
        }
    )
    base = evaluate(ANCHORED)
    tuned = evaluate(ANCHORED, weather_heavy)
    assert tuned.delay_score != base.delay_score
    assert tuned.top_factor == "Weather"


def test_zero_weight_factor_is_disabled():
    model = model_from_dict(
        {
            "bands": {"high": 60, "medium": 30},
            "factors": [
                {"id": "weather", "label": "Weather", "kind": "weather_severity", "weight": 100},
                {"id": "slowdown", "label": "Slowdown", "kind": "slowdown", "weight": 0},
            ],
        }
    )
    ids = {f.id for f in model.factors}
    assert ids == {"weather"}


def test_congestion_factor_can_be_enabled_by_config():
    model = model_from_dict(
        {
            "bands": {"high": 60, "medium": 30},
            "factors": [
                {"id": "congestion", "label": "Congestion", "kind": "zone_congestion",
                 "weight": 100, "params": {"congestion_scale": 5}},
            ],
        }
    )
    r = evaluate({"in_zone": True, "zone_slow_count": 5}, model)
    assert r.delay_score == 100.0
    assert r.top_factor == "Congestion"
