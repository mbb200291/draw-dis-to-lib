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
   - `notebooks/01_fetch_data.ipynb` — 整理里界、讀 `data/fallback/libraries_hardcoded.json` 並透過 **TGOS Lite** 把地址轉成經緯度（cache 在 `data/cache/geocode.csv`，第二次跑不打 API）
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

涵蓋 `lib/geo.py`、`lib/colors.py`、`lib/osrm.py`、`lib/geocoder.py` 的純函數邏輯（共 31 個測試）。Notebook 本身仰賴手動執行驗證。

### 圖書館清單與地址 → 經緯度

`data/fallback/libraries_hardcoded.json` 只記 `name`/`district`/`address`。經緯度由 `lib/geocoder.TGOSGeocoder` 從 [TGOS MAP API Lite](https://api.tgos.tw/TGOS_MAP_API/docs/site/web/LiteIntro)（免註冊的政府地址定位服務）查詢，結果 cache 在 `data/cache/geocode.csv`。

要新增或修改圖書館：直接編 JSON 的 address，下次跑 notebook 01 會自動補座標。如果 TGOS 查不到某個地址（極少數，例如門牌沒收錄），會 fallback 到該區質心；要手動覆寫的話在 JSON entry 上加 `"lat": ..., "lon": ...` 即可。

## 未來擴展（Future Work）

對應 Google 地圖其他交通模式（機車、腳踏車、大眾運輸、步行）— 詳見 [spec 的 Future Work 章節](docs/superpowers/specs/2026-05-16-tainan-library-drive-time-map-design.md#future-work後續可能擴展本次先預留架構)。
