
import math
import random
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class Coordinates:
    lat: float
    lon: float


def haversine_km(a: Coordinates, b: Coordinates) -> float:
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    sin_dlat = math.sin(dlat / 2.0)
    sin_dlon = math.sin(dlon / 2.0)
    h = sin_dlat**2 + math.cos(lat1) * math.cos(lat2) * sin_dlon**2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def within_radius(center: Coordinates, candidate: Coordinates, radius_km: float) -> bool:
    return haversine_km(center, candidate) <= radius_km


def fuzz_location(coord: Coordinates, max_meters: int, seed: int | None = None) -> Coordinates:
    if max_meters <= 0:
        return coord
    rng = random.Random(seed)
    # Convert meters to degrees approximately
    max_km = max_meters / 1000.0
    delta_lat = (rng.random() * 2 - 1) * (max_km / 110.574)
    delta_lon = (rng.random() * 2 - 1) * (max_km / (111.320 * math.cos(math.radians(coord.lat)) or 1))
    return Coordinates(lat=coord.lat + delta_lat, lon=coord.lon + delta_lon)
