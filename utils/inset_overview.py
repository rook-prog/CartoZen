# === utils/inset_overview.py ===
# Figure-level inset with robust country/continent boxing, dateline safety,
# and a small status channel back to the caller via fig._cz_inset_used/_cz_inset_reason

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle

from shapely.geometry import Point
from shapely.prepared import prep
import os


def _anchor_offsets(inset_pos: str):
    pos = inset_pos.lower()
    if pos == "top left":
        return 0.02, 0.98, "tl"
    if pos == "bottom left":
        return 0.02, 0.02, "bl"
    if pos == "bottom right":
        return 0.98, 0.02, "br"
    return 0.98, 0.98, "tr"  # default top-right


def _ci_get(d: dict, key: str, default=None):
    if isinstance(d, dict) and key in d:
        return d[key]
    lk = key.lower()
    if isinstance(d, dict):
        for k, v in d.items():
            if k.lower() == lk:
                return v
    return default


def _to_set_extent_box_from_shapely(bounds_tuple):
    """Convert Shapely bounds (minx, miny, maxx, maxy) → (min_lon, max_lon, min_lat, max_lat)."""
    minx, miny, maxx, maxy = bounds_tuple
    return (minx, maxx, miny, maxy)


def _normalize_longitudes(min_lon, max_lon):
    """Normalize to [-180,180] and handle dateline. Returns (min_lon, max_lon)."""
    def wrap(x):
        while x < -180:
            x += 360
        while x > 180:
            x -= 360
        return x

    a = wrap(min_lon)
    b = wrap(max_lon)
    span_direct = b - a
    if span_direct < 0:
        span_direct += 360
    if span_direct > 340:  # absurdly wide → fallback to global
        return -180, 180
    if a > b:
        a, b = b, a
    return a, b


def _country_and_continent_boxes(bounds, ne_countries_path=None, country_hint=None):
    """Return (country_box, continent_box, continent_name) in set_extent order
    for the AOI centroid. Boxes are (min_lon, max_lon, min_lat, max_lat).
    If `ne_countries_path` (zip or folder) is provided and readable, prefer it; otherwise
    fall back to Cartopy's Natural Earth cache (admin_0_countries)."""
    try:
        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0
        pt = Point(cx, cy)

        records = []
        # 1) Prefer local NE 10m zip if available (via GeoPandas/Fiona VFS)
        if ne_countries_path and os.path.exists(ne_countries_path):
            import geopandas as gpd
            vfs_path = ne_countries_path
            gdf = gpd.read_file(f"zip://{vfs_path}") if vfs_path.lower().endswith('.zip') else gpd.read_file(vfs_path)
            # Normalize continent field name
            cont_col = None
            for cand in ["CONTINENT", "continent", "Continent"]:
                if cand in gdf.columns:
                    cont_col = cand; break
            for row in gdf.itertuples(index=False):
                attrs = {"CONTINENT": getattr(row, cont_col) if cont_col else None}
                records.append((row.geometry, attrs))
        else:
            # 2) Fallback to Cartopy NE cache (110m)
            from cartopy.io import shapereader as shpreader
            shp = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
            reader = shpreader.Reader(shp)
            for r in reader.records():
                a = r.attributes if hasattr(r, 'attributes') else getattr(r, '__dict__', {})
                records.append((r.geometry, a))

        # Robust hit selection
        # Optional AOI rectangle for offshore/coastal ranking
        from shapely.geometry import box as _box
        aoi_box_geom = _box(bounds[0], bounds[2], bounds[1], bounds[3])

        # Optional: country name hint prefilter (ADMIN/NAME fields in NE 10m)
        def _name_of(attrs):
            for k in ("ADMIN","NAME","SOVEREIGNT","BRK_NAME","NAME_LONG","NAME_EN","ADMIN_EN"):
                v = _ci_get(attrs, k)
                if v:
                    return str(v)
            return None

        if country_hint:
            cand = []
            for g,a in records:
                nm = _name_of(a)
                if nm and country_hint.lower() in nm.lower():
                    cand.append((g,a))
            if cand:
                records = cand

        # --- Ranking / selection ---
        # 0) direct contains of AOI centroid
        hit_geom = hit_attrs = None
        hit_geom = hit_attrs = None
        for g, a in records:
            if g is None:
                continue
            try:
                if prep(g).contains(pt):
                    hit_geom, hit_attrs = g, a; break
            except Exception:
                continue
        # 1) intersects AOI rectangle (helps when centroid is offshore)
        if hit_geom is None:
            for g, a in records:
                if g is None: continue
                try:
                    if g.intersects(aoi_box_geom):
                        hit_geom, hit_attrs = g, a; break
                except Exception:
                    continue
        if hit_geom is None:
            # 2) intersects tiny centroid buffer (legacy path)
            pbuf = pt.buffer(1e-6)
            for g, a in records:
                if g is None: continue
                try:
                    if g.intersects(pbuf):
                        hit_geom, hit_attrs = g, a; break
                except Exception:
                    continue
        if hit_geom is None:
            # 3) bbox contains centroid (coarse)
            for g, a in records:
                try:
                    mnx, mny, mxx, mxy = g.bounds
                    if mnx <= cx <= mxx and mny <= cy <= mxy:
                        hit_geom, hit_attrs = g, a; break
                except Exception:
                    continue
        if hit_geom is None:
            # 4) nearest by distance to AOI rectangle (better for coastal AOIs)
            best = (1e18, None, None)
            for g, a in records:
                if g is None: continue
                try:
                    d = g.distance(aoi_box_geom)
                    if d < best[0]:
                        best = (d, g, a)
                except Exception:
                    continue
            _, hit_geom, hit_attrs = best
        if hit_geom is None:
            best = (1e18, None, None)
            for g, a in records:
                if g is None: continue
                try:
                    d = g.distance(pt)
                    if d < best[0]:
                        best = (d, g, a)
                except Exception:
                    continue
            _, hit_geom, hit_attrs = best

        if hit_geom is None:
            return None, None, None

        # Country box
        try:
            cb = _to_set_extent_box_from_shapely(hit_geom.bounds)
        except Exception:
            cb = None

        # Continent aggregation
        cont_name = _ci_get(hit_attrs, 'CONTINENT', None) or _ci_get(hit_attrs, 'continent', None)
        cont_box = None
        if cont_name is not None:
            xs_min, xs_max, ys_min, ys_max = [], [], [], []
            for g, a in records:
                if _ci_get(a, 'CONTINENT', _ci_get(a, 'continent')) == cont_name and g is not None:
                    try:
                        mnx, mny, mxx, mxy = g.bounds
                        xs_min.append(mnx); xs_max.append(mxx)
                        ys_min.append(mny); ys_max.append(mxy)
                    except Exception:
                        pass
            if xs_min:
                cont_box = (min(xs_min), max(xs_max), min(ys_min), max(ys_max))

        # Dateline-safe normalization
        if cb is not None:
            a, b = _normalize_longitudes(cb[0], cb[1]); cb = (a, b, cb[2], cb[3])
        if cont_box is not None:
            a, b = _normalize_longitudes(cont_box[0], cont_box[1]); cont_box = (a, b, cont_box[2], cont_box[3])

        return cb, cont_box, cont_name
    except Exception:
        return None, None, None

        # Country box in set_extent order
        try:
            cb = _to_set_extent_box_from_shapely(hit.geometry.bounds)
        except Exception:
            cb = None

        # Continent aggregation
        attrs = hit.attributes if hasattr(hit, "attributes") else getattr(hit, "__dict__", {})
        cont_name = _ci_get(attrs, "CONTINENT", None) or _ci_get(attrs, "continent", None)

        cont_box = None
        if cont_name is not None:
            xs_min, xs_max, ys_min, ys_max = [], [], [], []
            for r in recs:
                a = r.attributes if hasattr(r, "attributes") else getattr(r, "__dict__", {})
                if _ci_get(a, "CONTINENT", _ci_get(a, "continent")) == cont_name:
                    try:
                        mnx, mny, mxx, mxy = r.geometry.bounds
                        xs_min.append(mnx)
                        xs_max.append(mxx)
                        ys_min.append(mny)
                        ys_max.append(mxy)
                    except Exception:
                        pass
            if xs_min:
                cont_box = (min(xs_min), max(xs_max), min(ys_min), max(ys_max))

        # Dateline-safe normalization
        if cb is not None:
            a, b = _normalize_longitudes(cb[0], cb[1])
            cb = (a, b, cb[2], cb[3])
        if cont_box is not None:
            a, b = _normalize_longitudes(cont_box[0], cont_box[1])
            cont_box = (a, b, cont_box[2], cont_box[3])

        return cb, cont_box, cont_name
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
    overlay_edge_color="#0000ff",
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    aoi_fill_alpha=0.0,
    extent_mode="global",
    extent_pad_deg=3.0,
    inset_frame=True,
    inset_frame_lw=0.8,
    ne_countries_path=None,
    country_hint=None,
):
    ax_main,
    bounds,
    overlay_path=None,
    plot_overlay=True,
    inset_pos="top right",
    inset_size_pct=20,
    aoi_edge_color="#ff0000",
    overlay_edge_color="#0000ff",
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    aoi_fill_alpha=0.0,
    extent_mode="global",
    extent_pad_deg=3.0,
    inset_frame=True,
    inset_frame_lw=0.8,
    ne_countries_path=None,
):
    fig = ax_main.figure
    # Status channel: default to requested mode; may be overwritten below
    fig._cz_inset_used = extent_mode
    fig._cz_inset_reason = "ok"

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

    # Extent selection
    def _pad_box(box):
        mnx, mxx, mny, mxy = box
        return (mnx - extent_pad_deg, mxx + extent_pad_deg, mny - extent_pad_deg, mxy + extent_pad_deg)

    set_global = True
    try:
        if extent_mode == "aoi":
            aoi_box = (bounds[0], bounds[1], bounds[2], bounds[3])
            ax_inset.set_extent(_pad_box(aoi_box), crs=ccrs.PlateCarree())
            set_global = False
        elif extent_mode in ("country", "continent"):
            cbox, cont_box, _ = _country_and_continent_boxes(bounds, ne_countries_path=ne_countries_path, country_hint=country_hint)
            if extent_mode == "country" and cbox is not None:
                ax_inset.set_extent(_pad_box(cbox), crs=ccrs.PlateCarree())
                set_global = False
            elif extent_mode == "continent" and cont_box is not None:
                ax_inset.set_extent(_pad_box(cont_box), crs=ccrs.PlateCarree())
                set_global = False
            else:
                fig._cz_inset_used = "global"
                fig._cz_inset_reason = "Natural Earth lookup failed (no match)"
    except Exception:
        fig._cz_inset_used = "global"
        fig._cz_inset_reason = "Natural Earth shapefile unavailable or read error"
        set_global = True

    if set_global:
        ax_inset.set_global()

    # Optional overlay
    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=overlay_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=100
            )
        except Exception:
            pass

    # AOI rectangle
    min_lon, max_lon, min_lat, max_lat = bounds
    base_lw = 1.2
    lw = max(base_lw, 0.8 * (40.0 / max(10.0, float(inset_size_pct))))
    rect = Rectangle(
        (min_lon, min_lat),
        width=(max_lon - min_lon),
        height=(max_lat - min_lat),
        linewidth=lw,
        edgecolor=aoi_edge_color,
        facecolor=(aoi_edge_color if aoi_fill_alpha > 0 else "none"),
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
        ax_inset.set_xticks([])
        ax_inset.set_yticks([])
    except Exception:
        pass

    return ax_inset

