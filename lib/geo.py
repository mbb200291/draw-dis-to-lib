"""Geographic utilities: distance and centroid helpers."""

from __future__ import annotations

import math
from typing import Tuple

import pyproj
from shapely.geometry.base import BaseGeometry

EARTH_RADIUS_KM = 6371.0088

# 台南位於 EPSG:3826（TWD97 / TM2 zone 121）— 平面座標下做幾何計算才準
_PROJECTED_CRS = "EPSG:3826"
_WGS84 = "EPSG:4326"

_TO_PROJ = pyproj.Transformer.from_crs(_WGS84, _PROJECTED_CRS, always_xy=True)
_TO_WGS84 = pyproj.Transformer.from_crs(_PROJECTED_CRS, _WGS84, always_xy=True)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_KM * c


def drive_minutes_from_km(distance_km: float, speed_kmh: float = 30.0) -> float:
    """Convert straight-line km into estimated drive minutes at the given speed."""
    if speed_kmh <= 0:
        raise ValueError("speed_kmh must be positive")
    return distance_km / speed_kmh * 60.0


def safe_centroid_latlon(
    geom: BaseGeometry,
    source_crs: str = _WGS84,
) -> Tuple[float, float]:
    """Return (lat, lon) for the centroid of geom; fall back to representative_point
    if the centroid lies outside the geometry (e.g. crescent/C-shaped 里界).

    Geometry is projected to EPSG:3826 (a metric CRS for Taiwan) before computing
    the centroid so that the result is geometrically meaningful, then projected
    back to WGS84.
    """
    if source_crs == _WGS84:
        proj_geom = _project_geom(geom, _TO_PROJ)
    elif source_crs == _PROJECTED_CRS:
        proj_geom = geom
    else:
        # 不支援的 CRS：呼叫端應該先 to_crs 過
        raise ValueError(f"Unsupported source_crs={source_crs}; reproject upstream")

    c = proj_geom.centroid
    if not proj_geom.contains(c):
        c = proj_geom.representative_point()

    lon, lat = _TO_WGS84.transform(c.x, c.y)
    return lat, lon


def _project_geom(geom: BaseGeometry, transformer: pyproj.Transformer) -> BaseGeometry:
    """Apply a pyproj Transformer to every coordinate in geom (preserves type)."""
    from shapely.ops import transform as shapely_transform
    return shapely_transform(lambda x, y, z=None: transformer.transform(x, y), geom)
