"""Tests for lib.grid — grid cell generation."""

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from lib.grid import generate_grid


def _square_boundary(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """A small square test region for predictable cell-count math."""
    # In WGS84 a degree of lon at lat 23 is ~102 km. Use a tiny region.
    poly = Polygon([(120.0, 23.0), (120.01, 23.0), (120.01, 23.01), (120.0, 23.01)])
    return gpd.GeoDataFrame({"id": [1]}, geometry=[poly], crs=crs)


def test_generate_grid_returns_expected_columns():
    boundary = _square_boundary()
    gdf = generate_grid(boundary, cell_size_m=500)
    assert set(gdf.columns) == {"cell_id", "centroid_lat", "centroid_lon", "geometry"}
    assert gdf.crs.to_epsg() == 4326


def test_generate_grid_cell_ids_unique():
    boundary = _square_boundary()
    gdf = generate_grid(boundary, cell_size_m=500)
    assert gdf["cell_id"].is_unique


def test_generate_grid_only_cells_intersecting_boundary():
    """A small ~1 km × 1 km region should yield only a handful of 500m cells."""
    boundary = _square_boundary()
    gdf = generate_grid(boundary, cell_size_m=500)
    # 0.01 degree ≈ 1.1 km. Expect roughly 4–9 cells (depending on alignment)
    assert 1 <= len(gdf) <= 16


def test_generate_grid_centroids_inside_bounds():
    boundary = _square_boundary()
    gdf = generate_grid(boundary, cell_size_m=500)
    # All centroids should be in the vicinity of the boundary
    assert (gdf["centroid_lat"].between(22.99, 23.02)).all()
    assert (gdf["centroid_lon"].between(119.99, 120.02)).all()


def test_generate_grid_smaller_cell_yields_more():
    boundary = _square_boundary()
    a = generate_grid(boundary, cell_size_m=500)
    b = generate_grid(boundary, cell_size_m=200)
    assert len(b) > len(a)


def test_generate_grid_rejects_zero_cell_size():
    with pytest.raises(ValueError):
        generate_grid(_square_boundary(), cell_size_m=0)


def test_generate_grid_requires_crs():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly])  # no crs
    with pytest.raises(ValueError):
        generate_grid(gdf, cell_size_m=500)


def test_generate_grid_donut_drops_cells_outside_ring():
    """For an L-shape region, cells in the missing corner should be dropped."""
    # L-shape: bottom-left 1km square removed from a 2km square
    big = Polygon([(120.0, 23.0), (120.02, 23.0), (120.02, 23.02), (120.0, 23.02)])
    hole = Polygon([(120.0, 23.0), (120.01, 23.0), (120.01, 23.01), (120.0, 23.01)])
    l_shape = big.difference(hole)
    boundary = gpd.GeoDataFrame({"id": [1]}, geometry=[l_shape], crs="EPSG:4326")
    full = generate_grid(big and gpd.GeoDataFrame({"id":[1]},geometry=[big],crs="EPSG:4326"), cell_size_m=500)
    lshape = generate_grid(boundary, cell_size_m=500)
    # L-shape has 3/4 the area → expect ~3/4 the cells
    assert len(lshape) < len(full)
