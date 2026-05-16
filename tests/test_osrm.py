import json
from pathlib import Path

import pytest
import responses

from lib.osrm import (
    OSRMClient,
    OSRMError,
    load_progress,
    save_progress_row,
)

OSRM_URL = "https://router.project-osrm.org"


@responses.activate
def test_route_duration_minutes_happy_path():
    # OSRM /route 回 duration 單位是秒
    responses.add(
        method=responses.GET,
        url=f"{OSRM_URL}/route/v1/driving/120.2,23.0;120.3,23.1",
        json={
            "code": "Ok",
            "routes": [{"duration": 600.0, "distance": 5000.0}],
        },
        status=200,
    )
    client = OSRMClient(base_url=OSRM_URL, request_delay_s=0.0)
    minutes = client.route_duration_minutes(23.0, 120.2, 23.1, 120.3)
    assert minutes == pytest.approx(10.0)


@responses.activate
def test_route_duration_raises_on_no_route():
    responses.add(
        method=responses.GET,
        url=f"{OSRM_URL}/route/v1/driving/120.2,23.0;120.3,23.1",
        json={"code": "NoRoute"},
        status=200,
    )
    client = OSRMClient(base_url=OSRM_URL, request_delay_s=0.0)
    with pytest.raises(OSRMError):
        client.route_duration_minutes(23.0, 120.2, 23.1, 120.3)


@responses.activate
def test_route_duration_retries_on_500_then_succeeds():
    url = f"{OSRM_URL}/route/v1/driving/120.2,23.0;120.3,23.1"
    responses.add(method=responses.GET, url=url, status=500)
    responses.add(method=responses.GET, url=url, status=500)
    responses.add(
        method=responses.GET,
        url=url,
        json={"code": "Ok", "routes": [{"duration": 300.0, "distance": 2000.0}]},
        status=200,
    )
    client = OSRMClient(base_url=OSRM_URL, request_delay_s=0.0, max_retries=3)
    minutes = client.route_duration_minutes(23.0, 120.2, 23.1, 120.3)
    assert minutes == pytest.approx(5.0)


def test_load_progress_when_file_missing(tmp_path: Path):
    assert load_progress(tmp_path / "missing.csv") == {}


def test_save_then_load_progress_roundtrip(tmp_path: Path):
    progress_file = tmp_path / "progress.csv"
    save_progress_row(
        progress_file,
        village_id="6700A001",
        nearest_library="台南市立圖書館新總館",
        library_lat=23.05,
        library_lon=120.25,
        distance_km=3.2,
        drive_minutes=8.5,
        method="osrm_driving",
    )
    save_progress_row(
        progress_file,
        village_id="6700A002",
        nearest_library="安南分館",
        library_lat=23.07,
        library_lon=120.20,
        distance_km=5.0,
        drive_minutes=12.0,
        method="osrm_driving",
    )
    progress = load_progress(progress_file)
    assert set(progress.keys()) == {"6700A001", "6700A002"}
    assert progress["6700A001"]["drive_minutes"] == 8.5
    assert progress["6700A002"]["nearest_library"] == "安南分館"
