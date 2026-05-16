import math

from lib.geo import haversine_km


def test_haversine_zero_distance():
    assert haversine_km(25.0, 121.5, 25.0, 121.5) == 0.0


def test_haversine_known_distance_taipei_to_kaohsiung():
    # 台北車站 (25.0478, 121.5170) 到高雄車站 (22.6396, 120.3022)
    # 大圓距離約 295 km，容許 ±5 km 誤差
    d = haversine_km(25.0478, 121.5170, 22.6396, 120.3022)
    assert 290 < d < 300


def test_haversine_symmetric():
    a = haversine_km(24.0, 120.0, 23.0, 120.5)
    b = haversine_km(23.0, 120.5, 24.0, 120.0)
    assert math.isclose(a, b, rel_tol=1e-9)


def test_haversine_one_degree_lat():
    # 1 度緯度 ≈ 111 km
    d = haversine_km(23.0, 120.0, 24.0, 120.0)
    assert 110 < d < 112


import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

from lib.geo import drive_minutes_from_km, safe_centroid_latlon


def test_drive_minutes_30kmh():
    # 30 km @ 30 km/h = 60 分鐘
    assert drive_minutes_from_km(30.0, speed_kmh=30.0) == 60.0


def test_drive_minutes_zero_distance():
    assert drive_minutes_from_km(0.0, speed_kmh=30.0) == 0.0


def test_drive_minutes_default_speed_is_30():
    assert drive_minutes_from_km(15.0) == 30.0


def test_safe_centroid_returns_point_inside_polygon():
    # 簡單正方形：質心應在裡面
    sq = Polygon([(120.0, 23.0), (120.1, 23.0), (120.1, 23.1), (120.0, 23.1)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[sq], crs="EPSG:4326")
    lat, lon = safe_centroid_latlon(gdf.iloc[0].geometry, source_crs="EPSG:4326")
    assert 23.0 < lat < 23.1
    assert 120.0 < lon < 120.1


def test_safe_centroid_falls_back_for_donut_when_centroid_outside():
    # C 形多邊形（質心會落在缺口外）— representative_point 應落在實際範圍內
    c_shape = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10), (0, 9), (9, 9), (9, 1), (0, 1)]
    )
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[c_shape], crs="EPSG:3826")
    lat, lon = safe_centroid_latlon(c_shape, source_crs="EPSG:3826")
    # representative_point 保證落在 polygon 內
    from shapely.geometry import Point
    import pyproj
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    x, y = transformer.transform(lon, lat)
    assert c_shape.contains(Point(x, y))
