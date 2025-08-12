# USAGE — CartoZen v1.0.0

## 1) Data upload
- Upload **CSV** or **XLSX**.
- Choose **Coord format**: `DMS`, `Decimal Degrees`, or `UTM`.
- Enable **Auto-fit extent** (default) or choose a fixed buffer (°).

> Tip: The converter cleans commas as decimals, trims spaces, and handles loose tokenised DMS. UTM expects columns `[E, N, Z, ZL]` (hemisphere letter).

## 2) Overlay
- Upload a **zip/GeoJSON/KML** overlay.
- Toggle **Show overlay** and pick a colour.
- The overlay is reprojected to `EPSG:4326` automatically.

## 3) Map Colors
- Pick **Land** and **Water** colours (defaults: warm land, cool water).

## 4) Marker
- Shape, colour, size.
- Labels: toggle on/off and tweak **lon/lat offsets (°)** for placement.

## 5) Grid & Axis
- Toggle **Grid** on/off. When off, the app still places **outer ticks/labels** so you keep axis context without interior gridlines.
- Set **Interval (°)**, colour, style, and linewidth.
- **Label format**: `Decimal` or `DMS`.
- *(Optional in some builds)* **Latitude direction**: Ascending (default) or Descending.

## 6) Elements + Fonts
- **Legend**: position + text size.
- **Scale bar**: length, segments, thickness, position, units.
- **North arrow**: position, colour, size.
- All text elements are clipped to the map axes to avoid bleed during export.

## 7) Inset overview
- Toggle **Show inset**.
- **Inset pos** and **Inset size (%)**.
- **Inset extent**: `global` / `aoi` / `country` / `continent`.
  - Country/continent lookups prefer local **Natural Earth** zip at `assets/ne_10m_admin_0_countries.zip` (fallback: Cartopy cache).
- Optional: draw your **Overlay** inside the inset and set independent colours.
- Frame visibility and width.

## 8) Declutter & Cluster
- **Avoid label overlap**: uses `adjustText` when installed, otherwise a light fallback.
- **Cluster nearby stations**: greedy single‑linkage by distance (km); renders **counts** on map when >1.
- **Local insets for largest clusters**: choose how many; set **anchor**, **offset fraction**, **size (%)**, **marker size**.
- Advanced mini‑inset styling: **frame width**, **connector colour/width**, **inset label colour/size/halo**, **label offset (px)**, **align**.

## 9) Export
- Choose **PNG/JPEG**, **DPI**, **Page size** and **Orientation**.
- **Export guard**: if *any* inset exists (global or local), the app **does not** use tight bounding boxes to preserve the full page frame.

---

## Tips & Troubleshooting
- **Columns not detected** → rename or use common aliases (e.g., `lat`, `latitude`, `y`; `lon`, `longitude`, `x`).  
- **Country/continent shows global** → ensure the Natural Earth zip exists at `assets/ne_10m_admin_0_countries.zip` **or** that Cartopy’s data cache is accessible.  
- **Cluster counts KeyError** → when showing counts, pull a representative label from `clusters[cid][0]` only if you’re not printing counts.  
- **Declutter quality** → install `adjustText` for best results; fallback is basic but fast.

