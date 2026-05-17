"""Color binning for drive-time / walk-time / distance choropleth maps.

Three named scales, all using the same 6-step green→yellow→red palette
(intervals are left-closed, right-open):

- DRIVING: 0/5/10/15/20/30+ min   — for road driving time
- WALKING: 0/15/30/60/90/120+ min — for walking time (4.5 km/h)
- DISTANCE: 0/2/5/10/15/20+ km    — for road distance regardless of mode

Use `Scale(...).color(value)` or call the module-level helpers
`minutes_to_color(...)` (driving, default) for backward compatibility.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import List


# Shared 6-step green→yellow→red palette
PALETTE_HEX: List[str] = [
    "#1a9641",  # deepest green
    "#a6d96a",  # light green
    "#ffffbf",  # yellow
    "#fdae61",  # orange
    "#d7191c",  # red
    "#7a0177",  # dark purple-red
]


@dataclass(frozen=True)
class Scale:
    """A binned color scale: cuts + colors + per-bin labels."""

    name: str
    cuts: List[float]    # n cut points → n+1 bins
    colors: List[str]
    labels: List[str]
    unit: str = ""

    def _index(self, value: float) -> int:
        if value < 0:
            raise ValueError(f"value must be >= 0, got {value}")
        return bisect.bisect_right(self.cuts, value)

    def color(self, value: float) -> str:
        return self.colors[self._index(value)]

    def label(self, value: float) -> str:
        return self.labels[self._index(value)]


DRIVING = Scale(
    name="driving_minutes",
    cuts=[5.0, 10.0, 15.0, 20.0, 30.0],
    colors=PALETTE_HEX,
    labels=["0–5", "5–10", "10–15", "15–20", "20–30", "30+"],
    unit="分鐘",
)

WALKING = Scale(
    name="walking_minutes",
    cuts=[15.0, 30.0, 60.0, 90.0, 120.0],
    colors=PALETTE_HEX,
    labels=["0–15", "15–30", "30–60", "60–90", "90–120", "120+"],
    unit="分鐘",
)

DISTANCE = Scale(
    name="distance_km",
    cuts=[2.0, 5.0, 10.0, 15.0, 20.0],
    colors=PALETTE_HEX,
    labels=["0–2", "2–5", "5–10", "10–15", "15–20", "20+"],
    unit="km",
)


# === Backward-compat module-level API (driving time) ===

BINS_MINUTES: List[float] = DRIVING.cuts
COLORS_HEX: List[str] = DRIVING.colors


def minutes_to_color(minutes: float) -> str:
    """Driving-time color (backward-compat). Use DRIVING.color() for new code."""
    return DRIVING.color(minutes)


def minutes_to_bin_label(minutes: float) -> str:
    """Driving-time bin label (backward-compat)."""
    return DRIVING.label(minutes)
