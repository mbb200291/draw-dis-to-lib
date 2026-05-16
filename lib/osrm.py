"""OSRM HTTP client with retry and a resumable progress-file helper."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Dict, Optional

import requests


class OSRMError(RuntimeError):
    """Raised when OSRM returns a non-Ok response after retries."""


PROGRESS_FIELDS = [
    "village_id",
    "nearest_library",
    "library_lat",
    "library_lon",
    "distance_km",
    "drive_minutes",
    "method",
]


class OSRMClient:
    """Minimal OSRM /route client for driving duration queries."""

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

    def route_duration_minutes(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Query OSRM for driving duration; return minutes."""
        # OSRM uses lon,lat ordering
        coords = f"{lon1},{lat1};{lon2},{lat2}"
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
                duration_s = data["routes"][0]["duration"]
                time.sleep(self.request_delay_s)
                return duration_s / 60.0
            except (requests.RequestException, OSRMError) as exc:
                last_err = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_s * (attempt + 1))

        raise OSRMError(f"OSRM failed after {self.max_retries} attempts: {last_err}")


def load_progress(progress_file: Path) -> Dict[str, dict]:
    """Read existing progress rows keyed by village_id. Returns {} if file missing."""
    progress_file = Path(progress_file)
    if not progress_file.exists():
        return {}
    out: Dict[str, dict] = {}
    with progress_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # cast numeric fields
            row["library_lat"] = float(row["library_lat"])
            row["library_lon"] = float(row["library_lon"])
            row["distance_km"] = float(row["distance_km"])
            row["drive_minutes"] = float(row["drive_minutes"])
            out[row["village_id"]] = row
    return out


def save_progress_row(
    progress_file: Path,
    *,
    village_id: str,
    nearest_library: str,
    library_lat: float,
    library_lon: float,
    distance_km: float,
    drive_minutes: float,
    method: str,
) -> None:
    """Append one result row to the progress CSV (creates with header if missing)."""
    progress_file = Path(progress_file)
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    new_file = not progress_file.exists()
    with progress_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PROGRESS_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(
            {
                "village_id": village_id,
                "nearest_library": nearest_library,
                "library_lat": library_lat,
                "library_lon": library_lon,
                "distance_km": distance_km,
                "drive_minutes": drive_minutes,
                "method": method,
            }
        )
