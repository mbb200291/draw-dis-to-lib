# 台南市各里到最近市立圖書館行車時間地圖

**Date**: 2026-05-16
**Status**: Approved design, awaiting implementation plan

## Goal

繪製涵蓋台南市全部 37 區的地圖，以「里」為單位上色，呈現「該里質心開車到最近的台南市立圖書館（總館 + 分館）所需的行車時間」。

成果輸出三種格式：

1. 靜態地圖（PNG）
2. 互動式網頁地圖（HTML）
3. 原始資料（CSV + Excel）

## Scope

- **空間範圍**：臺南市全部 37 個行政區（縣代碼 6700），預估約 750+ 里
- **圖書館範圍**：臺南市立圖書館新總館 + 各區分館（約 40 座）。**不含**智慧圖書館（自助借還）、閱覽室、其他附屬點
- **跨縣市限制**：即使隔壁縣市的圖書館實際上更近，也只計算同屬台南市的圖書館
- **單位**：每個里取質心作為計算點

## Non-Goals（本次迭代不做）

- 不考慮時段差異（無交通流量資訊）
- 不做歷史變化分析
- 不做跨縣市圖書館（即使更近）

## Future Work（後續可能擴展，本次先預留架構）

對應 Google 地圖的其他交通模式，未來可能補做：

- **機車**（OSRM 可用 `motorcycle` profile，或調整 `driving` 速度）
- **腳踏車**（OSRM `bicycle` profile）
- **大眾運輸**（公車 / 火車，需另外抓 GTFS 資料，門檻較高）
- **步行**（OSRM `foot` profile）

**設計影響**：`compute_times` 階段的 `method` 欄位除了記錄 `haversine_30kmh` / `osrm_driving`，未來可擴展為 `osrm_motorcycle`、`osrm_bicycle`、`osrm_foot`、`gtfs_transit`。輸出檔案命名也預留模式後綴（如 `tainan_library_time_driving.png`、`..._motorcycle.png`），便於同一份程式跑出多份對照圖。

## 技術選擇

| 項目     | 選擇                                              |
| -------- | ------------------------------------------------- |
| 語言     | Python 3.10+                                      |
| 開發環境 | Jupyter Notebook（每階段一個 notebook）           |
| 地理處理 | `geopandas`, `shapely`, `pyproj`                  |
| 路徑 v1  | Haversine 直線距離 ÷ 平均速度 **30 km/h**         |
| 路徑 v2  | OSRM 公開 demo server (`router.project-osrm.org`) |
| 靜態圖   | `matplotlib`                                      |
| 互動圖   | `folium`                                          |
| 資料處理 | `pandas`, `openpyxl`                              |
| HTTP     | `requests`                                        |
| 進度顯示 | `tqdm.notebook`（OSRM 長時間任務必備）            |

## 系統架構

四階段資料管線，每階段可獨立重跑、有明確 input/output 介面：

```text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. fetch_data │ -> │ 2. compute   │ -> │ 3. visualize │ -> │ 4. export    │
│   里界 GeoJSON│    │   時間矩陣   │    │   PNG + HTML │    │   CSV + Excel│
│   圖書館清單  │    │   每里→最近館│    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                    │                    │                    │
       v                    v                    v                    v
   data/raw/          data/processed/       output/maps/         output/data/
```

### 1. fetch_data

**Input**: （無）

**Output**:

- `data/raw/tainan_villages.geojson` — 里界圖層（過濾 6700 開頭）
- `data/raw/tainan_libraries.csv` — 圖書館清單（name, address, lat, lon, district）

**做法**：先嘗試自動下載，失敗時印出手動下載步驟與連結。

資料來源（在 fetch_data 階段才實際確認 URL 並寫入程式碼，避免本文件 URL 過時誤導）：

- **里界**：政府資料開放平台 [data.gov.tw](https://data.gov.tw/) 搜尋「村里界圖」（內政部國土測繪中心），或 內政部 SEGIS [segis.moi.gov.tw](https://segis.moi.gov.tw/) 下載「村里界圖（WGS84）」
- **圖書館**：
  - 主要：臺南市政府資料開放平台 [data.tainan.gov.tw](https://data.tainan.gov.tw/) 搜尋「圖書館」
  - 備援：臺南市立圖書館官網 [tnml.tn.edu.tw](https://www.tnml.tn.edu.tw/) 各館頁面爬取

地理編碼後備方案：如果開放資料沒有經緯度，用地址透過 Nominatim（OpenStreetMap 免費 geocoding）查詢。

### 2. compute_times

**Input**:

- `data/raw/tainan_villages.geojson`
- `data/raw/tainan_libraries.csv`

**Output**:

- `data/processed/village_to_nearest_library.csv` — 欄位：`village_id, village_name, district, centroid_lat, centroid_lon, nearest_library, library_lat, library_lon, distance_km, drive_minutes, method`

**做法**：

1. 計算每個里的質心（EPSG:3826 平面座標下取 centroid，再轉回 WGS84）
2. 對每個里質心，計算到所有圖書館的距離
3. 取最短的那座為「最近圖書館」
4. 計算行車時間（method 欄位記錄 `haversine_30kmh` 或 `osrm`）

**v1 (haversine)**：`distance_km / 30 * 60` 分鐘

**v2 (OSRM)**：先用 haversine 取最近 3 座候選，再呼叫 OSRM 路徑 API 取最小行車時間（節省 API 呼叫量）

OSRM rate limiting：sleep ~200ms between requests（友善對待公開 server），預估 750 × 3 = 2250 次呼叫，最壞情況下可能跑數小時。**必須**用 `tqdm` 顯示進度條與預估剩餘時間。

**斷點續跑**：每處理完 N=50 個里就把結果 append 寫入 `data/processed/osrm_progress.csv`，重跑時讀取已完成部分跳過。長時間任務一定要可中斷續跑，不然 OSRM 跑到一半失敗等於白做。

### 3. visualize

**Input**: `data/processed/village_to_nearest_library.csv` + 里界 GeoJSON

**Output**:

- `output/maps/tainan_library_time_static.png` — matplotlib 靜態地圖
- `output/maps/tainan_library_time_interactive.html` — folium 互動地圖

**色階設計**（參考 example.png 風格，離散分箱）：

| 分鐘  | 顏色            |
| ----- | --------------- |
| 0–5   | 深綠 `#1a9641`  |
| 5–10  | 淺綠 `#a6d96a`  |
| 10–15 | 黃 `#ffffbf`    |
| 15–20 | 橙 `#fdae61`    |
| 20–30 | 紅 `#d7191c`    |
| 30+   | 暗紅 `#7a0177`  |

**靜態圖**：里界填色 + 圖書館位置以黑色十字標示 + 區界較粗線條 + 圖例 + 標題。

**互動圖**：folium choropleth，hover 顯示「里名 / 區名 / 最近館 / 預估時間」；圖書館用 marker 標出，點擊看名稱。

### 4. export

**Input**: `data/processed/village_to_nearest_library.csv`

**Output**:

- `output/data/tainan_library_drive_time.csv`
- `output/data/tainan_library_drive_time.xlsx`（含「資料」與「圖書館清單」兩個 sheet）

## 專案結構

```text
draw-dis-to-lib/
├── goal.md
├── example.png
├── README.md                          # 使用說明（如何安裝 + 跑 notebook 順序）
├── requirements.txt
├── docs/superpowers/specs/
│   └── 2026-05-16-tainan-library-drive-time-map-design.md
├── notebooks/
│   ├── 01_fetch_data.ipynb            # 階段 1：抓資料
│   ├── 02_compute_times.ipynb         # 階段 2：計算時間（v1 haversine / v2 OSRM 切換）
│   ├── 03_visualize.ipynb             # 階段 3：產出 PNG + HTML
│   └── 04_export.ipynb                # 階段 4：匯出 CSV + Excel
├── lib/                               # 共用 utility（避免 notebook 重複貼程式碼）
│   ├── __init__.py
│   ├── geo.py                         # haversine, centroid 計算
│   ├── osrm.py                        # OSRM client + 斷點續跑邏輯
│   └── colors.py                      # 色階分箱
├── data/
│   ├── raw/                           # gitignore
│   └── processed/                     # gitignore（含 osrm_progress.csv 續跑檔）
└── output/
    ├── maps/                          # PNG + HTML
    └── data/                          # CSV + Excel
```

**為什麼拆成 4 個 notebook 而不是 1 個**：

- 階段間透過 `data/processed/` 檔案介接，下游 notebook 可獨立重跑
- 階段 2（OSRM）可能跑數小時，跟其他階段分開比較不會誤觸 Run All
- 純函數（haversine、色階）抽到 `lib/` 才能寫 pytest 單元測試

## 錯誤處理

- **資料下載失敗**：印出清楚的手動下載步驟（含 URL + 預期存放路徑），不要 silent fail
- **Geocoding 失敗**：記錄哪些地址查不到，跳過該圖書館並警告
- **OSRM 呼叫失敗**：fallback 到 haversine，但在 method 欄位標記 `osrm_failed_fallback`，方便事後檢查
- **質心落在水域 / 範圍外**：少數里可能因形狀奇特導致質心不在範圍內，使用 `representative_point()` 替代 centroid

## 測試策略

由於這是資料管線專案、主要邏輯是與外部資料源互動，採取以下方式：

- **單元測試**：純函數（haversine 計算、時間轉換、色階分箱）有 pytest 測試
- **整合測試**：用一小組假資料（5 個里、3 座圖書館）跑完整管線，檢查輸出檔案存在且格式正確
- **手動驗證**：跑完後人眼檢查 PNG 圖（顏色分布是否合理、有沒有破洞）+ 抽 5 個里看 CSV 數值

## 開放問題（v2 時再決定）

- OSRM 公開 server 是否穩定到能跑完 ~2000 次請求？如果常 timeout，可能要改為：
  - (a) 用 Docker 自架 OSRM
  - (b) 改用 OpenRouteService（每日 2000 次免費額度，剛好可能夠）
  - (c) 換 Valhalla 或其他

## Success Criteria

- [ ] 依序執行 4 個 notebook 可從零產出三種輸出
- [ ] 靜態 PNG 視覺風格接近 example.png（離散色階、區界清晰、可辨識區位）
- [ ] 互動 HTML 可在瀏覽器打開，hover 任一里能看到正確資料
- [ ] CSV/Excel 欄位完整、可被 Excel 直接開啟（中文不亂碼）
- [ ] v1（haversine）跑完不超過 30 秒
- [ ] v2（OSRM）在 6 小時內跑完，期間有清楚的進度條（已處理 X/Y、預估剩餘時間）
- [ ] v2 中斷後重跑可從上次斷點繼續，不需要從頭開始
- [ ] 結果通過人眼合理性檢查（市區里時間短、偏遠山區里時間長）
