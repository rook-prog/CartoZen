# CartoZen v1.1.0 — Station Map Generator (Stable)

**Released:** 2025-08-17  
![CartoZen Logo](assets/logo_small.png)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.16814346.svg)](https://doi.org/10.5281/zenodo.16814346)

CartoZen turns your station table into a polished map—fast. It combines **Streamlit** + **Matplotlib/Cartopy** for a dependable, offline-friendly mapping tool.

## ✨ Highlights
- **Inset overview**: global / AOI / country / continent (uses local Natural Earth zip if available).
- **Independent colours**: AOI rectangle vs inset overlay.
- **Dateline-safe**: robust longitude normalization and multiple hit tests.
- **Safe exports**: avoids `bbox_inches="tight"` whenever any inset exists.
- **Clipped elements**: legend, scale bar, north arrow, watermark are all clipped to map axes.
- **Declutter & Cluster**: greedy distance clustering with counts; optional local mini-insets.
- **Coordinate handling**: DD/DMS/UTM parsing with cleaning.
- **New in 1.1.0**:
  - Number inputs for buffer, grid interval, offsets, scale-bar length/thickness, inset padding, cluster offset fraction.
  - Marker border/halo styling.
  - North arrow halo/border.
  - Bold legend headers.
  - Custom text overlay (position, style, halo, box).
  - Scroll-fit preview (no vertical scrolling).

## 📦 Requirements
- Python **3.10+**
- Core: `streamlit`, `matplotlib`, `cartopy`, `shapely`, `geopandas`, `fiona`, `pyproj`, `pandas`, `numpy`, `Pillow`
- Optional: `adjustText` (improves label declutter)
- Data (optional but recommended): `assets/ne_10m_admin_0_countries.zip`

## 🚀 Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 📑 Usage
See **USAGE.md** for detailed steps.

## 🔧 File layout
- `app.py` – Streamlit app (stable v1.1.0)
- `utils/` – helpers: coordinates, insets, clustering, declutter, overlay loading
- `assets/` – optional Natural Earth admin zip

## 🧩 Data expectations
Provide latitude/longitude columns (DD or DMS) or UTM columns. App auto-detects common column names.

## 📝 Changelog
See **changelog.md** — current v1.1.0, earlier v1.0.0.

## ⚠️ Known issues
See **KNOWN_ISSUES.md**.

## 🙏 Credits
- Natural Earth (public domain)
- Cartopy/Matplotlib/Shapely/GeoPandas communities
