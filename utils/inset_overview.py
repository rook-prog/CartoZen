# utils/inset_overview.py (figure-level inset, separate AOI and overlay colors)
# Draw inset overview with independent colors for AOI rectangle and overlay.

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle
from shapely.geometry import Point
from shapely.prepared import prep

def _anchor_offsets(inset_pos: str):
    pos = inset_pos.lower()
    if pos == "top left":
        return 0.02, 0.98, "tl"
    if pos == "bottom left":
        return 0.02, 0.02, "bl"
    if pos == "bottom right":
        return 0.98, 0.02, "br"
    return 0.98, 0.98, "tr"

def _ci_get(d: dict, key: str, default=None):
    if key in d:
        return d[key]
    lk = key.lower()
    for k, v in d.items():
        if k.lower() == lk:
            return v
    return default

def _country_and_continent_bbox(bounds):
    try:
        from cartopy.io import shapereader as shpreader
        shp = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
        recs = list(shpreader.Reader(shp).records())
        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0
        pt = Point(cx, cy)
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
                continue
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
        if hit is None:
            return None, None, None
        cb = hit.geometry.bounds if hit.geometry else None
        cont_name = _ci_get(hit.attributes, 'CONTINENT', _ci_get(hit.attributes, 'continent'))
        cont_bounds = None
        if cont_name:
            bxs = [r.geometry.bounds for r in recs if _ci_get(r.attributes, 'CONTINENT', _ci_get(r.attributes, 'continent')) == cont_name]
            if bxs:
                mnx = min(b[0] for b in bxs)
                mny = min(b[1] for b in bxs)
                mxx = max(b[2] for b in bxs)
                mxy = max(b[3] for b in bxs)
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
    aoi_edge_color="#ff0000",       # AOI rectangle colour
    overlay_edge_color="#0000ff",   # NEW: overlay outline colour (independent)
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    aoi_fill_alpha=0.0,
    extent_mode="global",        # "global" | "aoi" | "country" | "continent"
    extent_pad_deg=3.0,           # padding for aoi/country/continent extents
    inset_frame=True,
    inset_frame_lw=0.8,
):
    fig = ax_main.figure
    main_box = ax_main.get_position()
    frac = max(10, min(40, int(inset_size_pct))) / 100.0
    inset_w = main_box.width * frac
    inset_h = main_box.height * frac
    axx, axy, corner = _anchor_offsets(inset_pos)
    if corner == "tr":
        left = main_box.x0 + axx * main_box.width - inset_w
        bottom = main_box.y0 + axy * main_box.height - inset_h
    elif corner == "tl":
        left = main_box.x0 + axx * main_box.width
        bottom = main_box.y0 + axy * main_box.height - inset_h
    elif corner == "bl":
        left = main_box.x0 + axx * main_box.width
        bottom = main_box.y0 + axy * main_box.height
    else:
        left = main_box.x0 + axx * main_box.width - inset_w
        bottom = main_box.y0 + axy * main_box.height
    left = max(0.0, min(1.0 - inset_w, left))
    bottom = max(0.0, min(1.0 - inset_h, bottom))
    ax_inset = fig.add_axes([left, bottom, inset_w, inset_h], projection=ccrs.PlateCarree())
    try:
        ax_inset.set_in_layout(False)
    except Exception:
        pass
    ax_inset.set_zorder(99)
    ax_inset.patch.set_alpha(1.0)
    ax_inset.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
    ax_inset.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
    ax_inset.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)
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
    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=overlay_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=100
            )
        except Exception:
            pass
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
        edgecolor=overlay_edge_color,
        facecolor=(aoi_edge_color if aoi_fill_alpha > 0 else 'none'),
        alpha=aoi_fill_alpha if aoi_fill_alpha > 0 else 1.0,
        transform=ccrs.PlateCarree(),
        zorder=101,
    )
    ax_inset.add_patch(rect)
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
