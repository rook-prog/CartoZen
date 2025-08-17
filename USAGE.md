# USAGE — CartoZen v1.1.0

## 1) Data upload
- Upload **CSV** or **XLSX**.
- Choose **Coord format**: `DMS`, `Decimal Degrees`, or `UTM`.
- Enable **Auto-fit extent** (default) or set a fixed **Buffer (°)** via numeric input.

## 2) Overlay
- Upload a **zip/GeoJSON/KML** overlay.
- Toggle **Show overlay** and pick a colour.
- The overlay is reprojected to `EPSG:4326` automatically.

## 3) Map Colors
- Pick **Land** and **Water** colours (defaults: warm land, cool water).

## 4) Marker
- Shape, colour, size.
- Labels: toggle on/off and tweak **lon/lat offsets (° float)**.
- **New:** optional marker border (colour/width) and halo (colour/width).

## 5) Grid & Axis
- Toggle **Grid** on/off. When off, the app still places **outer ticks/labels** so you keep axis context without interior gridlines.
- **Interval (°)** is now a free numeric input (float).
- **Label format**: `Decimal` or `DMS`.

## 6) Elements + Fonts
- **Legend**: position + bold headers.
- **Scale bar**: length, segments, thickness, position, units (length/thickness as integer inputs).
- **North arrow**: position, colour, size. **New:** halo/border controls.

## 7) Inset overview
- Toggle **Show inset**.
- **Inset pos** and **Inset size (%)**.
- **Inset extent**: `global` / `aoi` / `country` / `continent`.
  - Country/continent lookups prefer local **Natural Earth** zip at `assets/ne_10m_admin_0_countries.zip` (fallback: Cartopy cache).
- Optional: draw your **Overlay** inside the inset and set independent colours.
- Frame visibility and width.
- **New:** **Extent padding (° float)**.

## 8) Declutter & Cluster
- **Avoid label overlap**: uses `adjustText` when installed, otherwise a light fallback.
- **Cluster nearby stations**: greedy single-linkage by distance (km); renders **counts** on map when >1.
- **Local insets for largest clusters**: choose how many; set **anchor**, **offset fraction**, **size (%)**, **marker size**.
- Advanced mini-inset styling: **frame width**, **connector colour/width**, **inset label colour/size/halo**, **label offset (px)**, **align**.
- **New:** **Inset offset fraction (float)**.

## 9) Custom text (new)
- Insert arbitrary text on map.
- Options: position (axes fraction), font size, colour, bold/italic, rotation, box, halo.

## 10) Export
- Choose **PNG/JPEG**, **DPI**, **Page size** and **Orientation**.
- **Export guard**: if *any* inset exists, the app **does not** use tight bounding boxes to preserve the full page frame.
- **Preview** auto-fits viewport height (no vertical scrolling).

---

## Tips & Troubleshooting
- **Columns not detected** → rename or use common aliases (e.g., `lat`, `latitude`, `y`; `lon`, `longitude`, `x`).  
- **Country/continent shows global** → ensure the Natural Earth zip exists at `assets/ne_10m_admin_0_countries.zip` **or** that Cartopy’s data cache is accessible.  
- **Cluster counts KeyError** → when showing counts, pull a representative label from `clusters[cid][0]` only if you’re not printing counts.  
- **Declutter quality** → install `adjustText` for best results; fallback is basic but fast.
