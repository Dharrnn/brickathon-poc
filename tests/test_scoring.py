from scdi.scoring import score


def test_open_water_scores_zero():
    r = score(avg_sog=15.0, weather_severity=0.9, in_zone=False)
    assert r.delay_score == 0.0
    assert r.risk_band == "low"
    assert r.slowdown_flag is False


def test_anchored_in_severe_weather_is_high():
    r = score(avg_sog=0.3, weather_severity=1.0, in_zone=True)
    # slowdown ~36 + weather 40 + proximity 20 -> ~96
    assert r.delay_score > 90
    assert r.risk_band == "high"
    assert r.slowdown_flag is True
    assert "reroute" in r.recommended_action.lower() or "anchorage" in r.recommended_action.lower()


def test_moving_vessel_calm_weather_in_zone_is_low_or_medium():
    r = score(avg_sog=12.0, weather_severity=0.05, in_zone=True)
    assert r.slowdown_flag is False
    assert r.risk_band in {"low", "medium"}


def test_score_never_exceeds_100():
    r = score(avg_sog=0.0, weather_severity=1.0, in_zone=True)
    assert r.delay_score <= 100.0


def test_result_carries_reasoning_and_breakdown():
    r = score(avg_sog=0.3, weather_severity=1.0, in_zone=True)
    assert r.reasoning
    assert r.top_factor
    assert len(r.breakdown) >= 1
