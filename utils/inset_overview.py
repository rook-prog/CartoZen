# utils/inset_overview.py (re-patched: figure-level inset, robust country/continent)
# Draw a reliable inset overview WITHOUT affecting main axes layout.
# Adds robust country/continent extent detection (case-insensitive attrs,
# point-in-poly fallback strategies) and optional frame.

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle

from shapely.geometry import Point
from shapely.ops import nearest_points
from shapely.prepared import prep


def _anchor_offsets(inset_pos: str):
    # offsets in [0..1] within the main axes bbox
    pos = inset_pos.lower()
    if pos == "top left":
        return 0.02, 0.98, "tl"
    if pos == "bottom left":
        return 0.02, 0.02, "bl"
    if pos == "bottom right":
        return 0.98, 0.02, "br"
    # default
    return 0.98, 0.98, "tr"


def _ci_get(d: dict, key: str, default=None):
    """Case-insensitive dict getter (returns first matching key's value)."""
    if key in d:
        return d[key]
    lk = key.lower()
    for k, v in d.items():
        if k.lower() == lk:
            return v
    return default


def _country_and_continent_bbox(bounds):
    """Return (country_bounds, continent_bounds, continent_name) for AOI centroid.
    Uses Natural Earth admin_0 countries, robust to case of field names and
    geometry issues. Returns None entries if lookup fails.
    """
    try:
        from cartopy.io import shapereader as shpreader
        shp = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
        reader = shpreader.Reader(shp)
        recs = list(reader.records())
        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0
        pt = Point(cx, cy)

        # 1) try strict contains with prepared geoms
        hit = None
        for r in recs:
            geom = r.geometry
            if geom is None:
                continue
            try:
                if prep(geom).contains(pt):
                    hit = r
                    break
            except Exception:
                # Shapely may error on invalid polys; ignore
                continue

        # 2) if none found, try intersects on small buffer (handles edge cases)
        if hit is None:
            pbuf = pt.buffer(1e-6)
            for r in recs:
                geom = r.geometry
                if geom is None:
                    continue
                try:
                    if geom.intersects(pbuf):
                        hit = r
                        break
                except Exception:
                    continue

        # 3) still none: choose country with bbox containing pt, else nearest
        if hit is None:
            candidates = []
            for r in recs:
                try:
                    mnx, mny, mxx, mxy = r.geometry.bounds
                    if mnx <= cx <= mxx and mny <= cy <= mxy:
                        candidates.append(r)
                except Exception:
                    continue
            if candidates:
                hit = candidates[0]
            else:
                # nearest by polygon distance
                best = (1e18, None)
                for r in recs:
                    g = r.geometry
                    if g is None:
                        continue
                    try:
                        d = g.distance(pt)
                        if d < best[0]:
                            best = (d, r)
                    except Exception:
                        continue
                hit = best[1]

        if hit is None:
            return None, None, None

        # Country bounds
        try:
            cb = hit.geometry.bounds  # (minx, miny, maxx, maxy)
        except Exception:
            cb = None

        # Continent name (case-insensitive)
        attrs = hit.attributes if hasattr(hit, 'attributes') else hit.__dict__
        cont_name = _ci_get(attrs, 'CONTINENT', None)
        if cont_name is None:
            cont_name = _ci_get(attrs, 'continent', None)

        # Aggregate bounds for that continent
        cont_bounds = None
        if cont_name is not None:
            bxs = []
            for r in recs:
                a = r.attributes if hasattr(r, 'attributes') else r.__dict__
                if _ci_get(a, 'CONTINENT', _ci_get(a, 'continent')) == cont_name:
                    try:
                        bxs.append(r.geometry.bounds)
                    except Exception:
                        pass
            if bxs:
                mnx = min(b[0] for b in bxs); mny = min(b[1] for b in bxs)
                mxx = max(b[2] for b in bxs); mxy = max(b[3] for b in bxs)
                cont_bounds = (mnx, mxx, mny, mxy)

        return cb, cont_bounds, cont_name
    except Exception:
        return None, None, None


def draw_inset_overview(
    ax_main,
    bounds,
    overlay_path=None,
    plot_overlay=True,
    inset_pos="top right",
    inset_size_pct=20,
    aoi_edge_color="#ff0000",
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    aoi_fill_alpha=0.0,
    extent_mode="global",        # "global" | "aoi" | "country" | "continent"
    extent_pad_deg=3.0,           # padding for aoi/country/continent extents
    inset_frame=True,
    inset_frame_lw=0.8,
):
    """Figure-level inset that does not change main axes layout."""
    fig = ax_main.figure
    main_box = ax_main.get_position()  # in figure coordinates

    # Size of inset in figure coords (percentage of main axes size)
    frac = max(10, min(40, int(inset_size_pct))) / 100.0
    inset_w = main_box.width * frac
    inset_h = main_box.height * frac

    # Anchor corner within main axes bbox
    axx, axy, corner = _anchor_offsets(inset_pos)

    # Convert anchor (relative in [0..1]) to figure coords
    if corner == "tr":
        left = main_box.x0 + axx * main_box.width - inset_w
        bottom = main_box.y0 + axy * main_box.height - inset_h
    elif corner == "tl":
        left = main_box.x0 + axx * main_box.width
        bottom = main_box.y0 + axy * main_box.height - inset_h
    elif corner == "bl":
        left = main_box.x0 + axx * main_box.width
        bottom = main_box.y0 + axy * main_box.height
    else:  # br
        left = main_box.x0 + axx * main_box.width - inset_w
        bottom = main_box.y0 + axy * main_box.height

    # Clamp inside figure bounds a bit (safety margin)
    left = max(0.0, min(1.0 - inset_w, left))
    bottom = max(0.0, min(1.0 - inset_h, bottom))

    # Create as FIGURE-LEVEL axes (decoupled from main axes layout)
    ax_inset = fig.add_axes([left, bottom, inset_w, inset_h], projection=ccrs.PlateCarree())

    # Keep inset out of tight layout and bring on top
    try:
        ax_inset.set_in_layout(False)
    except Exception:
        pass
    ax_inset.set_zorder(99)
    ax_inset.patch.set_alpha(1.0)

    # Basemap
    ax_inset.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
    ax_inset.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
    ax_inset.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)

    # ----- Extent logic ------------------------------------------------------
    def _pad_box(b):
        mnx, mxx, mny, mxy = b
        return (mnx - extent_pad_deg, mxx + extent_pad_deg, mny - extent_pad_deg, mxy + extent_pad_deg)

    set_global = True
    try:
        if extent_mode == "aoi":
            ax_inset.set_extent(_pad_box((bounds[0], bounds[1], bounds[2], bounds[3])), crs=ccrs.PlateCarree())
            set_global = False
        elif extent_mode in ("country", "continent"):
            cb, contb, _ = _country_and_continent_bbox(bounds)
            if extent_mode == "country" and cb is not None:
                ax_inset.set_extent(_pad_box((cb[0], cb[2], cb[1], cb[3])), crs=ccrs.PlateCarree())
                set_global = False
            elif extent_mode == "continent" and contb is not None:
                ax_inset.set_extent(_pad_box((contb[0], contb[1], contb[2], contb[3])), crs=ccrs.PlateCarree())
                set_global = False
    except Exception:
        set_global = True

    if set_global:
        ax_inset.set_global()

    # Optional overlay
    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=aoi_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=100
            )
        except Exception:
            pass

    # AOI rectangle (scaled linewidth)
    min_lon, max_lon, min_lat, max_lat = bounds
    aoi_w = max_lon - min_lon
    aoi_h = max_lat - min_lat
    base_lw = 1.2
    lw = max(base_lw, 0.8 * (40.0 / max(10.0, float(inset_size_pct))))

    rect = Rectangle(
        (min_lon, min_lat),
        width=aoi_w,
        height=aoi_h,
        linewidth=lw,
        edgecolor=aoi_edge_color,
        facecolor=(aoi_edge_color if aoi_fill_alpha > 0 else 'none'),
        alpha=aoi_fill_alpha if aoi_fill_alpha > 0 else 1.0,
        transform=ccrs.PlateCarree(),
        zorder=101,
    )
    ax_inset.add_patch(rect)

    # Frame styling
    try:
        if inset_frame:
            for spine in ax_inset.spines.values():
                spine.set_visible(True)
                spine.set_linewidth(inset_frame_lw)
        else:
            for spine in ax_inset.spines.values():
                spine.set_visible(False)
        ax_inset.set_xticks([]); ax_inset.set_yticks([])
    except Exception:
        pass

    return ax_inset
