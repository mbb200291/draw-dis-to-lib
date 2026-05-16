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
