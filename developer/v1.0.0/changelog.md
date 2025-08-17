# Changelog — CartoZen

All notable changes will be documented in this file.

## v1.0.0 — 2025-08-12 — First stable
**Added**
- Inset overview with robust extent modes: global, aoi, country, continent (uses local Natural Earth zip when present).
- Safe export behaviour: skips `bbox_inches="tight"` when any inset exists to preserve page frames.
- Elements (legend, scale bar, north arrow) are clipped to map axes in merged build.
- Declutter & Cluster: greedy distance clustering with counts; local mini‑insets near large clusters with advanced styling and connectors.
- Safe extent helper to clamp extents and enforce non‑zero spans (main map and insets).

**Improved**
- Dateline‑safe longitudes and multiple hit tests (contains → intersects → bbox → nearest) for country/continent detection.
- Overlay pipeline with auto‑reprojection to `EPSG:4326`.

**Notes**
- This release promotes the long‑running beta into a **stable** baseline. Experimental font styling was removed to prioritise stability.

---

### Earlier (beta) work
Multiple beta iterations occurred prior to 2025-08-12; see repository history for granular changes.
