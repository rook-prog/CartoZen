# CartoZen

CartoZen is a lightweight, Streamlit-based map generator for station datasets. It focuses on **sane defaults**, **robust coordinate handling**, and **production-friendly exports** without GIS bloat.

## What it is
- A single-page app to drop in your tabular data (CSV/XLSX) and export polished maps.
- Designed for **field/ops teams** as well as analysts—minimal clicks, clear results.

## Current release
- **v1.1.0 — 2025-08-17** is a minor feature release building on the first stable (v1.0.0).
- Stability preserved; UI extended with new numeric inputs and styling controls.
- Experimental table legend deferred to v2.0.0 for simplicity.

## Core capabilities
- **Inset overview** with extent modes: *global*, *aoi*, *country*, *continent* (uses local Natural Earth zip when present).
- **Main map elements** (legend, scale bar, north arrow) render reliably and are **clipped to the map axes**.
- **Export guard**: when any inset exists, we **avoid tight bbox** to preserve full page framing.
- **Safe extents** everywhere to prevent zero-width/height or out-of-bounds views.
- **Declutter & Cluster**: greedy distance clustering, optional local cluster insets near big clusters, and configurable styling.
- **Coordinate ingestion**: Decimal Degrees, DMS, and UTM with resilient parsing and cleaning.
- **New in 1.1.0**: numeric inputs for buffer/offsets, marker and north arrow halos, bold legend headers, custom text insertion, scroll-fit preview.

See **USAGE.md** for step-by-step instructions and **KNOWN_ISSUES.md** for current caveats.
