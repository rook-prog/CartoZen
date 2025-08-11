# utils/inset_overview.py (re-patched: figure-level inset)
# Draw a reliable inset overview WITHOUT affecting main axes layout.
# Key changes:
# - Create inset as a FIGURE-LEVEL axes (fig.add_axes in figure coords),
#   positioned within the main axes bbox. This prevents main map shrink.
# - Keep inset out of tight-layout math (set_in_layout(False)).
# - Dynamic AOI visibility and optional overlay as before.

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle


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
    extent_mode="global",        # NEW: "global" | "aoi" | "country" | "continent"
    extent_pad_deg=3.0,           # padding for aoi/country/continent extents
    inset_frame=True,             # NEW: show/hide frame
    inset_frame_lw=0.8,           # NEW: frame linewidth
):
    """Figure-level inset that does not change main axes layout.

    Parameters
    ----------
    extent_mode : str
        "global" (world), "aoi" (bounds+padded), "country" (country bbox),
        or "continent" (continent bbox). Falls back gracefully on errors.
    inset_frame : bool
        Whether to draw a frame around the inset.
    inset_frame_lw : float
        Frame line width.
    """
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
    def _pad(b):
        mnx, mxx, mny, mxy = b
        return (mnx - extent_pad_deg, mxx + extent_pad_deg, mny - extent_pad_deg, mxy + extent_pad_deg)

    set_global = True
    try:
        if extent_mode == "aoi":
            # AOI (bounds) view with padding
            ax_inset.set_extent(_pad((bounds[0], bounds[1], bounds[2], bounds[3])), crs=ccrs.PlateCarree())
            set_global = False
        elif extent_mode in ("country", "continent"):
            from cartopy.io import shapereader as shpreader
            from shapely.geometry import Point
            shp = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
            recs = list(shpreader.Reader(shp).records())
            # AOI centroid
            cx = (bounds[0] + bounds[1]) / 2.0
            cy = (bounds[2] + bounds[3]) / 2.0
            pt = Point(cx, cy)
            hit = None
            for r in recs:
                try:
                    if r.geometry is not None and r.geometry.contains(pt):
                        hit = r
                        break
                except Exception:
                    continue
            if hit is not None:
                if extent_mode == "country":
                    mnx, mny, mxx, mxy = hit.geometry.bounds
                    ax_inset.set_extent(_pad((mnx, mxx, mny, mxy)), crs=ccrs.PlateCarree())
                    set_global = False
                else:  # continent
                    cont = hit.attributes.get('CONTINENT')
                    if cont:
                        bxs = []
                        for r in recs:
                            if r.attributes.get('CONTINENT') == cont and r.geometry is not None:
                                try:
                                    bxs.append(r.geometry.bounds)
                                except Exception:
                                    pass
                        if bxs:
                            mnx = min(b[0] for b in bxs); mny = min(b[1] for b in bxs)
                            mxx = max(b[2] for b in bxs); mxy = max(b[3] for b in bxs)
                            ax_inset.set_extent(_pad((mnx, mxx, mny, mxy)), crs=ccrs.PlateCarree())
                            set_global = False
    except Exception:
        # Any failure falls back to global
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
