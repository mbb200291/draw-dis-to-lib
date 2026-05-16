# 台南市各里到最近市立圖書館行車時間地圖 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 依據 spec 產出涵蓋台南 37 區、以「里」為單位、顯示「該里質心到最近台南市立圖書館行車時間」的 PNG / HTML 地圖 + CSV/Excel 原始資料。

**Architecture:** 四階段 notebook 管線（fetch → compute → visualize → export）；純函數（haversine、色階、OSRM client）抽到 `lib/` 模組用 pytest TDD；notebook 只負責編排與展示。

**Tech Stack:** Python 3.10+, Jupyter, geopandas, shapely, pyproj, matplotlib, folium, pandas, openpyxl, requests, tqdm, pytest

**參考文件:** [Spec](../specs/2026-05-16-tainan-library-drive-time-map-design.md)

---

## File Structure

```text
draw-dis-to-lib/
├── .gitignore                         # 新增
├── README.md                          # 新增
├── requirements.txt                   # 新增
├── pyproject.toml                     # 新增（pytest config）
├── lib/                               # 新增（共用 utility，pytest 可測）
│   ├── __init__.py
│   ├── geo.py                         # haversine, project & centroid
│   ├── osrm.py                        # OSRM client + 進度/續跑
│   └── colors.py                      # 時間→顏色分箱
├── notebooks/                         # 新增（4 個 notebook）
│   ├── 01_fetch_data.ipynb
│   ├── 02_compute_times.ipynb
│   ├── 03_visualize.ipynb
│   └── 04_export.ipynb
├── tests/                             # 新增（pytest）
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_geo.py
│   ├── test_colors.py
│   └── test_osrm.py
├── data/
│   ├── raw/.gitkeep                   # 抓下來的原始檔（gitignore 內容）
│   ├── processed/.gitkeep             # 計算中間檔
│   └── fallback/
│       └── libraries_hardcoded.json   # 內建備援圖書館清單
└── output/
    ├── maps/.gitkeep
    └── data/.gitkeep
```

**Responsibility per file:**

- `lib/geo.py`: 純地理計算（haversine 距離、座標系轉換、質心 / representative_point）
- `lib/osrm.py`: OSRM HTTP 呼叫、retry、斷點續跑檔案讀寫
- `lib/colors.py`: 分鐘 → bin → 色碼，以及 matplotlib/folium 可用的 colormap
- `notebooks/*`: 編排上述 utility，並讀寫 `data/`、`output/`
- `tests/*`: 對 `lib/` 做單元測試（不打網路）

---

## Task 1: 專案骨架與 git 初始化

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/.gitignore`
- Create: `/Users/linbangqi/draw-dis-to-lib/requirements.txt`
- Create: `/Users/linbangqi/draw-dis-to-lib/pyproject.toml`
- Create: `/Users/linbangqi/draw-dis-to-lib/README.md`
- Create: empty placeholders `data/raw/.gitkeep`, `data/processed/.gitkeep`, `data/fallback/.gitkeep`, `output/maps/.gitkeep`, `output/data/.gitkeep`

- [ ] **Step 1: 確認當前目錄並 git init**

```bash
cd /Users/linbangqi/draw-dis-to-lib
git init
git status
```

Expected: `Initialized empty Git repository...` 並列出 `goal.md`、`example.png`、`docs/` 為 untracked。

- [ ] **Step 2: 寫 `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
env/

# Jupyter
.ipynb_checkpoints/
*.ipynb_meta

# Data (大檔 + 中間檔不入 repo)
data/raw/*
data/processed/*
!data/raw/.gitkeep
!data/processed/.gitkeep

# Output (產出物不入 repo，可重算)
output/maps/*
output/data/*
!output/maps/.gitkeep
!output/data/.gitkeep

# macOS
.DS_Store
```

注意：`data/fallback/` 沒被 ignore，因為內含手寫備援 JSON 要進 repo。

- [ ] **Step 3: 寫 `requirements.txt`**

```text
# Core
pandas>=2.2
numpy>=1.26

# Geo
geopandas>=0.14
shapely>=2.0
pyproj>=3.6

# Visualization
matplotlib>=3.8
folium>=0.16
mapclassify>=2.6        # geopandas choropleth 需要

# Data IO
openpyxl>=3.1           # Excel writer
requests>=2.31

# Progress
tqdm>=4.66
ipywidgets>=8.1         # tqdm.notebook 進度條

# Jupyter
jupyter>=1.0
notebook>=7.0

# Testing
pytest>=8.0
pytest-mock>=3.12
responses>=0.25         # mock requests
```

- [ ] **Step 4: 寫 `pyproject.toml`（只配 pytest）**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v"
```

- [ ] **Step 5: 建立目錄與 .gitkeep**

```bash
mkdir -p lib notebooks tests data/raw data/processed data/fallback output/maps output/data
touch data/raw/.gitkeep data/processed/.gitkeep data/fallback/.gitkeep output/maps/.gitkeep output/data/.gitkeep
```

- [ ] **Step 6: 寫最小可用 `README.md`（完整版在最後一個 task 補）**

```markdown
# 台南市各里到最近市立圖書館行車時間地圖

依據 [spec](docs/superpowers/specs/2026-05-16-tainan-library-drive-time-map-design.md)。

## 安裝

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 跑

依序開 `notebooks/01_fetch_data.ipynb` → `02_compute_times.ipynb` → `03_visualize.ipynb` → `04_export.ipynb`。

詳細說明見最後一個 task 完成後的 README。
```

- [ ] **Step 7: 建立 venv 並安裝依賴**

```bash
cd /Users/linbangqi/draw-dis-to-lib
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Expected: 安裝成功，無 error。geopandas 可能需要 GDAL 系統函式庫，若失敗請參考 geopandas 安裝文件。

- [ ] **Step 8: 驗證 pytest 可跑（暫時無測試）**

```bash
source .venv/bin/activate
pytest
```

Expected: `no tests ran`（exit code 5），代表 pytest 配置正確。

- [ ] **Step 9: 第一次 commit**

```bash
git add .gitignore requirements.txt pyproject.toml README.md data/ output/ docs/ goal.md example.png
git commit -m "chore: scaffold project structure with deps and gitignore"
```

---

## Task 2: `lib/geo.py` haversine 距離（TDD）

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/lib/__init__.py`（空檔）
- Create: `/Users/linbangqi/draw-dis-to-lib/lib/geo.py`
- Create: `/Users/linbangqi/draw-dis-to-lib/tests/__init__.py`（空檔）
- Create: `/Users/linbangqi/draw-dis-to-lib/tests/conftest.py`
- Create: `/Users/linbangqi/draw-dis-to-lib/tests/test_geo.py`

- [ ] **Step 1: 建空檔**

```bash
touch lib/__init__.py tests/__init__.py
```

- [ ] **Step 2: 寫 `tests/conftest.py` 讓 pytest 找得到 `lib/`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 3: 寫 `tests/test_geo.py` 失敗測試（haversine）**

```python
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
```

- [ ] **Step 4: 跑測試確認失敗**

```bash
source .venv/bin/activate
pytest tests/test_geo.py -v
```

Expected: 4 個測試 `ImportError` 或 `ModuleNotFoundError: lib.geo`。

- [ ] **Step 5: 寫 `lib/geo.py` 最小實作**

```python
"""Geographic utilities: distance and centroid helpers."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_KM * c
```

- [ ] **Step 6: 跑測試確認通過**

```bash
pytest tests/test_geo.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add lib/__init__.py lib/geo.py tests/__init__.py tests/conftest.py tests/test_geo.py
git commit -m "feat(geo): add haversine distance with unit tests"
```

---

## Task 3: `lib/geo.py` 質心 + drive_time_from_distance（TDD）

**Files:**

- Modify: `/Users/linbangqi/draw-dis-to-lib/lib/geo.py`
- Modify: `/Users/linbangqi/draw-dis-to-lib/tests/test_geo.py`

- [ ] **Step 1: 在 `tests/test_geo.py` 結尾追加測試**

```python
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

from lib.geo import drive_minutes_from_km, safe_centroid_latlon


def test_drive_minutes_30kmh():
    # 30 km @ 30 km/h = 60 分鐘
    assert drive_minutes_from_km(30.0, speed_kmh=30.0) == 60.0


def test_drive_minutes_zero_distance():
    assert drive_minutes_from_km(0.0, speed_kmh=30.0) == 0.0


def test_drive_minutes_default_speed_is_30():
    assert drive_minutes_from_km(15.0) == 30.0


def test_safe_centroid_returns_point_inside_polygon():
    # 簡單正方形：質心應在裡面
    sq = Polygon([(120.0, 23.0), (120.1, 23.0), (120.1, 23.1), (120.0, 23.1)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[sq], crs="EPSG:4326")
    lat, lon = safe_centroid_latlon(gdf.iloc[0].geometry, source_crs="EPSG:4326")
    assert 23.0 < lat < 23.1
    assert 120.0 < lon < 120.1


def test_safe_centroid_falls_back_for_donut_when_centroid_outside():
    # C 形多邊形（質心會落在缺口外）— representative_point 應落在實際範圍內
    c_shape = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10), (0, 9), (9, 9), (9, 1), (0, 1)]
    )
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[c_shape], crs="EPSG:3826")
    lat, lon = safe_centroid_latlon(c_shape, source_crs="EPSG:3826")
    # representative_point 保證落在 polygon 內
    from shapely.geometry import Point
    import pyproj
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    x, y = transformer.transform(lon, lat)
    assert c_shape.contains(Point(x, y))
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
pytest tests/test_geo.py -v
```

Expected: 4 個舊測試 pass、5 個新測試 `ImportError`。

- [ ] **Step 3: 擴充 `lib/geo.py`**

在 `lib/geo.py` 結尾追加：

```python
from typing import Tuple

import pyproj
from shapely.geometry.base import BaseGeometry

# 台南位於 EPSG:3826（TWD97 / TM2 zone 121）— 平面座標下做幾何計算才準
_PROJECTED_CRS = "EPSG:3826"
_WGS84 = "EPSG:4326"

_TO_PROJ = pyproj.Transformer.from_crs(_WGS84, _PROJECTED_CRS, always_xy=True)
_TO_WGS84 = pyproj.Transformer.from_crs(_PROJECTED_CRS, _WGS84, always_xy=True)


def drive_minutes_from_km(distance_km: float, speed_kmh: float = 30.0) -> float:
    """Convert straight-line km into estimated drive minutes at the given speed."""
    if speed_kmh <= 0:
        raise ValueError("speed_kmh must be positive")
    return distance_km / speed_kmh * 60.0


def safe_centroid_latlon(
    geom: BaseGeometry,
    source_crs: str = _WGS84,
) -> Tuple[float, float]:
    """Return (lat, lon) for the centroid of geom; fall back to representative_point
    if the centroid lies outside the geometry (e.g. crescent/C-shaped 里界).

    Geometry is projected to EPSG:3826 (a metric CRS for Taiwan) before computing
    the centroid so that the result is geometrically meaningful, then projected
    back to WGS84.
    """
    if source_crs == _WGS84:
        proj_geom = _project_geom(geom, _TO_PROJ)
    elif source_crs == _PROJECTED_CRS:
        proj_geom = geom
    else:
        # 不支援的 CRS：呼叫端應該先 to_crs 過
        raise ValueError(f"Unsupported source_crs={source_crs}; reproject upstream")

    c = proj_geom.centroid
    if not proj_geom.contains(c):
        c = proj_geom.representative_point()

    lon, lat = _TO_WGS84.transform(c.x, c.y)
    return lat, lon


def _project_geom(geom: BaseGeometry, transformer: pyproj.Transformer) -> BaseGeometry:
    """Apply a pyproj Transformer to every coordinate in geom (preserves type)."""
    from shapely.ops import transform as shapely_transform
    return shapely_transform(lambda x, y, z=None: transformer.transform(x, y), geom)
```

- [ ] **Step 4: 跑測試確認通過**

```bash
pytest tests/test_geo.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/geo.py tests/test_geo.py
git commit -m "feat(geo): add drive_minutes and safe_centroid with CRS reprojection"
```

---

## Task 4: `lib/colors.py` 色階分箱（TDD）

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/lib/colors.py`
- Create: `/Users/linbangqi/draw-dis-to-lib/tests/test_colors.py`

- [ ] **Step 1: 寫失敗測試 `tests/test_colors.py`**

```python
import pytest

from lib.colors import BINS_MINUTES, COLORS_HEX, minutes_to_color, minutes_to_bin_label


def test_bins_and_colors_align():
    # COLORS_HEX 數量比 BINS_MINUTES 多 1（n 個 cut 點分成 n+1 個 bin）
    assert len(COLORS_HEX) == len(BINS_MINUTES) + 1


@pytest.mark.parametrize(
    "minutes,expected_hex",
    [
        (0.0, "#1a9641"),       # 0-5 深綠
        (4.9, "#1a9641"),
        (5.0, "#a6d96a"),       # 5-10 淺綠（左閉右開）
        (12.0, "#ffffbf"),      # 10-15 黃
        (18.0, "#fdae61"),      # 15-20 橙
        (25.0, "#d7191c"),      # 20-30 紅
        (60.0, "#7a0177"),      # 30+ 暗紅
        (999.0, "#7a0177"),
    ],
)
def test_minutes_to_color_table(minutes, expected_hex):
    assert minutes_to_color(minutes) == expected_hex


def test_minutes_to_color_negative_raises():
    with pytest.raises(ValueError):
        minutes_to_color(-1.0)


def test_minutes_to_bin_label():
    assert minutes_to_bin_label(0.0) == "0–5"
    assert minutes_to_bin_label(7.5) == "5–10"
    assert minutes_to_bin_label(60.0) == "30+"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
pytest tests/test_colors.py -v
```

Expected: `ImportError`。

- [ ] **Step 3: 寫 `lib/colors.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
pytest tests/test_colors.py -v
```

Expected: 全部 passed（包含參數化的 8 個 case）。

- [ ] **Step 5: Commit**

```bash
git add lib/colors.py tests/test_colors.py
git commit -m "feat(colors): add 6-bin drive-time color scale with unit tests"
```

---

## Task 5: `lib/osrm.py` OSRM client + 斷點續跑（TDD）

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/lib/osrm.py`
- Create: `/Users/linbangqi/draw-dis-to-lib/tests/test_osrm.py`

- [ ] **Step 1: 寫失敗測試 `tests/test_osrm.py`**

```python
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
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
pytest tests/test_osrm.py -v
```

Expected: 全部 `ImportError`。

- [ ] **Step 3: 寫 `lib/osrm.py`**

```python
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
```

- [ ] **Step 4: 跑測試確認通過**

```bash
pytest tests/test_osrm.py -v
```

Expected: 5 passed.

- [ ] **Step 5: 跑全部測試確認沒回歸**

```bash
pytest -v
```

Expected: 18+ passed（geo 9 + colors 5+ + osrm 5）。

- [ ] **Step 6: Commit**

```bash
git add lib/osrm.py tests/test_osrm.py
git commit -m "feat(osrm): add OSRM client with retry and resumable progress CSV"
```

---

## Task 6: `data/fallback/libraries_hardcoded.json` 備援圖書館清單

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/data/fallback/libraries_hardcoded.json`

**Why this task exists:** 圖書館清單只有 ~40 筆，open data API 不穩定時可直接使用 fallback；爬蟲也可能因網站改版失效。這份 JSON 是「永遠能用」的最後防線。

- [ ] **Step 1: 寫 `data/fallback/libraries_hardcoded.json`**

以下為臺南市立圖書館主要館舍的代表性清單（總館 + 各區分館共 40+ 筆）。經緯度為粗估值，正式跑 notebook 時若 open data 抓到更精確值會優先使用。

```json
{
  "_note": "Backup hardcoded list of Tainan municipal libraries. Coordinates are approximate; prefer data from data.tainan.gov.tw when available. Used only when both open-data fetch and website scraping fail in notebook 01.",
  "_source": "Compiled from tnml.tn.edu.tw branch listings.",
  "libraries": [
    {"name": "臺南市立圖書館新總館", "district": "永康區", "address": "永康區康橋大道255號", "lat": 23.0264, "lon": 120.2541},
    {"name": "永康分館", "district": "永康區", "address": "永康區中山南路655號", "lat": 23.0381, "lon": 120.2569},
    {"name": "大灣分館", "district": "永康區", "address": "永康區中華路1巷40號", "lat": 23.0205, "lon": 120.2698},
    {"name": "中西區圖書館", "district": "中西區", "address": "中西區開山路35號", "lat": 22.9881, "lon": 120.2049},
    {"name": "南區圖書館", "district": "南區", "address": "南區夏林路6號", "lat": 22.9710, "lon": 120.1924},
    {"name": "北區圖書館", "district": "北區", "address": "北區公園北路5號", "lat": 23.0044, "lon": 120.2090},
    {"name": "東區圖書館", "district": "東區", "address": "東區林森路二段4號", "lat": 22.9885, "lon": 120.2204},
    {"name": "安平分館", "district": "安平區", "address": "安平區建平五街111號", "lat": 23.0010, "lon": 120.1755},
    {"name": "安南分館", "district": "安南區", "address": "安南區安和路四段260號", "lat": 23.0497, "lon": 120.1762},
    {"name": "鹽水分館", "district": "鹽水區", "address": "鹽水區朝琴路140號", "lat": 23.3199, "lon": 120.2649},
    {"name": "白河分館", "district": "白河區", "address": "白河區中山路1號", "lat": 23.3508, "lon": 120.4153},
    {"name": "後壁分館", "district": "後壁區", "address": "後壁區嘉苗路74-3號", "lat": 23.3661, "lon": 120.3580},
    {"name": "新營圖書館", "district": "新營區", "address": "新營區民治路35號", "lat": 23.3097, "lon": 120.3170},
    {"name": "柳營分館", "district": "柳營區", "address": "柳營區中山西路三段25號", "lat": 23.2778, "lon": 120.3115},
    {"name": "東山分館", "district": "東山區", "address": "東山區東中里東中街43號", "lat": 23.3257, "lon": 120.4047},
    {"name": "六甲分館", "district": "六甲區", "address": "六甲區民權街210號", "lat": 23.2317, "lon": 120.3478},
    {"name": "下營分館", "district": "下營區", "address": "下營區中山路一段301號", "lat": 23.2354, "lon": 120.2643},
    {"name": "麻豆分館", "district": "麻豆區", "address": "麻豆區興中路31號", "lat": 23.1817, "lon": 120.2484},
    {"name": "佳里分館", "district": "佳里區", "address": "佳里區六安里六安街59號", "lat": 23.1635, "lon": 120.1773},
    {"name": "西港分館", "district": "西港區", "address": "西港區慶安路72號", "lat": 23.1233, "lon": 120.2034},
    {"name": "七股分館", "district": "七股區", "address": "七股區大寮里188-1號", "lat": 23.1407, "lon": 120.1395},
    {"name": "將軍分館", "district": "將軍區", "address": "將軍區忠興里6鄰44號", "lat": 23.1990, "lon": 120.1593},
    {"name": "學甲分館", "district": "學甲區", "address": "學甲區華宗路156號", "lat": 23.2326, "lon": 120.1810},
    {"name": "北門分館", "district": "北門區", "address": "北門區北門里舊埕200號", "lat": 23.2670, "lon": 120.1247},
    {"name": "新化分館", "district": "新化區", "address": "新化區忠孝路42號", "lat": 23.0383, "lon": 120.3094},
    {"name": "善化分館", "district": "善化區", "address": "善化區光復路191號", "lat": 23.1325, "lon": 120.2974},
    {"name": "新市分館", "district": "新市區", "address": "新市區中華路125號", "lat": 23.0790, "lon": 120.2944},
    {"name": "安定分館", "district": "安定區", "address": "安定區安定里中沙路347號", "lat": 23.1244, "lon": 120.2374},
    {"name": "山上分館", "district": "山上區", "address": "山上區山上里山上79之1號", "lat": 23.1037, "lon": 120.3537},
    {"name": "玉井分館", "district": "玉井區", "address": "玉井區中正路183號", "lat": 23.1230, "lon": 120.4609},
    {"name": "楠西分館", "district": "楠西區", "address": "楠西區楠西里中興路2號", "lat": 23.1747, "lon": 120.4862},
    {"name": "南化分館", "district": "南化區", "address": "南化區南化里253號", "lat": 23.0418, "lon": 120.4806},
    {"name": "左鎮分館", "district": "左鎮區", "address": "左鎮區左鎮里91-3號", "lat": 23.0584, "lon": 120.4072},
    {"name": "仁德分館", "district": "仁德區", "address": "仁德區中山路591號", "lat": 22.9714, "lon": 120.2511},
    {"name": "歸仁分館", "district": "歸仁區", "address": "歸仁區中正北路一段160號", "lat": 22.9670, "lon": 120.2935},
    {"name": "關廟分館", "district": "關廟區", "address": "關廟區中正路998號", "lat": 22.9646, "lon": 120.3289},
    {"name": "龍崎分館", "district": "龍崎區", "address": "龍崎區崎頂里新市子1-3號", "lat": 22.9657, "lon": 120.3725}
  ]
}
```

- [ ] **Step 2: 驗證 JSON 可被解析**

```bash
python -c "import json; d=json.load(open('data/fallback/libraries_hardcoded.json')); print(f'{len(d[\"libraries\"])} libraries loaded')"
```

Expected: `37 libraries loaded`（或接近）

- [ ] **Step 3: Commit**

```bash
git add data/fallback/libraries_hardcoded.json
git commit -m "data: add hardcoded fallback list of Tainan municipal libraries"
```

---

## Task 7: Notebook 01 — fetch_data

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/notebooks/01_fetch_data.ipynb`

**Notebook 目的：**

1. 抓台南里界 GeoJSON / SHP，過濾出台南市（COUNTYCODE `67` / `6700` 開頭）並存為 `data/raw/tainan_villages.geojson`
2. 抓圖書館清單與經緯度 → `data/raw/tainan_libraries.csv`

**做法（如何建立 notebook）：** 在 Jupyter 或 VS Code 新建一個空 notebook，把以下每個區塊（標題 `### Cell N`）依序貼成一個 cell。Markdown cell 直接貼文字，Code cell 貼 Python code。

- [ ] **Step 1: 建空 notebook 並按順序貼入 cells**

```bash
jupyter notebook notebooks/01_fetch_data.ipynb
# 或在 VS Code 開啟並建立 .ipynb
```

### Cell 1 (Markdown)

```markdown
# 01 · Fetch Data

抓兩種資料：
1. 台南市村里界圖（GeoJSON / SHP）
2. 台南市立圖書館清單與經緯度

成功後輸出：
- `data/raw/tainan_villages.geojson`
- `data/raw/tainan_libraries.csv`
```

### Cell 2 (Code) — imports & paths

```python
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

# 讓 notebook 找得到 lib/
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw"
FALLBACK_DIR = ROOT / "data" / "fallback"
RAW_DIR.mkdir(parents=True, exist_ok=True)

VILLAGES_OUT = RAW_DIR / "tainan_villages.geojson"
LIBRARIES_OUT = RAW_DIR / "tainan_libraries.csv"

print(f"ROOT = {ROOT}")
print(f"RAW_DIR = {RAW_DIR}")
```

### Cell 3 (Markdown)

```markdown
## 1. 村里界圖

來源：政府資料開放平台「村里界圖」（內政部國土測繪中心）

由於該資料集 URL 經常變動且檔案較大（~50MB），預設**手動下載**：

1. 開 https://data.gov.tw/ 搜尋「村里界圖」（或上 https://segis.moi.gov.tw/ ）
2. 下載 WGS84 經緯度版本（SHP 或 GeoJSON 皆可）
3. 解壓後將檔案放到 `data/raw/`，下一個 cell 會自動讀取並過濾台南市
```

### Cell 4 (Code) — 載入並過濾台南

```python
# 自動偵測 data/raw/ 內任何 .shp 或 .geojson（除了我們自己輸出的）
candidates = [
    p for p in RAW_DIR.glob("*")
    if p.suffix.lower() in (".shp", ".geojson", ".gpkg")
    and p.name != VILLAGES_OUT.name
]

if not candidates:
    raise FileNotFoundError(
        f"找不到村里界圖。請依上一個 cell 說明手動下載到 {RAW_DIR}"
    )

src = candidates[0]
print(f"讀取 {src.name}...")
gdf = gpd.read_file(src)
print(f"全國共 {len(gdf)} 個里")
print(f"欄位：{list(gdf.columns)}")
gdf.head(2)
```

### Cell 5 (Code) — 過濾台南並輸出

```python
# 內政部資料的欄位名稱可能是 COUNTYCODE / COUNTY_ID / COUNTY 之一；遇到都嘗試
county_col_candidates = ["COUNTYCODE", "COUNTY_ID", "COUNTY"]
county_col = next((c for c in county_col_candidates if c in gdf.columns), None)
if county_col is None:
    raise KeyError(
        f"找不到縣市代碼欄位（試過 {county_col_candidates}）；"
        f"現有欄位：{list(gdf.columns)}"
    )

# 台南：代碼以 67 開頭或名稱含「臺南」/「台南」
if gdf[county_col].dtype == object:
    mask = gdf[county_col].astype(str).str.contains("臺南|台南", na=False) | \
           gdf[county_col].astype(str).str.startswith("67")
else:
    mask = gdf[county_col].astype(str).str.startswith("67")

tainan = gdf[mask].copy()
print(f"台南市共 {len(tainan)} 個里")

# 確保 CRS 是 WGS84
if tainan.crs is None or tainan.crs.to_epsg() != 4326:
    tainan = tainan.to_crs(epsg=4326)

# 給每個里一個穩定的 village_id；優先使用 VILLCODE
id_col = next(
    (c for c in ["VILLCODE", "VILLAGE_ID", "VILLAGE_CODE"] if c in tainan.columns),
    None,
)
if id_col is None:
    tainan["village_id"] = [f"tn_{i:04d}" for i in range(len(tainan))]
else:
    tainan["village_id"] = tainan[id_col].astype(str)

# 統一里名 / 區名欄位
name_col = next((c for c in ["VILLNAME", "VILLAGE", "NAME"] if c in tainan.columns), None)
district_col = next((c for c in ["TOWNNAME", "TOWN"] if c in tainan.columns), None)

tainan["village_name"] = tainan[name_col] if name_col else ""
tainan["district"] = tainan[district_col] if district_col else ""

# 只保留必要欄位 + 幾何
out = tainan[["village_id", "village_name", "district", "geometry"]]
out.to_file(VILLAGES_OUT, driver="GeoJSON")
print(f"✅ Saved {len(out)} villages to {VILLAGES_OUT}")
```

### Cell 6 (Markdown)

```markdown
## 2. 圖書館清單

策略：依序嘗試
1. 臺南市政府開放資料平台 https://data.tainan.gov.tw/ (`圖書館各館資訊`)
2. 內建備援 `data/fallback/libraries_hardcoded.json`

備援清單已涵蓋 37 區的主要館舍，不需爬蟲也能跑完整個流程。
```

### Cell 7 (Code) — 嘗試從 open data 抓，失敗就用 fallback

```python
def try_tainan_open_data() -> pd.DataFrame | None:
    """Try Tainan open data API; return DataFrame or None on failure."""
    # 此處為示意；實際 API endpoint 可能變動，找不到就 return None
    # 主要 dataset 名稱常見：圖書館分館資訊 / 臺南市立圖書館各分館
    try:
        url = "https://data.tainan.gov.tw/api/3/action/datastore_search"
        # 占位：實際使用前請去 data.tainan.gov.tw 搜尋「圖書館」確認 resource_id
        # 找到後填入下面這個變數，否則直接返回 None
        resource_id = ""
        if not resource_id:
            return None
        resp = requests.get(url, params={"resource_id": resource_id, "limit": 200}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("result", {}).get("records", [])
        if not records:
            return None
        # 假設欄位有 name / address / lat / lon —— 視實際資料調整
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        print(f"⚠️  Tainan open data fetch failed: {e}")
        return None


def load_fallback() -> pd.DataFrame:
    with (FALLBACK_DIR / "libraries_hardcoded.json").open(encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data["libraries"])


libs = try_tainan_open_data()
if libs is None:
    print("ℹ️  Using hardcoded fallback library list")
    libs = load_fallback()
else:
    print(f"✅ Fetched {len(libs)} libraries from Tainan open data")

# 確保 schema 一致
required = {"name", "district", "address", "lat", "lon"}
missing = required - set(libs.columns)
if missing:
    raise ValueError(f"Library data missing columns: {missing}")

libs = libs[["name", "district", "address", "lat", "lon"]].copy()
libs.to_csv(LIBRARIES_OUT, index=False, encoding="utf-8-sig")  # utf-8-sig 讓 Excel 看中文
print(f"✅ Saved {len(libs)} libraries to {LIBRARIES_OUT}")
libs.head()
```

### Cell 8 (Code) — sanity check：把圖書館點與里界畫個小圖預覽

```python
import matplotlib.pyplot as plt

villages = gpd.read_file(VILLAGES_OUT)
libs_gdf = gpd.GeoDataFrame(
    libs,
    geometry=gpd.points_from_xy(libs.lon, libs.lat),
    crs="EPSG:4326",
)

fig, ax = plt.subplots(figsize=(8, 9))
villages.boundary.plot(ax=ax, linewidth=0.2, color="gray")
libs_gdf.plot(ax=ax, color="red", markersize=20)
ax.set_title(f"Tainan: {len(villages)} villages + {len(libs_gdf)} libraries")
ax.set_aspect("equal")
plt.show()
```

- [ ] **Step 2: 整本 notebook Restart & Run All，確認所有 cell 跑過**

Expected:
- `data/raw/tainan_villages.geojson` 存在，~700-800 筆里
- `data/raw/tainan_libraries.csv` 存在，~37 筆圖書館
- 最後一個 cell 顯示預覽圖：紅點散布在台南輪廓內

如果村里界圖手動下載步驟出問題，記下實際使用的資料來源 URL，並修正 cell 3 的說明。

- [ ] **Step 3: Commit**

```bash
git add notebooks/01_fetch_data.ipynb
git commit -m "feat(notebook): add 01_fetch_data for villages and libraries"
```

---

## Task 8: Notebook 02 — compute_times（v1 haversine）

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/notebooks/02_compute_times.ipynb`

**Notebook 目的：** 對每個里質心，找到最近的台南市立圖書館，輸出 `data/processed/village_to_nearest_library.csv`。本 task 只實作 v1（haversine × 30 km/h），v2（OSRM）在下一個 task 加。

- [ ] **Step 1: 建空 notebook 並依序貼入 cells**

### Cell 1 (Markdown)

```markdown
# 02 · Compute Drive Times

對每個里質心，計算到最近的台南市立圖書館的時間。

支援兩種 method（由 cell 內的 `METHOD` 變數切換）：
- `haversine_30kmh` — 直線距離 ÷ 30 km/h（快、粗略）
- `osrm` — 真實道路路徑（慢、準）；會自動斷點續跑

輸出：`data/processed/village_to_nearest_library.csv`
```

### Cell 2 (Code) — imports & paths & 設定

```python
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from tqdm.notebook import tqdm

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

from lib.geo import haversine_km, drive_minutes_from_km, safe_centroid_latlon

RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

VILLAGES_IN = RAW_DIR / "tainan_villages.geojson"
LIBRARIES_IN = RAW_DIR / "tainan_libraries.csv"
OUTPUT = PROC_DIR / "village_to_nearest_library.csv"

# 切換計算方式：先用 haversine 跑一遍，確認管線正常再切 osrm
METHOD = "haversine_30kmh"   # or "osrm"
SPEED_KMH = 30.0
```

### Cell 3 (Code) — 載入資料 & 算質心

```python
villages = gpd.read_file(VILLAGES_IN)
libraries = pd.read_csv(LIBRARIES_IN)

print(f"Villages: {len(villages)}, Libraries: {len(libraries)}")

# 對每個里算質心，存成新欄位
centroids = villages.geometry.apply(lambda g: safe_centroid_latlon(g, source_crs="EPSG:4326"))
villages["centroid_lat"] = [c[0] for c in centroids]
villages["centroid_lon"] = [c[1] for c in centroids]
villages[["village_id", "village_name", "district", "centroid_lat", "centroid_lon"]].head()
```

### Cell 4 (Code) — haversine 計算（一次到位，無需斷點續跑）

```python
def nearest_library_haversine(lat: float, lon: float) -> dict:
    distances = libraries.apply(
        lambda r: haversine_km(lat, lon, r["lat"], r["lon"]),
        axis=1,
    )
    idx = distances.idxmin()
    return {
        "nearest_library": libraries.at[idx, "name"],
        "library_lat": libraries.at[idx, "lat"],
        "library_lon": libraries.at[idx, "lon"],
        "distance_km": float(distances.at[idx]),
    }


if METHOD == "haversine_30kmh":
    rows = []
    for _, v in tqdm(villages.iterrows(), total=len(villages), desc="haversine"):
        n = nearest_library_haversine(v["centroid_lat"], v["centroid_lon"])
        rows.append({
            "village_id": v["village_id"],
            "village_name": v["village_name"],
            "district": v["district"],
            "centroid_lat": v["centroid_lat"],
            "centroid_lon": v["centroid_lon"],
            **n,
            "drive_minutes": drive_minutes_from_km(n["distance_km"], speed_kmh=SPEED_KMH),
            "method": METHOD,
        })
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(result)} rows to {OUTPUT}")
    result.head()
```

### Cell 5 (Code) — sanity check：時間分布

```python
result = pd.read_csv(OUTPUT)
print(result["drive_minutes"].describe())
print("\nBy bin:")
import numpy as np
bins = [0, 5, 10, 15, 20, 30, np.inf]
result["bin"] = pd.cut(result["drive_minutes"], bins=bins, right=False)
print(result["bin"].value_counts().sort_index())
```

- [ ] **Step 2: Restart & Run All**

Expected:
- `data/processed/village_to_nearest_library.csv` 存在，row 數 ≈ 里數
- 時間分布合理：majority < 20 min，山區（楠西、南化、左鎮）較長
- 整個 notebook 在 30 秒內跑完

- [ ] **Step 3: Commit**

```bash
git add notebooks/02_compute_times.ipynb
git commit -m "feat(notebook): add 02_compute_times with haversine method"
```

---

## Task 9: Notebook 02 — 加入 v2 OSRM 計算（含斷點續跑與進度條）

**Files:**

- Modify: `/Users/linbangqi/draw-dis-to-lib/notebooks/02_compute_times.ipynb`

- [ ] **Step 1: 在 Cell 4 之後追加新 cell（保留原 cell 4 給 haversine）**

### Cell 4b (Code) — OSRM 計算 + 斷點續跑

貼到 cell 5（sanity check）之前。

```python
from lib.osrm import OSRMClient, OSRMError, load_progress, save_progress_row

OSRM_PROGRESS = PROC_DIR / "osrm_progress.csv"
N_CANDIDATES = 3           # 先用 haversine 取最近 3 座，再 OSRM 算實際時間取最小
OSRM_REQUEST_DELAY_S = 0.2  # 對公開 server 友善


def compute_osrm_for_village(
    client: OSRMClient, v_lat: float, v_lon: float
) -> dict:
    # 先 haversine 排序取候選
    candidates = libraries.copy()
    candidates["hav_km"] = candidates.apply(
        lambda r: haversine_km(v_lat, v_lon, r["lat"], r["lon"]), axis=1
    )
    top = candidates.nsmallest(N_CANDIDATES, "hav_km")

    best: dict | None = None
    method = "osrm_driving"
    for _, lib in top.iterrows():
        try:
            minutes = client.route_duration_minutes(
                v_lat, v_lon, lib["lat"], lib["lon"]
            )
        except OSRMError as exc:
            # 整個候選都失敗會 fallback；單一失敗只是跳過此候選
            continue
        if best is None or minutes < best["drive_minutes"]:
            best = {
                "nearest_library": lib["name"],
                "library_lat": float(lib["lat"]),
                "library_lon": float(lib["lon"]),
                "distance_km": float(lib["hav_km"]),
                "drive_minutes": minutes,
            }

    if best is None:
        # 所有候選都失敗 → fallback 到 haversine，標記方法
        fallback = nearest_library_haversine(v_lat, v_lon)
        best = {
            **fallback,
            "drive_minutes": drive_minutes_from_km(fallback["distance_km"], SPEED_KMH),
        }
        method = "osrm_failed_fallback"

    best["method"] = method
    return best


if METHOD == "osrm":
    client = OSRMClient(request_delay_s=OSRM_REQUEST_DELAY_S)

    done = load_progress(OSRM_PROGRESS)
    print(f"Resume: already done {len(done)} / {len(villages)} villages")

    todo = villages[~villages["village_id"].isin(done.keys())].copy()
    print(f"To process: {len(todo)}")

    for _, v in tqdm(todo.iterrows(), total=len(todo), desc="OSRM"):
        r = compute_osrm_for_village(client, v["centroid_lat"], v["centroid_lon"])
        save_progress_row(
            OSRM_PROGRESS,
            village_id=v["village_id"],
            nearest_library=r["nearest_library"],
            library_lat=r["library_lat"],
            library_lon=r["library_lon"],
            distance_km=r["distance_km"],
            drive_minutes=r["drive_minutes"],
            method=r["method"],
        )

    # 合併 progress + village 中繼資料，輸出最終 csv
    done = load_progress(OSRM_PROGRESS)
    rows = []
    for _, v in villages.iterrows():
        d = done.get(v["village_id"])
        if d is None:
            continue
        rows.append({
            "village_id": v["village_id"],
            "village_name": v["village_name"],
            "district": v["district"],
            "centroid_lat": v["centroid_lat"],
            "centroid_lon": v["centroid_lon"],
            **{k: d[k] for k in ["nearest_library", "library_lat", "library_lon", "distance_km", "drive_minutes", "method"]},
        })
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(result)} rows to {OUTPUT}")
    n_fallback = (result["method"] == "osrm_failed_fallback").sum()
    if n_fallback:
        print(f"⚠️  {n_fallback} villages fell back to haversine due to OSRM errors")
```

- [ ] **Step 2: 先以小樣本驗證 OSRM cell 能跑（避免一開始就跑 6 小時）**

在 cell 2 暫時把 `METHOD = "osrm"`，並在 cell 3 後面臨時加：

```python
villages = villages.head(10)   # TEMP: smoke test only
```

跑 cell 2、3、4b（跳過 4），觀察：
- tqdm 進度條有顯示 `10/10`
- 完成後 `data/processed/osrm_progress.csv` 有 10 row
- `data/processed/village_to_nearest_library.csv` 有 10 row、`method` 欄是 `osrm_driving`（或部分 `osrm_failed_fallback`）

驗證後**移除 `villages.head(10)` 那行**，把 `METHOD` 改回 `haversine_30kmh`（避免下次誤觸跑 6 小時）。

- [ ] **Step 3: 驗證斷點續跑**

故意中斷上一步跑到一半（按 stop），再跑一次同一個 cell。應看到：

```text
Resume: already done 5 / 10 villages
To process: 5
```

只重跑剩下 5 個。

- [ ] **Step 4: Commit（包含 OSRM 升級）**

```bash
git add notebooks/02_compute_times.ipynb
git commit -m "feat(notebook): add OSRM method with resumable progress to 02"
```

---

## Task 10: Notebook 03 — visualize 靜態 PNG

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/notebooks/03_visualize.ipynb`

- [ ] **Step 1: 建空 notebook 並貼入以下 cells**

### Cell 1 (Markdown)

```markdown
# 03 · Visualize

讀 `data/processed/village_to_nearest_library.csv` + 里界 GeoJSON，輸出：
- `output/maps/tainan_library_time_static.png`
- `output/maps/tainan_library_time_interactive.html`
```

### Cell 2 (Code) — imports & 讀資料

```python
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

from lib.colors import BINS_MINUTES, COLORS_HEX

RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output" / "maps"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

villages = gpd.read_file(RAW_DIR / "tainan_villages.geojson")
times = pd.read_csv(PROC_DIR / "village_to_nearest_library.csv")
libs = pd.read_csv(RAW_DIR / "tainan_libraries.csv")

merged = villages.merge(times[["village_id", "drive_minutes", "nearest_library", "method"]], on="village_id", how="left")
print(f"Merged: {len(merged)} villages, missing time: {merged['drive_minutes'].isna().sum()}")
merged.head()
```

### Cell 3 (Code) — 靜態 PNG

```python
cmap = ListedColormap(COLORS_HEX)
bounds = [0, *BINS_MINUTES, 1e9]
norm = BoundaryNorm(bounds, cmap.N)

fig, ax = plt.subplots(figsize=(12, 14), dpi=150)

merged.plot(
    column="drive_minutes",
    cmap=cmap,
    norm=norm,
    edgecolor="white",
    linewidth=0.15,
    ax=ax,
    missing_kwds={"color": "lightgray", "label": "no data"},
)

# 區界（粗一點）
districts = merged.dissolve(by="district", as_index=False)
districts.boundary.plot(ax=ax, color="black", linewidth=0.6)

# 圖書館位置
libs_gdf = gpd.GeoDataFrame(libs, geometry=gpd.points_from_xy(libs.lon, libs.lat), crs="EPSG:4326")
libs_gdf.plot(ax=ax, marker="P", color="black", markersize=40, edgecolor="white", linewidth=0.5)

# 圖例
labels = ["0–5", "5–10", "10–15", "15–20", "20–30", "30+"]
legend_handles = [Patch(facecolor=c, edgecolor="white", label=f"{lab} 分鐘") for c, lab in zip(COLORS_HEX, labels)]
legend_handles.append(Patch(facecolor="lightgray", edgecolor="white", label="無資料"))
ax.legend(handles=legend_handles, title="到最近市立圖書館", loc="lower left", fontsize=9)

# 中文標題：matplotlib 預設字型可能無中文 → 用系統字型；找不到可註解掉
try:
    plt.rcParams["font.sans-serif"] = ["PingFang TC", "Heiti TC", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass

ax.set_title("台南市各里到最近市立圖書館行車時間", fontsize=14, pad=10)
ax.set_axis_off()
ax.set_aspect("equal")

out = OUTPUT_DIR / "tainan_library_time_static.png"
fig.savefig(out, bbox_inches="tight", dpi=150)
plt.show()
print(f"✅ Saved {out}")
```

### Cell 4 (Code) — 互動 HTML（folium）

```python
import folium
from folium.features import GeoJsonTooltip
from lib.colors import minutes_to_color

# 為每個 feature 加 fill_color 屬性
merged["fill_color"] = merged["drive_minutes"].apply(
    lambda m: minutes_to_color(m) if pd.notna(m) else "#cccccc"
)
merged["drive_minutes_str"] = merged["drive_minutes"].apply(
    lambda m: f"{m:.1f}" if pd.notna(m) else "N/A"
)

# 地圖中心：台南幾何中心
centroid = merged.geometry.unary_union.centroid
m = folium.Map(location=[centroid.y, centroid.x], zoom_start=11, tiles="cartodbpositron")

folium.GeoJson(
    merged.to_json(),
    name="到最近圖書館行車時間",
    style_function=lambda feat: {
        "fillColor": feat["properties"]["fill_color"],
        "color": "white",
        "weight": 0.3,
        "fillOpacity": 0.75,
    },
    tooltip=GeoJsonTooltip(
        fields=["village_name", "district", "nearest_library", "drive_minutes_str", "method"],
        aliases=["里", "區", "最近圖書館", "預估時間(分)", "計算方式"],
        sticky=True,
    ),
).add_to(m)

# 圖書館標記
for _, lib in libs.iterrows():
    folium.Marker(
        location=[lib["lat"], lib["lon"]],
        popup=folium.Popup(f"<b>{lib['name']}</b><br>{lib['district']}<br>{lib['address']}", max_width=300),
        icon=folium.Icon(color="black", icon="book", prefix="fa"),
    ).add_to(m)

# 圖例（HTML 直接嵌入）
legend_html = """
<div style="position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            background: white; padding: 10px; border: 1px solid #999;
            font-family: sans-serif; font-size: 12px;">
  <b>到最近市立圖書館（分鐘）</b><br>
""" + "".join(
    f'<div><span style="display:inline-block;width:14px;height:14px;background:{c};margin-right:6px;"></span>{lab}</div>'
    for c, lab in zip(COLORS_HEX, ["0–5", "5–10", "10–15", "15–20", "20–30", "30+"])
) + "</div>"
m.get_root().html.add_child(folium.Element(legend_html))

out = OUTPUT_DIR / "tainan_library_time_interactive.html"
m.save(str(out))
print(f"✅ Saved {out}")
m
```

- [ ] **Step 2: Restart & Run All；人眼檢查兩張圖**

PNG 檢查項：
- 視覺風格類似 example.png（離散色階：綠 / 黃 / 紅）
- 黑色十字（圖書館位置）散布在各區
- 山區（楠西、南化、左鎮、龍崎）整體偏紅 / 暗紅
- 市中心（中西、東、北、安平）整體偏綠
- 圖例與標題清楚（標題的中文若亂碼，註解 `set_title` 或調整 `font.sans-serif`）

HTML 檢查項：
- 用瀏覽器打開能正常顯示
- Hover 任意里能看到里名、區名、最近圖書館、時間
- 點圖書館 marker 能彈出資訊

- [ ] **Step 3: Commit**

```bash
git add notebooks/03_visualize.ipynb
git commit -m "feat(notebook): add 03_visualize for static PNG and interactive HTML"
```

---

## Task 11: Notebook 04 — export CSV + Excel

**Files:**

- Create: `/Users/linbangqi/draw-dis-to-lib/notebooks/04_export.ipynb`

- [ ] **Step 1: 建空 notebook 並貼入 cells**

### Cell 1 (Markdown)

```markdown
# 04 · Export

把 `data/processed/village_to_nearest_library.csv` 加上圖書館清單一起匯出為終端使用者要看的：

- `output/data/tainan_library_drive_time.csv`
- `output/data/tainan_library_drive_time.xlsx`（兩個 sheet：「行車時間」與「圖書館清單」）
```

### Cell 2 (Code)

```python
import sys
from pathlib import Path

import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

times = pd.read_csv(PROC_DIR / "village_to_nearest_library.csv")
libs = pd.read_csv(RAW_DIR / "tainan_libraries.csv")

# 排序：依 區 → 里 名稱，讓 Excel 開起來好看
times_sorted = times.sort_values(["district", "village_name"]).reset_index(drop=True)

# CSV：utf-8-sig 讓 Excel 不亂碼
csv_out = OUT_DIR / "tainan_library_drive_time.csv"
times_sorted.to_csv(csv_out, index=False, encoding="utf-8-sig")
print(f"✅ CSV: {csv_out}")

# Excel：兩個 sheet
xlsx_out = OUT_DIR / "tainan_library_drive_time.xlsx"
with pd.ExcelWriter(xlsx_out, engine="openpyxl") as writer:
    times_sorted.to_excel(writer, sheet_name="行車時間", index=False)
    libs.to_excel(writer, sheet_name="圖書館清單", index=False)
print(f"✅ Excel: {xlsx_out}")

# 顯示前幾筆驗證
times_sorted.head()
```

- [ ] **Step 2: Run All；用 Excel / Numbers 開 .xlsx 確認中文正常**

Expected:
- `output/data/tainan_library_drive_time.csv` 存在，可被 Excel 開且中文正常
- `output/data/tainan_library_drive_time.xlsx` 兩個 sheet：「行車時間」、「圖書館清單」

- [ ] **Step 3: Commit**

```bash
git add notebooks/04_export.ipynb
git commit -m "feat(notebook): add 04_export for CSV and Excel output"
```

---

## Task 12: 完整 README + 收尾

**Files:**

- Modify: `/Users/linbangqi/draw-dis-to-lib/README.md`

- [ ] **Step 1: 覆寫 `README.md`（替換 Task 1 寫的最小版本）**

```markdown
# 台南市各里到最近市立圖書館行車時間地圖

依據 [spec](docs/superpowers/specs/2026-05-16-tainan-library-drive-time-map-design.md) 製作。

繪製涵蓋台南市全部 37 個行政區的地圖，以「里」為單位上色，呈現該里質心開車到最近的台南市立圖書館（總館 + 各區分館）所需的行車時間。

## 安裝

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> macOS 上 geopandas 安裝若失敗，需要先用 Homebrew 裝 GDAL：`brew install gdal`

## 跑

### 第一次

1. **手動下載村里界圖**到 `data/raw/`（任一 `.shp` / `.geojson` 即可，notebook 會自動偵測過濾台南）。來源：[政府資料開放平台](https://data.gov.tw) 搜尋「村里界圖」或 [內政部 SEGIS](https://segis.moi.gov.tw/) 下載 WGS84 版本。
2. 依序執行：
   - `notebooks/01_fetch_data.ipynb` — 整理里界、抓 / 載入圖書館清單
   - `notebooks/02_compute_times.ipynb` — 算最近圖書館時間
   - `notebooks/03_visualize.ipynb` — 產出 PNG + HTML
   - `notebooks/04_export.ipynb` — 產出 CSV + Excel

### 切換計算方式

`notebooks/02_compute_times.ipynb` 的第 2 個 cell 有：

```python
METHOD = "haversine_30kmh"   # 或 "osrm"
```

- `haversine_30kmh` — 直線距離 ÷ 30 km/h，**30 秒**內完成，適合快速驗證
- `osrm` — 真實道路路徑（透過 OSRM 公開 server），**最多數小時**完成，較準確；支援斷點續跑

OSRM 進度檔在 `data/processed/osrm_progress.csv`。中斷後再執行 cell 會從上次斷點繼續。

## 輸出

- `output/maps/tainan_library_time_static.png` — 靜態地圖
- `output/maps/tainan_library_time_interactive.html` — 互動式地圖（hover 看資訊）
- `output/data/tainan_library_drive_time.csv` — 原始資料 CSV
- `output/data/tainan_library_drive_time.xlsx` — 原始資料 Excel（兩個 sheet）

## 開發

跑單元測試：

```bash
pytest
```

涵蓋 `lib/geo.py`、`lib/colors.py`、`lib/osrm.py` 的純函數邏輯。Notebook 本身仰賴手動執行驗證。

## 未來擴展（Future Work）

對應 Google 地圖其他交通模式（機車、腳踏車、大眾運輸、步行）— 詳見 [spec 的 Future Work 章節](docs/superpowers/specs/2026-05-16-tainan-library-drive-time-map-design.md#future-work後續可能擴展本次先預留架構)。
```

- [ ] **Step 2: 跑全部測試確認沒回歸**

```bash
source .venv/bin/activate
pytest -v
```

Expected: 全部 pass。

- [ ] **Step 3: 整理 git status，確認沒漏檔**

```bash
git status
```

不該有 untracked 的 source / test / notebook 檔（data/output 因為 gitignore 不會顯示）。

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: write full README with run instructions and dev notes"
```

---

## Self-Review Notes

跑完所有 task 後請手動驗收 spec 的 Success Criteria：

- [ ] 依序執行 4 個 notebook 可從零產出三種輸出 → Task 7-11
- [ ] 靜態 PNG 視覺風格接近 example.png → Task 10 step 2 人眼檢查
- [ ] 互動 HTML 可在瀏覽器打開，hover 任一里能看到正確資料 → Task 10 step 2 人眼檢查
- [ ] CSV/Excel 欄位完整、可被 Excel 直接開啟（中文不亂碼） → Task 11 step 2 驗證
- [ ] v1（haversine）跑完不超過 30 秒 → Task 8 step 2 驗證
- [ ] v2（OSRM）在 6 小時內跑完，期間有清楚的進度條 → Task 9 step 2 smoke test 驗證有進度條；完整跑由使用者決定何時做
- [ ] v2 中斷後重跑可從上次斷點繼續 → Task 9 step 3 驗證
- [ ] 結果通過人眼合理性檢查（市區短、山區長） → Task 8 step 2、Task 10 step 2

## 完成後（非必要）

若需要產出機車 / 腳踏車版本：在 `notebooks/02_compute_times.ipynb` 把 `OSRMClient(profile="...")` 改為 `motorcycle` / `bicycle`，並把 OUTPUT 檔名加後綴 `..._motorcycle.csv` 避免覆蓋。詳見 spec Future Work。
