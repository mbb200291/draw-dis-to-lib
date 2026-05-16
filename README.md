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
