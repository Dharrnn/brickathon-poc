from scdi.zones import PortZone, assign_zone, haversine_km

ZONES = [
    PortZone("la_long_beach", "Los Angeles / Long Beach", 33.74, -118.22, 40.0),
    PortZone("oakland", "Oakland / SF Bay", 37.80, -122.33, 30.0),
]


def test_haversine_known_distance():
    # LA to Oakland is ~540 km great-circle.
    d = haversine_km(33.74, -118.22, 37.80, -122.33)
    assert 500 < d < 600


def test_assign_zone_inside():
    assert assign_zone(33.72, -118.25, ZONES) == "la_long_beach"


def test_assign_zone_open_water_is_none():
    assert assign_zone(25.0, -140.0, ZONES) is None


def test_assign_zone_picks_nearest_when_overlapping():
    near_oakland = assign_zone(37.81, -122.32, ZONES)
    assert near_oakland == "oakland"
