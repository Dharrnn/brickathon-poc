"""Generate a richer, deterministic synthetic demo dataset.

Produces ~30 vessels spread across all five port zones with a realistic mix of
anchored / slow / moving behaviour, per-port weather profiles, a few open-water
vessels (excluded by the pipeline), and a couple of malformed rows (to exercise
quarantine). Seeded, so it is reproducible. This is SEPARATE from the tiny
data/sample/ fixture the tests pin against.

    uv run python scripts/make_demo_data.py
    # -> data/demo/ais.csv, data/demo/weather.csv

Upload data/demo/ais.csv to the Volume's ais/ folder and data/demo/weather.csv
as weather/weather.csv for a fuller dashboard.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from scdi.zones import load_zones

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo"
SEED = 42
DAY = datetime(2024, 1, 15)  # noqa: DTZ001 - naive is fine; used only for string formatting

# Per-zone weather profile: (wind, gust, precip, wave) center values.
WEATHER = {
    "la_long_beach": (37, 46, 5.5, 4.6),   # severe
    "oakland": (8, 12, 0.0, 0.8),          # calm
    "seattle_tacoma": (24, 30, 2.0, 2.0),  # moderate
    "ny_nj": (30, 37, 3.0, 2.6),           # moderate-high
    "houston": (12, 17, 0.5, 1.0),         # mild
}

NAME_POOL = [
    "PACIFIC", "EASTERN", "GOLDEN", "NORTHERN", "SOUTHERN", "ATLANTIC", "CORAL",
    "IRON", "SILVER", "EVER", "OCEAN", "POLAR", "STAR", "HORIZON", "VOYAGER",
    "TRADER", "PIONEER", "GUARDIAN", "MARINER", "CLIPPER",
]


def _jitter(rng: random.Random, center: float, spread: float) -> float:
    return round(center + rng.uniform(-spread, spread), 4)


def main() -> None:
    rng = random.Random(SEED)
    zones = {z.zone_id: z for z in load_zones(ROOT / "data" / "ports.json")}
    OUT.mkdir(parents=True, exist_ok=True)

    ais_rows: list[list] = []
    mmsi = 366000001

    for zone_id, z in zones.items():
        n_vessels = rng.randint(5, 8)
        for _ in range(n_vessels):
            mmsi += rng.randint(1, 40)
            name = f"{rng.choice(NAME_POOL)} {rng.choice(NAME_POOL)}"
            # Behaviour mix: ~40% anchored/slow, ~60% moving.
            if rng.random() < 0.45:
                base_sog = rng.uniform(0.0, 2.8)   # slow / anchored
            else:
                base_sog = rng.uniform(6.0, 15.0)  # moving
            # 3-5 pings spread across the morning, inside the zone radius.
            deg = z.radius_km / 111.0 * 0.6
            for h in range(rng.randint(3, 5)):
                ts = DAY + timedelta(hours=2 + h * 2, minutes=rng.randint(0, 59))
                ais_rows.append([
                    mmsi,
                    ts.strftime("%Y-%m-%dT%H:%M:%S"),
                    _jitter(rng, z.center_lat, deg),
                    _jitter(rng, z.center_lon, deg),
                    round(max(0.0, base_sog + rng.uniform(-0.4, 0.4)), 1),
                    round(rng.uniform(0, 359), 1),
                    rng.randint(0, 359),
                    name,
                    70,
                ])

    # A few open-water vessels (no zone -> excluded by the pipeline).
    for _ in range(3):
        mmsi += rng.randint(1, 40)
        ts = DAY + timedelta(hours=rng.randint(1, 10))
        ais_rows.append([mmsi, ts.strftime("%Y-%m-%dT%H:%M:%S"),
                         _jitter(rng, 25.0, 3.0), _jitter(rng, -140.0, 3.0),
                         round(rng.uniform(10, 18), 1), 300.0, 301, "OPEN SEA DRIFTER", 70])

    # Two malformed rows -> quarantine (bad MMSI, out-of-range lat).
    ais_rows.append([999, "2024-01-15T04:00:00", 33.70, -118.20, 5.0, 100.0, 101, "BAD MMSI", 70])
    ais_rows.append([366123999, "2024-01-15T05:00:00", 999.0, -122.30, 3.0, 10.0, 11, "BAD LAT", 70])

    with (OUT / "ais.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "Heading",
                    "VesselName", "VesselType"])
        w.writerows(ais_rows)

    # Weather: hourly-ish per zone across the vessel window, with small jitter.
    with (OUT / "weather.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zone_id", "ts_hour", "wind_speed", "wind_gust", "precipitation", "wave_height"])
        for zone_id, (wind, gust, precip, wave) in WEATHER.items():
            for h in range(2, 13, 2):
                ts = (DAY + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00")
                w.writerow([
                    zone_id, ts,
                    round(wind + rng.uniform(-2, 2), 1),
                    round(gust + rng.uniform(-2, 2), 1),
                    round(max(0.0, precip + rng.uniform(-0.5, 0.5)), 1),
                    round(max(0.0, wave + rng.uniform(-0.4, 0.4)), 1),
                ])

    print(f"wrote {len(ais_rows)} AIS rows -> {OUT / 'ais.csv'}")
    print(f"wrote weather -> {OUT / 'weather.csv'}")


if __name__ == "__main__":
    main()
