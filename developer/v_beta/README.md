# ≡ƒù║∩╕Å CartoZen Beta ΓÇô Interactive Station Map Generator

![CartoZen Logo](assets/logo_small.png)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.16566366.svg)](https://doi.org/10.5281/zenodo.16566366)

**CartoZen** is a lightweight, modular, and interactive map generator that helps you create high-quality station maps from geospatial data files like CSV or Excel.

Whether you're a researcher, student, educator, or content creator ΓÇö CartoZen offers an intuitive interface to plot latitude-longitude data over styled maps with complete layout control.

---

## ≡ƒÜª Beta Release Notice

This is the **first public release** of CartoZen (Beta), currently available for **trial and testing**.  
We welcome feedback, bug reports, and suggestions for improving the app before the stable version.

> ≡ƒöÆ Internal dev version: `v3.3`  
> ≡ƒîÉ Public beta tag: `v0.9.1 Beta`

---

## Γ£¿ Features

- ≡ƒôî **Upload station data** (CSV or XLSX with lat/lon columns)
- ≡ƒù║∩╕Å Generate map using **Cartopy + Matplotlib** backend
- ≡ƒôÉ Customize **page size** and **orientation**
- ≡ƒº¡ Show **coordinate labels on all 4 sides** (top, bottom, left, right)
- ≡ƒÄ¿ Set **land and ocean colors** using color pickers
- ≡ƒöó Avoid overlapping ticks with **manual/auto toggle**
- ≡ƒº╛ Margins respected using `subplots_adjust`

---

## ≡ƒôé Project Structure

```
cartozen/
Γö£ΓöÇΓöÇ app.py # Main Streamlit app
Γö£ΓöÇΓöÇ utils/
Γöé Γö£ΓöÇΓöÇ config.py # Settings and constants
Γöé Γö£ΓöÇΓöÇ coord_utils.py # DMS to DD converter functions
Γöé Γö£ΓöÇΓöÇ overlay_loader.py # Overlay file support (future)
Γöé ΓööΓöÇΓöÇ plot_helpers.py # Map rendering utilities
Γö£ΓöÇΓöÇ assets/
Γöé ΓööΓöÇΓöÇ logo.png # App logo or banner image
Γö£ΓöÇΓöÇ requirements.txt # Python dependencies
Γö£ΓöÇΓöÇ LICENSE # BSD 3-Clause license
ΓööΓöÇΓöÇ USAGE.md # Fair use and citation policy
```

---

## ΓÜÖ∩╕Å Installation

Ensure Python 3.9+ is installed.

```bash
# Clone the repository
git clone https://github.com/rook-prog/CartoZen.git
cd CartoZen

# Install dependencies
pip install -r requirements.txt
```

---

## Γû╢∩╕Å Run the App

```bash
streamlit run app.py
```

Steps:
1. Upload your CSV/Excel file with `Latitude` and `Longitude`
2. Adjust colors, layout, margins, and orientation
3. View map output (download/export support coming soon)

---

## ≡ƒôî Planned Features

| Feature                   | Status    |
|---------------------------|-----------|
| PDF export support        | ≡ƒöä Planned |
| Style preset saving       | ≡ƒöä Planned |
| GeoJSON/AOI overlay       | ≡ƒöä Planned |
| Attribute-based legends   | ≡ƒöä Planned |

---

## ≡ƒôú Contribute or Report Issues

We're in beta!  
Please report bugs or suggest features via [GitHub Issues](https://github.com/rook-prog/CartoZen/issues).

---

## ≡ƒô£ License and Usage

This project is licensed under the **BSD 3-Clause License**.  
Please also review the [Fair Use and Citation Policy](USAGE.md) before using or modifying CartoZen.

> For citation:  
> **Srijith B. (2025). CartoZen: An Interactive Station Map Generator. GitHub: https://github.com/rook-prog/CartoZen**

---

_Developed with Γ¥ñ∩╕Å by [Srijith B](https://github.com/rook-prog)_
