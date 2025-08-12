# CartoZen v1.0.0 — Station Map Generator (Stable)

**Released:** 2025-08-12
![CartoZen Logo](assets/logo_small.png)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.16814346.svg)](https://doi.org/10.5281/zenodo.16814346)

CartoZen turns your station table into a polished map—fast. It combines **Streamlit** + **Matplotlib/Cartopy** for a dependable, offline‑friendly mapping tool.

## ✨ Highlights
- **Inset overview**: global / AOI / country / continent (uses local Natural Earth zip if available).
- **Independent colours**: AOI rectangle vs inset overlay.
- **Dateline‑safe**: robust longitude normalization and multiple hit tests (contains → intersects → bbox → nearest).
- **Safe exports**: avoids `bbox_inches="tight"` whenever any inset exists, to keep full page frames.
- **Clipped elements**: legend, scale bar, north arrow, watermark are all `clip_on=True` to the map axes.
- **Declutter & Cluster**: greedy distance clustering with counts; optional local mini‑insets around large clusters with advanced styling.
- **Coordinate handling**: DD/DMS/UTM parsing with cleaning; UTM converts via zone/hemisphere.

## 📦 Requirements
- Python **3.10+**
- Core: `streamlit`, `matplotlib`, `cartopy`, `shapely`, `geopandas`, `fiona`, `pyproj`, `pandas`, `numpy`, `Pillow`
- Optional: `adjustText` (improves label declutter)
- Data (optional but recommended): `assets/ne_10m_admin_0_countries.zip` for country/continent extent logic

## 🚀 Quick start
```bash
# create & activate a virtual env (example)
python -m venv .venv && source .venv/bin/activate

# install deps
pip install -r requirements.txt  # or install the packages listed above

# run
streamlit run app.py
```

## 📑 Usage
See **USAGE.md** for detailed, field‑tested steps and tips.

## 🔧 File layout (key files)
- `app.py` – Streamlit app (merged build: advanced insets + cluster + safe export)
- `utils/` – helpers: coordinate conversion, overview insets, clustering, declutter, overlay loading, plotting helpers
- `assets/` – optional Natural Earth admin layer zip (`ne_10m_admin_0_countries.zip`)

## 🧩 Data expectations
Provide latitude/longitude columns (DD or DMS) or UTM columns (E, N, Zone, Hemisphere letter). The app auto‑detects sensible column names (`lat`, `lon`, `x`, `y`, etc.).

## 📝 Changelog
See **changelog.md** — first stable: v1.0.0 (2025-08-12).

## ⚠️ Known issues
See **KNOWN_ISSUES.md** for current caveats and suggested workarounds.

## 🙏 Credits
- Natural Earth data (public domain)
- Cartopy/Matplotlib/Shapely/GeoPandas communities
