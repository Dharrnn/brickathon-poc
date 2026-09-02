from scdi.weather import parse_open_meteo, severity


def test_severity_calm_is_low():
    assert severity(5.0, 8.0, 0.0) < 0.1


def test_severity_gale_is_max():
    assert severity(40.0, 50.0, 0.0) == 1.0


def test_severity_gust_forces_top():
    # Moderate sustained wind but a gust above the cutoff -> top severity.
    assert severity(12.0, 41.0, 0.0) == 1.0


def test_severity_precip_bonus_capped():
    s = severity(24.0, 30.0, 10.0)  # 0.60 + 0.15 bonus
    assert s == 0.75


def test_severity_wave_height_adds():
    s = severity(24.0, 30.0, 0.0, wave_height=5.0)  # 0.60 + 0.20 wave bonus
    assert s == 0.80


def test_parse_open_meteo_flattens_hourly():
    payload = {
        "hourly": {
            "time": ["2024-01-15T00:00", "2024-01-15T01:00"],
            "wind_speed_10m": [10.0, 20.0],
            "wind_gusts_10m": [15.0, 28.0],
            "precipitation": [0.0, 1.0],
        }
    }
    obs = parse_open_meteo(payload, "la_long_beach")
    assert len(obs) == 2
    assert obs[0].zone_id == "la_long_beach"
    assert obs[1].wind_speed == 20.0
    assert 0.0 <= obs[1].severity <= 1.0
