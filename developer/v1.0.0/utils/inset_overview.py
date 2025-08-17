# utils/inset_overview.py — Safe-extent + robust country/continent + color wiring
# Ensures inset extents never go out of PlateCarree bounds and avoids wrap issues.

import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle
from shapely.geometry import Point, box as _box
from shapely.prepared import prep


# ── helpers ─────────────────────────────────────────────────────────────────

def _safe_extent(b):
    """Clamp (min_lon, max_lon, min_lat, max_lat) to valid PlateCarree range
    and guarantee a non-zero span so Cartopy never explodes/crops."""
    lo, hi, la, lb = map(float, b)
    lo = max(-179.999, min(179.999, lo))
    hi = max(-179.999, min(179.999, hi))
    la = max(-89.9,   min(89.9,   la))
    lb = max(-89.9,   min(89.9,   lb))
    if hi <= lo: hi = lo + 0.01
    if lb <= la: lb = la + 0.01
    return (lo, hi, la, lb)


def _anchor_offsets(pos: str):
    p = pos.lower()
    return {
        "top left": (0.02, 0.98, "tl"),
        "bottom left": (0.02, 0.02, "bl"),
        "bottom right": (0.98, 0.02, "br"),
    }.get(p, (0.98, 0.98, "tr"))


def _ci_get(d: dict, key: str, default=None):
    if isinstance(d, dict) and key in d:
        return d[key]
    lk = key.lower()
    if isinstance(d, dict):
        for k, v in d.items():
            if k.lower() == lk:
                return v
    return default


def _to_set_extent_box_from_shapely(b):
    minx, miny, maxx, maxy = b
    return (minx, maxx, miny, maxy)


def _normalize_longitudes(a, b):
    def wrap(x):
        while x < -180: x += 360
        while x > 180: x -= 360
        return x
    a, b = wrap(a), wrap(b)
    span = b - a
    if span < 0: span += 360
    if span > 340: return -180, 180
    if a > b: a, b = b, a
    return a, b


def _country_and_continent_boxes(bounds, ne_countries_path=None, country_hint=None):
    """Return (country_box, continent_box, continent_name) in set_extent order.
    Uses local NE zip if provided, else Cartopy cache; robust to offshore AOIs.
    """
    cx = (bounds[0] + bounds[1]) / 2.0
    cy = (bounds[2] + bounds[3]) / 2.0
    pt = Point(cx, cy)
    aoi_box_geom = _box(bounds[0], bounds[2], bounds[1], bounds[3])

    records = []
    try:
        if ne_countries_path and os.path.exists(ne_countries_path):
            import geopandas as gpd
            gdf = gpd.read_file(f"zip://{ne_countries_path}") if ne_countries_path.lower().endswith(".zip") else gpd.read_file(ne_countries_path)
            cont_col = next((c for c in ["CONTINENT","continent","Continent"] if c in gdf.columns), None)
            name_col = next((c for c in ["ADMIN","NAME","SOVEREIGNT","BRK_NAME","NAME_LONG","NAME_EN","ADMIN_EN"] if c in gdf.columns), None)
            for row in gdf.itertuples(index=False):
                attrs = {"CONTINENT": getattr(row, cont_col) if cont_col else None}
                if name_col: attrs[name_col] = getattr(row, name_col)
                records.append((row.geometry, attrs))
        else:
            from cartopy.io import shapereader as shpreader
            shp = shpreader.natural_earth("110m", "cultural", "admin_0_countries")
            reader = shpreader.Reader(shp)
            for r in reader.records():
                a = r.attributes if hasattr(r, "attributes") else getattr(r, "__dict__", {})
                records.append((r.geometry, a))
    except Exception:
        records = []

    def _name_of(attrs):
        for k in ("ADMIN","NAME","SOVEREIGNT","BRK_NAME","NAME_LONG","NAME_EN","ADMIN_EN"):
            v = _ci_get(attrs, k)
            if v: return str(v)
        return None

    if country_hint:
        filt = [(g,a) for (g,a) in records if (nm:=_name_of(a)) and country_hint.lower() in nm.lower()]
        if filt: records = filt

    hit_g = hit_a = None
    for g,a in records:
        if g is None: continue
        try:
            if prep(g).contains(pt): hit_g, hit_a = g, a; break
        except Exception: pass
    if hit_g is None:
        for g,a in records:
            try:
                if g is not None and g.intersects(aoi_box_geom): hit_g, hit_a = g, a; break
            except Exception: pass
    if hit_g is None:
        pbuf = pt.buffer(1e-6)
        for g,a in records:
            try:
                if g is not None and g.intersects(pbuf): hit_g, hit_a = g, a; break
            except Exception: pass
    if hit_g is None:
        for g,a in records:
            try:
                mnx,mny,mxx,mxy = g.bounds
                if mnx <= cx <= mxx and mny <= cy <= mxy: hit_g, hit_a = g, a; break
            except Exception: pass
    if hit_g is None:
        best = (1e18, None, None)
        for g,a in records:
            try:
                if g is None: continue
                d = g.distance(aoi_box_geom)
                if d < best[0]: best = (d, g, a)
            except Exception: pass
        _, hit_g, hit_a = best

    if hit_g is None:
        return None, None, None

    try:
        cb = _to_set_extent_box_from_shapely(hit_g.bounds)
    except Exception:
        cb = None

    cont_name = _ci_get(hit_a, "CONTINENT", None) or _ci_get(hit_a, "continent", None)
    cont_box = None
    if cont_name is not None:
        xs_min, xs_max, ys_min, ys_max = [], [], [], []
        for g,a in records:
            if _ci_get(a, "CONTINENT", _ci_get(a, "continent")) == cont_name and g is not None:
                try:
                    mnx,mny,mxx,mxy = g.bounds
                    xs_min.append(mnx); xs_max.append(mxx)
                    ys_min.append(mny); ys_max.append(mxy)
                except Exception: pass
        if xs_min:
            cont_box = (min(xs_min), max(xs_max), min(ys_min), max(ys_max))

    if cb is not None:
        a,b = _normalize_longitudes(cb[0], cb[1]); cb = (a,b,cb[2],cb[3])
    if cont_box is not None:
        a,b = _normalize_longitudes(cont_box[0], cont_box[1]); cont_box = (a,b,cont_box[2],cont_box[3])

    return cb, cont_box, cont_name


# ── main API ─────────────────────────────────────────────────────────────────

def draw_inset_overview(
    ax_main,
    bounds,
    overlay_path=None,
    plot_overlay=True,
    inset_pos="top right",
    inset_size_pct=20,
    aoi_edge_color="#ff0000",       # AOI rectangle
    overlay_edge_color="#0000ff",   # overlay outline inside inset
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    aoi_fill_alpha=0.0,
    extent_mode="global",           # global | aoi | country | continent
    extent_pad_deg=3.0,
    inset_frame=True,
    inset_frame_lw=0.8,
    ne_countries_path=None,
    country_hint=None,
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
    else:  # br
        left = main_box.x0 + axx * main_box.width - inset_w
        bottom = main_box.y0 + axy * main_box.height

    left = max(0.0, min(1.0 - inset_w, left))
    bottom = max(0.0, min(1.0 - inset_h, bottom))

    ax_inset = fig.add_axes([left, bottom, inset_w, inset_h], projection=ccrs.PlateCarree())
    try: ax_inset.set_in_layout(False)
    except Exception: pass
    ax_inset.set_zorder(99)
    ax_inset.patch.set_alpha(1.0)

    ax_inset.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
    ax_inset.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
    ax_inset.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)

    def _pad(box):
        mnx, mxx, mny, mxy = box
        return (mnx - extent_pad_deg, mxx + extent_pad_deg, mny - extent_pad_deg, mxy + extent_pad_deg)

    set_global = True
    try:
        if extent_mode == "aoi":
            ax_inset.set_extent(_safe_extent(_pad((bounds[0], bounds[1], bounds[2], bounds[3]))), crs=ccrs.PlateCarree())
            set_global = False
        elif extent_mode in ("country", "continent"):
            cbox, cont_box, _ = _country_and_continent_boxes(bounds, ne_countries_path, country_hint)
            if extent_mode == "country" and cbox is not None:
                ax_inset.set_extent(_safe_extent(_pad(cbox)), crs=ccrs.PlateCarree()); set_global = False
            elif extent_mode == "continent" and cont_box is not None:
                ax_inset.set_extent(_safe_extent(_pad(cont_box)), crs=ccrs.PlateCarree()); set_global = False
    except Exception:
        set_global = True

    if set_global:
        ax_inset.set_global()

    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=overlay_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=100,
            )
        except Exception:
            pass

    # AOI rectangle
    min_lon, max_lon, min_lat, max_lat = bounds
    base_lw = 1.2
    lw = max(base_lw, 0.8 * (40.0 / max(10.0, float(inset_size_pct))))
    rect = Rectangle((min_lon, min_lat), max_lon-min_lon, max_lat-min_lat,
                     linewidth=lw, edgecolor=aoi_edge_color,
                     facecolor=(aoi_edge_color if aoi_fill_alpha > 0 else "none"),
                     alpha=aoi_fill_alpha if aoi_fill_alpha > 0 else 1.0,
                     transform=ccrs.PlateCarree(), zorder=101)
    ax_inset.add_patch(rect)

    try:
        for s in ax_inset.spines.values():
            s.set_visible(bool(inset_frame)); s.set_linewidth(inset_frame_lw)
        ax_inset.set_xticks([]); ax_inset.set_yticks([])
    except Exception:
        pass

    return ax_inset
