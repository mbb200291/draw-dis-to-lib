"""Generate square grid cells covering a polygonal region (Taiwan land).

Used for finer-than-village resolution drive-time / walk-time maps. The grid
is regular in EPSG:3826 (Taiwan's metric projection), so each cell is exactly
`cell_size_m` meters on a side. Cells that don't intersect the region are
dropped; the rest are returned with both polygon geometry (WGS84) and the
centroid lat/lon for routing.
"""

from __future__ import annotations

from typing import Optional

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, box


_PROJECTED_CRS = "EPSG:3826"
_WGS84 = "EPSG:4326"


def generate_grid(
    boundary: gpd.GeoDataFrame,
    cell_size_m: float = 500.0,
    id_prefix: str = "grid",
) -> gpd.GeoDataFrame:
    """Return square grid cells (in WGS84) that intersect `boundary`.

    Parameters
    ----------
    boundary : GeoDataFrame
        Any polygons in any CRS — they're reprojected to EPSG:3826 internally.
        The union of all features defines the region the grid covers.
    cell_size_m : float
        Edge length of each square cell in meters (default 500).
    id_prefix : str
        Prefix for cell_id, e.g. "grid" → cell_ids "grid_R000_C012".

    Returns
    -------
    GeoDataFrame with columns:
        cell_id (str)         — unique id like "grid_R{row}_C{col}"
        geometry (Polygon)    — cell polygon in WGS84
        centroid_lat (float)  — cell centroid latitude (WGS84)
        centroid_lon (float)  — cell centroid longitude (WGS84)

    Cells fully outside the boundary are dropped. Cells partially inside
    are kept as full squares — the centroid may lie outside the boundary
    but is still valid for routing (OSRM snaps to nearest road).
    """
    if cell_size_m <= 0:
        raise ValueError(f"cell_size_m must be > 0, got {cell_size_m}")

    # Reproject boundary to a metric CRS so we can lay out cells in meters
    if boundary.crs is None:
        raise ValueError("boundary GeoDataFrame must have a CRS set")
    region = boundary.to_crs(_PROJECTED_CRS).geometry.union_all()
    minx, miny, maxx, maxy = region.bounds

    # Snap bounds outward to multiples of cell_size_m for clean alignment
    minx_aligned = np.floor(minx / cell_size_m) * cell_size_m
    miny_aligned = np.floor(miny / cell_size_m) * cell_size_m
    maxx_aligned = np.ceil(maxx / cell_size_m) * cell_size_m
    maxy_aligned = np.ceil(maxy / cell_size_m) * cell_size_m

    n_cols = int(round((maxx_aligned - minx_aligned) / cell_size_m))
    n_rows = int(round((maxy_aligned - miny_aligned) / cell_size_m))

    cells = []
    for r in range(n_rows):
        y0 = miny_aligned + r * cell_size_m
        y1 = y0 + cell_size_m
        for c in range(n_cols):
            x0 = minx_aligned + c * cell_size_m
            x1 = x0 + cell_size_m
            cell = box(x0, y0, x1, y1)
            if not region.intersects(cell):
                continue
            cells.append({
                "cell_id": f"{id_prefix}_R{r:03d}_C{c:03d}",
                "geometry": cell,
                # store the projected centroid; we convert below
                "_x": (x0 + x1) / 2,
                "_y": (y0 + y1) / 2,
            })

    gdf = gpd.GeoDataFrame(cells, crs=_PROJECTED_CRS)
    # Reproject geometry back to WGS84
    gdf = gdf.to_crs(_WGS84)
    # Convert centroid x/y to WGS84 lat/lon
    import pyproj
    transformer = pyproj.Transformer.from_crs(_PROJECTED_CRS, _WGS84, always_xy=True)
    lon, lat = transformer.transform(gdf["_x"].to_numpy(), gdf["_y"].to_numpy())
    gdf["centroid_lat"] = lat
    gdf["centroid_lon"] = lon
    gdf = gdf.drop(columns=["_x", "_y"])

    return gdf[["cell_id", "centroid_lat", "centroid_lon", "geometry"]]
