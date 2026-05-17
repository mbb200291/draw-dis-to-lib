"""TGOS (Taiwan Geospatial One Stop) address geocoder with on-disk cache.

Uses the public TGOS MAP API Lite credentials (no registration needed).
See: https://api.tgos.tw/TGOS_MAP_API/docs/site/web/LiteIntro

The TGOS server's TLS certificate is malformed (missing Subject Key Identifier),
so requests must use verify=False. The data is public reference data; no
sensitive payload is transmitted.
"""

from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import requests
import urllib3

# Suppress the "InsecureRequestWarning" caused by verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Public "Lite" credentials baked into the TGOS Lite SDK. The SDK at
# http://api.tgos.tw/TGOS_API/tgos?ver=2&AppID=<lite>&APIKey=<lite>
# returns JS containing tgHash. This value can be re-extracted with
# `grep -oE 'tgHash="[^"]+"' tgos.js` if TGOS rotates it.
TGOS_LITE_TGHASH = "HMXbG+Txt1Yv0uLnErJLKpooOVqL64RrBhS27tGeUCw="

TGOS_ADDRESS_URL = "https://gis.tgos.tw/TGAddress/TGAddress.aspx"
TGOS_REFERER = "http://api.tgos.tw/"

CACHE_FIELDS = ["address", "lat", "lon", "source", "matched_address", "fetched_at"]


class TGOSGeocoder:
    """Geocode Taiwanese addresses via TGOS, caching results to a CSV on disk.

    Cache schema (address keyed):
        address, lat, lon, source, matched_address, fetched_at

    `source` is "tgos" for successful lookups; callers that fall back to a
    different source should write their own row with source="manual" etc.
    """

    def __init__(
        self,
        cache_path: Path | str,
        request_delay_s: float = 0.2,
        timeout_s: float = 10.0,
        tghash: str = TGOS_LITE_TGHASH,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.request_delay_s = request_delay_s
        self.timeout_s = timeout_s
        self.tghash = tghash
        self._cache: dict[str, dict] = self._load_cache()

    def _load_cache(self) -> dict[str, dict]:
        if not self.cache_path.exists():
            return {}
        out: dict[str, dict] = {}
        with self.cache_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("lat") and row.get("lon"):
                    row["lat"] = float(row["lat"])
                    row["lon"] = float(row["lon"])
                else:
                    row["lat"] = row["lon"] = None
                out[row["address"]] = row
        return out

    def _append_cache(self, row: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.cache_path.exists()
        with self.cache_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CACHE_FIELDS)
            if new_file:
                writer.writeheader()
            writer.writerow({k: row.get(k, "") for k in CACHE_FIELDS})

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Return (lat, lon) for the address, or None if TGOS can't resolve it.

        Cached results (including negative cache for unresolvable addresses)
        are reused.
        """
        if address in self._cache:
            row = self._cache[address]
            return (row["lat"], row["lon"]) if row["lat"] is not None else None

        result = self._call_tgos(address)
        row = {
            "address": address,
            "lat": result[0] if result else "",
            "lon": result[1] if result else "",
            "source": "tgos" if result else "tgos_no_match",
            "matched_address": result[2] if result else "",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._cache[address] = {**row,
                                "lat": result[0] if result else None,
                                "lon": result[1] if result else None}
        self._append_cache(row)
        return result[:2] if result else None

    def _call_tgos(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Returns (lat, lon, matched_full_address) or None."""
        try:
            r = requests.get(
                TGOS_ADDRESS_URL,
                params={
                    "oAddress": address,
                    "oSRS": "EPSG:4326",
                    "oResultDataType": "json",
                    "pnum": "1",
                    "keystr": self.tghash,
                },
                headers={"Referer": TGOS_REFERER},
                timeout=self.timeout_s,
                verify=False,
            )
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            return None
        finally:
            time.sleep(self.request_delay_s)

        addr_list = data.get("AddressList") or []
        if not addr_list:
            return None
        row = addr_list[0]
        try:
            return float(row["Y"]), float(row["X"]), row.get("FULL_ADDR", "")
        except (KeyError, TypeError, ValueError):
            return None
