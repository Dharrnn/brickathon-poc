"""Port-zone reference data and point-in-zone assignment.

A zone is a labelled circle (centre + radius). `assign_zone` returns the id of
the first zone whose centre is within its radius of the point, or None. Pure and
framework-free so it is identical in local pandas and in a Databricks UDF.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

_EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class PortZone:
    zone_id: str
    name: str
    center_lat: float
    center_lon: float
    radius_km: float


def load_zones(path: str | Path) -> list[PortZone]:
    """Load port zones from a ports.json file (list of zone objects)."""
    raw = json.loads(Path(path).read_text())
    return [PortZone(**z) for z in raw]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def assign_zone(lat: float, lon: float, zones: list[PortZone]) -> str | None:
    """Return the id of the nearest zone containing the point, else None."""
    best: tuple[float, str] | None = None
    for z in zones:
        d = haversine_km(lat, lon, z.center_lat, z.center_lon)
        if d <= z.radius_km and (best is None or d < best[0]):
            best = (d, z.zone_id)
    return best[1] if best else None
