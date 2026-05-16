"""Color binning for drive-time choropleth maps."""

from __future__ import annotations

import bisect
from typing import List

# Cut points in minutes (left-closed, right-open intervals)
BINS_MINUTES: List[float] = [5.0, 10.0, 15.0, 20.0, 30.0]

# Hex colors for each bin (must be len(BINS_MINUTES) + 1):
# [0,5)  [5,10) [10,15) [15,20) [20,30) [30,inf)
COLORS_HEX: List[str] = [
    "#1a9641",
    "#a6d96a",
    "#ffffbf",
    "#fdae61",
    "#d7191c",
    "#7a0177",
]

_BIN_LABELS: List[str] = ["0–5", "5–10", "10–15", "15–20", "20–30", "30+"]


def _bin_index(minutes: float) -> int:
    if minutes < 0:
        raise ValueError(f"minutes must be >= 0, got {minutes}")
    return bisect.bisect_right(BINS_MINUTES, minutes)


def minutes_to_color(minutes: float) -> str:
    """Return hex color string for a drive-time in minutes."""
    return COLORS_HEX[_bin_index(minutes)]


def minutes_to_bin_label(minutes: float) -> str:
    """Return human-readable bin label like '5–10' or '30+'."""
    return _BIN_LABELS[_bin_index(minutes)]
