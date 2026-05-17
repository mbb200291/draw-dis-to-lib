"""OSRM HTTP client with retry and a resumable progress-file helper.

Supports any OSRM profile (driving / walking / cycling) — the choice of
which is driven by `base_url` + `profile`. The public router.project-osrm.org
demo server only carries the car profile (any `profile` value silently
returns car timings), so for walking use the FOSSGIS routed-foot endpoint:
    base_url="https://routing.openstreetmap.de/routed-foot"
    profile="walking"
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import requests


class OSRMError(RuntimeError):
    """Raised when OSRM returns a non-Ok response after retries."""


# Default progress fields. Callers with extra columns can pass a custom
# `fields` sequence to save_progress_row / load_progress.
PROGRESS_FIELDS: Sequence[str] = (
    "village_id",
    "nearest_library",
    "library_lat",
    "library_lon",
    "distance_km",
    "time_min",
    "method",
)

# Columns that should be cast to float when loading
_FLOAT_FIELDS = {"library_lat", "library_lon", "distance_km", "time_min", "drive_minutes"}


class OSRMClient:
    """Minimal OSRM /route client.

    `base_url` + `profile` together pick the endpoint:
      https://{base_url}/route/v1/{profile}/{lon1,lat1};{lon2,lat2}

    For driving, the public OSRM demo at https://router.project-osrm.org
    works with profile="driving". For walking, use the FOSSGIS server:
      base_url="https://routing.openstreetmap.de/routed-foot",
      profile="walking"
    """

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
        profile: str = "driving",
        request_delay_s: float = 0.2,
        timeout_s: float = 15.0,
        max_retries: int = 3,
        backoff_s: float = 2.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.profile = profile
        self.request_delay_s = request_delay_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_s = backoff_s

    def route_summary(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> Tuple[float, float]:
        """Query OSRM for a route; return (duration_minutes, distance_km)."""
        coords = f"{lon1},{lat1};{lon2},{lat2}"  # OSRM uses lon,lat
        url = f"{self.base_url}/route/v1/{self.profile}/{coords}"

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, timeout=self.timeout_s)
                if resp.status_code >= 500:
                    raise OSRMError(f"server {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    raise OSRMError(f"OSRM returned code={data.get('code')}")
                route = data["routes"][0]
                time.sleep(self.request_delay_s)
                return route["duration"] / 60.0, route["distance"] / 1000.0
            except (requests.RequestException, OSRMError) as exc:
                last_err = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_s * (attempt + 1))

        raise OSRMError(f"OSRM failed after {self.max_retries} attempts: {last_err}")

    def route_duration_minutes(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Backward-compat wrapper: return only duration."""
        return self.route_summary(lat1, lon1, lat2, lon2)[0]


def load_progress(progress_file: Path) -> Dict[str, dict]:
    """Read existing progress rows keyed by village_id. Returns {} if file missing.

    Columns are auto-detected from the CSV header; float-like fields (lat/lon,
    distance_km, time_min, drive_minutes) are cast back from string.
    """
    progress_file = Path(progress_file)
    if not progress_file.exists():
        return {}
    out: Dict[str, dict] = {}
    with progress_file.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for k in row:
                if k in _FLOAT_FIELDS and row[k] not in ("", None):
                    row[k] = float(row[k])
            out[row["village_id"]] = row
    return out


def save_progress_row(
    progress_file: Path,
    fields: Sequence[str] = PROGRESS_FIELDS,
    **row,
) -> None:
    """Append one result row to the progress CSV (creates with header if missing).

    `fields` controls the CSV column order and which keyword args are written.
    Unknown kwargs (not in fields) are silently dropped — caller's responsibility
    to pass the right ones.
    """
    progress_file = Path(progress_file)
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    new_file = not progress_file.exists()
    with progress_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})
