"""Tests for lib.geocoder — TGOS client + disk cache.

HTTP is mocked with the `responses` library; no real network calls.
"""

from pathlib import Path

import pytest
import responses

from lib.geocoder import TGOS_ADDRESS_URL, TGOSGeocoder


@pytest.fixture
def geocoder(tmp_path: Path) -> TGOSGeocoder:
    return TGOSGeocoder(cache_path=tmp_path / "cache.csv", request_delay_s=0.0)


def _tgos_response(lat: float, lon: float, full_addr: str = "matched") -> dict:
    return {
        "Info": [{"IsSuccess": "True", "OutTotal": "1"}],
        "AddressList": [{"Y": lat, "X": lon, "FULL_ADDR": full_addr}],
    }


@responses.activate
def test_geocode_hits_tgos_on_first_call(geocoder: TGOSGeocoder):
    responses.add(
        method=responses.GET,
        url=TGOS_ADDRESS_URL,
        json=_tgos_response(23.0244, 120.2380, "臺南市永康區康橋大道255號"),
        status=200,
    )
    result = geocoder.geocode("臺南市永康區康橋大道255號")
    assert result == (23.0244, 120.2380)
    assert len(responses.calls) == 1


@responses.activate
def test_geocode_cache_hit_skips_http(geocoder: TGOSGeocoder):
    responses.add(method=responses.GET, url=TGOS_ADDRESS_URL,
                  json=_tgos_response(23.0, 120.0), status=200)
    geocoder.geocode("某地址")
    geocoder.geocode("某地址")
    geocoder.geocode("某地址")
    assert len(responses.calls) == 1, "cached lookups should not hit HTTP"


@responses.activate
def test_geocode_returns_none_when_no_match_and_caches_negative(
    geocoder: TGOSGeocoder,
):
    responses.add(method=responses.GET, url=TGOS_ADDRESS_URL,
                  json={"Info": [{"IsSuccess": "False"}], "AddressList": []},
                  status=200)
    assert geocoder.geocode("無效地址") is None
    # second call should be cached (no HTTP)
    assert geocoder.geocode("無效地址") is None
    assert len(responses.calls) == 1


@responses.activate
def test_geocode_handles_http_error_as_no_match(geocoder: TGOSGeocoder):
    responses.add(method=responses.GET, url=TGOS_ADDRESS_URL, status=500)
    assert geocoder.geocode("壞掉的查詢") is None
    # negative cache: server error is treated as "no_match" — second call hits cache
    assert geocoder.geocode("壞掉的查詢") is None
    assert len(responses.calls) == 1


@responses.activate
def test_cache_persists_across_instances(tmp_path: Path):
    cache = tmp_path / "cache.csv"
    responses.add(method=responses.GET, url=TGOS_ADDRESS_URL,
                  json=_tgos_response(23.5, 120.5), status=200)
    g1 = TGOSGeocoder(cache_path=cache, request_delay_s=0.0)
    assert g1.geocode("地址A") == (23.5, 120.5)
    # New instance should load the cache from disk and skip HTTP
    g2 = TGOSGeocoder(cache_path=cache, request_delay_s=0.0)
    assert g2.geocode("地址A") == (23.5, 120.5)
    assert len(responses.calls) == 1


def test_cache_file_missing_returns_empty_cache(tmp_path: Path):
    g = TGOSGeocoder(cache_path=tmp_path / "missing.csv")
    assert g._cache == {}
