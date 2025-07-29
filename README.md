# 🗺️ CartoZen Beta – Interactive Station Map Generator

![CartoZen Logo](assets/logo_small.png)

**CartoZen** is a lightweight, modular, and interactive map generator that helps you create high-quality station maps from geospatial data files like CSV or Excel.

Whether you're a researcher, student, educator, or content creator — CartoZen offers an intuitive interface to plot latitude-longitude data over styled maps with complete layout control.

---

## 🚦 Beta Release Notice

This is the **first public release** of CartoZen (Beta), currently available for **trial and testing**.  
We welcome feedback, bug reports, and suggestions for improving the app before the stable version.

> 🔒 Internal dev version: `v3.2`  
> 🌐 Public beta tag: `vBeta-2025.07`

---

## ✨ Features

- 📌 **Upload station data** (CSV or XLSX with lat/lon columns)
- 🗺️ Generate map using **Cartopy + Matplotlib** backend
- 📐 Customize **page size** and **orientation**
- 🧭 Show **coordinate labels on all 4 sides** (top, bottom, left, right)
- 🎨 Set **land and ocean colors** using color pickers
- 🔢 Avoid overlapping ticks with **manual/auto toggle**
- 🧾 Margins respected using `subplots_adjust`

---

## 📂 Project Structure

```
cartozen/
├── app.py # Main Streamlit app
├── utils/
│ ├── config.py # Settings and constants
│ ├── coord_utils.py # DMS to DD converter functions
│ ├── overlay_loader.py # Overlay file support (future)
│ └── plot_helpers.py # Map rendering utilities
├── assets/
│ └── logo.png # App logo or banner image
├── requirements.txt # Python dependencies
├── LICENSE # BSD 3-Clause license
└── USAGE.md # Fair use and citation policy
```

---

## ⚙️ Installation

Ensure Python 3.9+ is installed.

```bash
# Clone the repository
git clone https://github.com/rook-prog/CartoZen.git
cd CartoZen

# Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Run the App

```bash
streamlit run app.py
```

Steps:
1. Upload your CSV/Excel file with `Latitude` and `Longitude`
2. Adjust colors, layout, margins, and orientation
3. View map output (download/export support coming soon)

---

## 📌 Planned Features

| Feature                   | Status    |
|---------------------------|-----------|
| PDF export support        | 🔄 Planned |
| Style preset saving       | 🔄 Planned |
| GeoJSON/AOI overlay       | 🔄 Planned |
| Attribute-based legends   | 🔄 Planned |

---

## 📣 Contribute or Report Issues

We're in beta!  
Please report bugs or suggest features via [GitHub Issues](https://github.com/rook-prog/CartoZen/issues).

---

## 📜 License and Usage

This project is licensed under the **BSD 3-Clause License**.  
Please also review the [Fair Use and Citation Policy](USAGE.md) before using or modifying CartoZen.

> For citation:  
> **Srijith B. (2025). CartoZen: An Interactive Station Map Generator. GitHub: https://github.com/rook-prog/CartoZen**

---

_Developed with ❤️ by [Srijith B](https://github.com/rook-prog)_
