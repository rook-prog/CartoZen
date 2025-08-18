# app.py — CartoZen (Merged):
# - Inset fixes (country/continent AOI), independent colors
# - Declutter + Greedy Cluster
# - Local cluster insets (anchors, label style, connector)
# - Safe extents + clipped elements + robust export
# Requires utils/
#   inset_overview.py (latest safe-extent version)
#   cluster_utils.py, label_declutter.py, local_inset_clusters.py (advanced)
#   coord_utils_v2.py, overlay_loader.py, plot_helpers.py, config.py

from PIL import Image
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import numpy as np
import tempfile, os, base64
from matplotlib import ticker as mticker

from utils.coord_utils_v2 import convert_coords, get_buffered_extent
from utils.overlay_loader import overlay_gdf
from utils.plot_helpers import dd_fmt_lon, dd_fmt_lat, dms_fmt_lon, dms_fmt_lat, draw_scale_bar
from utils.config import shape_map, get_page_size
from utils.inset_overview import draw_inset_overview
from utils.cluster_utils import greedy_cluster
from utils.label_declutter import declutter_texts
from utils.local_inset_clusters import draw_cluster_insets

NE_COUNTRIES_ZIP = "assets/ne_10m_admin_0_countries.zip"
logo = "assets/logo.png"

def _icon():
    try:
        # Use a small transparent PNG (ideally 32×32 or 64×64)
        return Image.open("assets/carozen_icon.png")
    except Exception:
        return "🗺️"  # fallback emoji

st.set_page_config(page_title="CartoZen v1.1.0", page_icon=_icon(), layout="wide")

# ── helpers ─────────────────────────────────────────────────────────────────

def _find_col(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _safe_extent(b):
    lo, hi, la, lb = map(float, b)
    lo = max(-179.999, min(179.999, lo))
    hi = max(-179.999, min(179.999, hi))
    la = max(-89.9,   min(89.9,   la))
    lb = max(-89.9,   min(89.9,   lb))
    if hi <= lo: hi = lo + 0.01
    if lb <= la: lb = la + 0.01
    return (lo, hi, la, lb)

# ── UI ──────────────────────────────────────────────────────────────────────
view = st.selectbox("View", ["Map", "About", "Changelog"])
left, right = st.columns([2,6], vertical_alignment="center")

with left:
    # show at native size to avoid blur (64 px)
    st.image(logo, width=400)

with right:
    st.title("CartoZen – Station Map Generator v1.1.0 (stable)")
    st.markdown("Upload your station data and generate custom maps easily.")
    #if Path(BANNER_HI).exists():
        #st.image(BANNER_HI, width=220)  # large but sharp because source is hi-re

if view == "Map":
    with st.sidebar:
        st.header("**⚙️ Controls**")
        with st.expander("**Data upload**", expanded=False):
            up_file = st.file_uploader("CSV / XLSX", ["csv","xlsx"])
            coord_fmt = st.selectbox("Coord format", ["DMS","Decimal Degrees","UTM"])
            auto_ext = st.checkbox("Auto-fit extent", True)
            margin = st.slider("Margin %", 1, 30, 10)
        buffer_deg = 5
        if not auto_ext:
            buffer_deg = st.number_input("Buffer around data (°)", min_value=0, max_value=60, value=5, step=1)
        with st.expander("**Overlay**", expanded=False):
            ov_file = st.file_uploader("zip / GeoJSON / KML", ["zip","geojson","kml"])
            show_ov = st.checkbox("Show overlay", True)
            ov_main_color = st.color_picker("Main overlay colour", "#0000ff")
        with st.expander("**Map Colors**", expanded=False):
            land_col = st.color_picker("Land color", "#f0e8d8")
            ocean_col = st.color_picker("Water color", "#cce6ff")
        with st.expander("**Marker**", expanded=False):
            shape = st.selectbox("Shape", list(shape_map.keys()))
            m_col = st.color_picker("Colour", "#00cc44")
            m_size = st.slider("Size", 5, 20, 10)
            m_edge_on  = st.checkbox("Marker border", True)
            m_edge_col = st.color_picker("Marker border colour", "#000000") if m_edge_on else "#000000"
            m_edge_w   = st.number_input("Marker border width", min_value=0.0, max_value=10.0, value=0.8, step=0.1)
            m_halo_on  = st.checkbox("Marker halo (outer stroke)", False)
            m_halo_col = st.color_picker("Halo colour", "#FFFFFF") if m_halo_on else "#FFFFFF"
            m_halo_w   = st.number_input("Halo width", min_value=0.0, max_value=10.0, value=2.0, step=0.1) if m_halo_on else 0.0
            show_lab = st.checkbox("Show labels", True)
            dx = dy = 0.0
            if show_lab:
                dx = st.number_input("Label offset °lon (float)", value=0.01, step=0.01, format="%.2f")
                dy = st.number_input("Label offset °lat (float)", value=0.05, step=0.01, format="%.2f")

        with st.expander("**Grid & Axis**", expanded=False):
            grid_on = st.checkbox("Grid", False)
            g_int = st.number_input("Interval ° (float)", min_value=0.01, max_value=30.0, value=1.00, step=0.01, format="%.2f")
            g_col = st.color_picker("Grid colour", "#666666")
            g_style = st.selectbox("Style", ["solid","dashed","dotted"])
            g_wid = st.slider("Line width", 0.5, 2.5, 1.0, 0.1)
            axis_fmt = st.radio("Label format", ["Decimal","DMS"])
        with st.expander("**Elements**", expanded=False):
            leg_on = st.checkbox("Legend", True)
            leg_pos = st.selectbox("Legend pos", ["upper left","upper right","lower left","lower right","center left","center right"]) 
            #leg_table = st.checkbox("Legend as table (align columns)", False)
            sb_on = st.checkbox("Scale-bar", True)
            sb_len = st.number_input("Bar length (integer)", min_value=1, max_value=2000, value=50, step=1)
            sb_seg = st.slider("Segments", 2, 5, 3)
            sb_thk = st.number_input("Bar thickness (integer)", min_value=1, max_value=100, value=3, step=1)
            sb_pos = st.selectbox("Bar pos", ["Bottom-Left","Bottom-Right","Top-Left","Top-Right"]) 
            sb_unit = st.selectbox("Units", ["km","miles"]) 
            na_on = st.checkbox("North arrow", True)
            na_pos = st.selectbox("North pos", ["Top-Right","Top-Left","Bottom-Right","Bottom-Left"]) 
            na_col = st.color_picker("North colour", "#000000")
            na_halo_on  = st.checkbox("North label halo", True)
            na_halo_col = st.color_picker("North halo colour", "#FFFFFF") if na_halo_on else "#FFFFFF"
            na_halo_w   = st.number_input("North halo width", min_value=0.0, max_value=10.0, value=2.5, step=0.1) if na_halo_on else 0.0
            na_arrow_halo_on  = st.checkbox("North arrow halo", True)
            na_arrow_halo_col = st.color_picker("Arrow halo colour", "#FFFFFF") if na_arrow_halo_on else "#FFFFFF"
            na_arrow_halo_w   = st.number_input("Arrow halo width", min_value=0.0, max_value=10.0, value=2.5, step=0.1) if na_arrow_halo_on else 0.0

        with st.expander("**Inset overview**", expanded=False):
            inset_on = st.checkbox("Show inset", False)
            inset_pos = st.selectbox("Inset pos", ["top right","top left","bottom right","bottom left"], index=0)
            inset_size = st.slider("Inset size (%)", 10, 40, 20)
            extent_mode = st.selectbox("Inset extent", ["global","aoi","country","continent"], index=0)
            extent_pad = st.number_input("Inset extent padding (°)", min_value=0.0, max_value=20.0, value=3.0, step=0.1, format="%.1f")
            inset_rect_color = st.color_picker("AOI rectangle colour", "#ff0000")
            inset_ov = st.checkbox("Plot overlay in inset", True)
            inset_ov_color = st.color_picker("Inset overlay colour", "#0000ff")
            frame_on = st.checkbox("Inset frame", True)
            frame_lw = st.slider("Inset frame width", 0.5, 3.0, 0.8, 0.1)
        with st.expander("**Declutter & Cluster**", expanded=False):
            declutter_on = st.checkbox("Avoid label overlap (repel)", False)
            cluster_on = st.checkbox("Cluster nearby stations", False)
            cluster_km = st.slider("Cluster distance (km)", 1, 50, 12)
            show_cluster_counts = st.checkbox("Show cluster counts on map", True)
            local_insets = st.checkbox("Local insets for largest clusters", False)
            max_insets = st.slider("Number of local insets", 0, 3, 2)
            # Advanced local-inset formatting & placement
            cluster_anchor = st.selectbox(
                "Cluster inset anchor",
                [
                    "top left","top center","top right",
                    "center left","center","center right",
                    "bottom left","bottom center","bottom right",
                ],
                index=2,
            )
            conn_color = st.color_picker("Connector colour", "#444444")
            conn_lw    = st.slider("Connector thickness", 0.3, 3.0, 0.8, 0.1)
            inset_label_color = st.color_picker("Inset label colour", "#6a5acd")
            inset_label_halo  = st.checkbox("Inset label halo", True)
            inset_label_halo_w= st.slider("Inset label halo width", 0.5, 4.0, 2.5, 0.1)
            inset_label_align = st.selectbox("Inset label align", ["left","center","right"], index=0)
            inset_lbl_dx = st.slider("Inset label offset X (px)", -30, 30, 6)
            inset_lbl_dy = st.slider("Inset label offset Y (px)", -30, 30, 4)
            # Cluster inset sizing
            cluster_inset_size_pct = st.slider("Cluster inset size (%)", 10, 40, 18)
            cluster_marker_size    = st.slider("Inset marker size", 6, 36, 16)
            _default_inset_lbl = max(6, min(20, int(st.session_state.get("Labels", 8) * 0.8)))
            cluster_label_size     = st.slider("Inset label size", 6, 20, _default_inset_lbl, key="cluster_label_size")
            cluster_frame_lw       = st.slider("Inset frame width", 0.3, 3.0, 0.6, 0.1)
            cluster_offset_frac = st.number_input("Inset offset fraction", min_value=0.000, max_value=0.200, value=0.012, step=0.001, format="%.3f")
        with st.expander("**Custom text**", expanded=False):
            custom_on   = st.checkbox("Add custom text", False)
            custom_txt  = st.text_area("Text", "Your title or notes here") if custom_on else ""
            custom_x    = st.number_input("X position (axes fraction)", min_value=0.0, max_value=1.0, value=0.50, step=0.01, format="%.2f") if custom_on else 0.5
            custom_y    = st.number_input("Y position (axes fraction)", min_value=0.0, max_value=1.0, value=0.95, step=0.01, format="%.2f") if custom_on else 0.95
            custom_fs   = st.number_input("Font size", min_value=6, max_value=48, value=16, step=1) if custom_on else 16
            custom_col  = st.color_picker("Text colour", "#000000") if custom_on else "#000000"
            custom_bold = st.checkbox("Bold", True) if custom_on else False
            custom_ital = st.checkbox("Italic", False) if custom_on else False
            custom_rot  = st.number_input("Rotation (°)", min_value=-180, max_value=180, value=0, step=1) if custom_on else 0
            custom_ha   = st.selectbox("Horizontal align", ["left","center","right"], index=1) if custom_on else "center"
            custom_va   = st.selectbox("Vertical align", ["bottom","center","top"], index=2) if custom_on else "top"
            custom_box  = st.checkbox("Background box", False) if custom_on else False
            custom_box_fc = st.color_picker("Box face", "#FFFFFF") if (custom_on and custom_box) else "#FFFFFF"
            custom_box_ec = st.color_picker("Box edge", "#000000") if (custom_on and custom_box) else "#000000"
            custom_box_alpha = st.slider("Box alpha", 0.0, 1.0, 0.8, 0.05) if (custom_on and custom_box) else 0.8
            custom_halo = st.checkbox("Halo", True) if custom_on else False
            custom_halo_w = st.number_input("Halo width", min_value=0.0, max_value=10.0, value=3.0, step=0.5) if (custom_on and custom_halo) else 0.0
            custom_halo_col = st.color_picker("Halo colour", "#FFFFFF") if (custom_on and custom_halo) else "#FFFFFF"

        with st.expander("**Font sizes**", expanded=False):
            axis_f = st.slider("Axis ticks", 6, 16, 8)
            label_f = st.slider("Labels", 6, 16, 8)
            legend_f = st.slider("Legend", 6, 16, 8)
            sb_f = st.slider("Scale-bar", 6, 16, 8)
            north_f = st.slider("North arrow", 10, 30, 18)
        if up_file:
            is_csv = up_file.name.lower().endswith(".csv")
            df0 = pd.read_csv(up_file) if is_csv else pd.read_excel(up_file)
            df_cols = df0.columns
            with st.expander("**Legend / Label columns**", expanded=False):
                stn = st.selectbox("Station ID", df_cols)
                at = st.selectbox("Attribute", df_cols)
                lab = st.selectbox("Label col", df_cols)
            with st.expander("**Legend header**", expanded=False):
                head1 = st.text_input("Header line 1", value=f"{stn} – {at}")
                head2 = st.text_input("Header line 2 (optional)", value="")
        else:
            stn = at = lab = head1 = head2 = None
        with st.expander("**Export**", expanded=False):
            fmt = st.selectbox("Format", ["PNG","JPEG"]) 
            dpi = st.slider("DPI", 100, 600, 300)
            p_sz = st.selectbox("Page", ["A4","A3","Letter"]) 
            ori = st.selectbox("Orientation", ["Landscape","Portrait"]) 
            full = st.checkbox("Full-width preview", False)

        with st.sidebar:
            st.markdown("### Feedback")
            #st.link_button("❤️ Contribute", "https://ko-fi.com/rookprog")
            st.link_button("💬 Feedback", "https://forms.gle/pF2LAJ76gniiiT2a7")

    if up_file and stn and at and lab:
        # Coordinates
        lat_col = _find_col(df0.columns, ["lat","latitude","lat_dd","y","ycoord","y_coord"])
        lon_col = _find_col(df0.columns, ["lon","long","longitude","lon_dd","x","xcoord","x_coord"])
        if not lat_col or not lon_col:
            st.error("❌ Couldn’t detect latitude/longitude columns."); st.stop()
        try:
            df = convert_coords(df0, coord_fmt, lat_col, lon_col)
        except Exception as e:
            st.error("❌ Coordinate conversion crashed."); st.exception(e); st.stop()
        if df is None or "Lat_DD" not in df.columns or "Lon_DD" not in df.columns:
            st.error("❌ Converted coordinate columns not found."); st.stop()
        if df["Lat_DD"].isnull().all() or df["Lon_DD"].isnull().all():
            st.error("❌ Coordinate conversion failed."); st.stop()

        # Extent (safe)
        if auto_ext:
            lo, hi = df["Lon_DD"].agg(["min","max"]) ; la, lb = df["Lat_DD"].agg(["min","max"])
            if hi == lo: hi, lo = hi + 0.01, lo - 0.01
            if lb == la: lb, la = lb + 0.01, la - 0.01
            bounds = (
                lo - (hi - lo) * margin / 100.0,
                hi + (hi - lo) * margin / 100.0,
                la - (lb - la) * margin / 100.0,
                lb + (lb - la) * margin / 100.0,
            )
        else:
            bounds = get_buffered_extent(df, buffer_deg)
        bounds = _safe_extent(bounds)

        # Figure
        halo = [pe.withStroke(linewidth=3, foreground="white")]
        fig = plt.figure(figsize=get_page_size(p_sz, ori), dpi=dpi)
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
        ax.set_extent(bounds, crs=ccrs.PlateCarree())
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Base
        ax.add_feature(cfeature.LAND.with_scale("50m"), fc=land_col)
        ax.add_feature(cfeature.OCEAN.with_scale("50m"), fc=ocean_col)
        ax.add_feature(cfeature.BORDERS, ls=":"); ax.add_feature(cfeature.COASTLINE)

        # Grid
        tol = 1e-9
        xt = np.arange(bounds[0], bounds[1] + g_int, g_int)
        yt = np.arange(bounds[2], bounds[3] + g_int, g_int)
        # keep only interior ticks (remove edges)
        xt_in = xt[(xt > bounds[0] + tol) & (xt < bounds[1] - tol)]
        yt_in = yt[(yt > bounds[2] + tol) & (yt < bounds[3] - tol)]
        if grid_on:
            gl = ax.gridlines(draw_labels=True, xlocs=xt, ylocs=yt, color=g_col, ls=g_style, lw=g_wid)
            gl.top_labels = gl.right_labels = True
            gl.xlabel_style = gl.ylabel_style = {"size": axis_f}
            gl.xformatter = (mticker.FuncFormatter(dms_fmt_lon) if axis_fmt=="DMS" else mticker.FuncFormatter(dd_fmt_lon))
            gl.yformatter = (mticker.FuncFormatter(dms_fmt_lat) if axis_fmt=="DMS" else mticker.FuncFormatter(dd_fmt_lat))
        else:                     
            ax.set_xticks(xt_in, crs=ccrs.PlateCarree()); ax.set_yticks(yt_in, crs=ccrs.PlateCarree())
            if axis_fmt == "DMS":
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(dms_fmt_lon))
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(dms_fmt_lat))
            else:
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(dd_fmt_lon))
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(dd_fmt_lat))

            ax.tick_params(
                axis="both", direction="out", length=4, width=g_wid, color=g_col,
                labelsize=axis_f, #bottom=True, top=False, left=True, right=False
            )

        # Overlay on main map
        if ov_file and show_ov:
            try:
                overlay_gdf(ov_file).to_crs("EPSG:4326").plot(ax=ax, edgecolor=ov_main_color, facecolor="none", lw=1)
            except Exception as e:
                st.warning(f"Overlay could not be rendered: {e}")

        # ===== Cluster & Declutter integration =====
        plot_df = df.copy(); clusters = None
        if cluster_on:
            rep_df, clusters = greedy_cluster(df, "Lat_DD", "Lon_DD", float(cluster_km))
            plot_df = rep_df

        # Markers
        # Optional halo stroke (draw first, underneath)
        if m_halo_on and m_halo_w > 0:
            ax.scatter(
                plot_df["Lon_DD"], plot_df["Lat_DD"],
                s=m_size**2, c=m_col, marker=shape_map[shape],
                edgecolors=m_halo_col, linewidths=m_halo_w,
                transform=ccrs.PlateCarree(), zorder=4
            )

        # Main markers (+ optional border)
        edgecols = m_edge_col if m_edge_on and m_edge_w > 0 else "none"
        edgew    = m_edge_w if m_edge_on and m_edge_w > 0 else 0.0

        ax.scatter(
            plot_df["Lon_DD"], plot_df["Lat_DD"],
            s=m_size**2, c=m_col, marker=shape_map[shape],
            edgecolors=edgecols, linewidths=edgew,
            transform=ccrs.PlateCarree(), zorder=5
        )


        # Labels (counts for clusters; label-of-representative otherwise)
        texts = []
        if show_lab:
            if cluster_on and clusters is not None:
                for _, r in plot_df.iterrows():
                    cid  = int(r.get("cluster_id", -1))
                    size = int(r.get("cluster_size", 1))
                    rep_idx = clusters.get(cid, [None])[0]
                    label = str(size) if (size > 1 and show_cluster_counts) else (str(df.iloc[rep_idx][lab]) if rep_idx is not None and lab in df.columns else "")
                    t = ax.text(r["Lon_DD"] + dx, r["Lat_DD"] + dy, label, fontsize=label_f, transform=ccrs.PlateCarree(), path_effects=halo, clip_on=True)
                    texts.append(t)
            else:
                for _, r in plot_df.iterrows():
                    t = ax.text(r["Lon_DD"] + dx, r["Lat_DD"] + dy, str(r[lab]), fontsize=label_f, transform=ccrs.PlateCarree(), path_effects=halo, clip_on=True)
                    texts.append(t)

        # Declutter labels if requested
        if show_lab and declutter_on and texts:
            declutter_texts(ax, texts)

        # Local mini-insets for biggest clusters (adjacent placement + label styles)
        if cluster_on and local_insets and clusters:
            draw_cluster_insets(
                ax, df, clusters,
                max_insets=max_insets, pad_deg=0.2, box_frac=float(cluster_inset_size_pct)/100.0,
                land_color=land_col, ocean_color=ocean_col, marker_color=m_col, marker_size=int(cluster_marker_size),
                show_labels=True, label_col=lab, label_fontsize=int(cluster_label_size),
                label_color=inset_label_color, label_align=inset_label_align,
                label_halo=inset_label_halo, label_halo_width=float(inset_label_halo_w),
                label_offset_px=(inset_lbl_dx, inset_lbl_dy),
                anchor=cluster_anchor, offset_frac=float(cluster_offset_frac),
                frame_lw=float(cluster_frame_lw), link=True, link_color=conn_color, link_lw=float(conn_lw),
            )

        # Global inset overview (figure-level)
        if inset_on:
            draw_inset_overview(
                ax_main=ax, bounds=bounds,
                overlay_path=ov_file if inset_ov else None, plot_overlay=inset_ov,
                inset_pos=inset_pos, inset_size_pct=inset_size,
                aoi_edge_color=inset_rect_color, overlay_edge_color=inset_ov_color,
                land_color=land_col, ocean_color=ocean_col,
                extent_mode=extent_mode, extent_pad_deg=extent_pad,
                inset_frame=frame_on, inset_frame_lw=frame_lw,
                ne_countries_path=NE_COUNTRIES_ZIP,
            )
            
            
        # Legend / Scale / North Arrow (draw after labels, clip to axes)
        if leg_on:
            # Build rows + bold header text
            rows = df[[stn, at]].astype(str).agg(" – ".join, axis=1)
            max_items = 50
            rows = list(rows.head(max_items)) + ([f"... (+{len(df)-max_items} more)"] if len(df) > max_items else [])
            header_lines = [h for h in [head1, head2] if h]
            if header_lines:
                def _mt(s): return s.replace("{","\\{").replace("}","\\}")
                bold_header = "\n".join([rf"$\bf{{{_mt(h)}}}$" for h in header_lines])
                leg_text = "\n".join([bold_header] + rows)
            else:
                leg_text = "\n".join(rows)

            # if leg_table:
            #     # === TABLE LEGEND (aligned columns, no borders, auto width/height) ===
            #     from matplotlib.table import Table
                

            #     # data for table
            #     _df_ = df[[stn, at]].astype(str).head(max_items)
            #     table_data = _df_.values.tolist()

            #     # Robust column headers (avoid duplicates)
            #     def _table_headers(stn, at, head1, head2):
            #         if head2 and head2.strip():
            #             h1 = (head1 or str(stn)).strip()
            #             h2 = (head2 or str(at)).strip()
            #         else:
            #             h1 = h2 = None
            #             if head1:
            #                 for delim in ["–", "-", "|", ",", "/"]:
            #                     if delim in head1:
            #                         p1, p2 = [p.strip() for p in head1.split(delim, 1)]
            #                         if p1 and p2:
            #                             h1, h2 = p1, p2
            #                             break
            #             if not h1 or not h2:
            #                 h1 = str(stn).strip()
            #                 h2 = str(at).strip()
            #         if h1 == h2:
            #             h2 = str(at).strip() if h1 != str(at).strip() else "Value"
            #         return [h1, h2]
                
            #     col_labels = _table_headers(stn, at, head1, head2)
                
            #     # Start with a tiny inset; we will resize and move it after measuring content
            #     tbl_ax = ax.inset_axes([0, 0, 0.01, 0.01], transform=ax.transAxes)
            #     tbl_ax.axis("off")

            #     tbl = tbl_ax.table(
            #         cellText=table_data,
            #         colLabels=col_labels,
            #         loc="upper left",
            #         cellLoc="left",
            #     )
            #     tbl.auto_set_font_size(False)
            #     tbl.set_fontsize(legend_f)
            #     tbl.scale(1.0, 1.2)

            #     try:
            #         tbl.auto_set_column_width(col=list(range(len(col_labels))))
            #     except Exception:
            #         pass
                
            #     # Style: bold header, no borders
            #     for (r, c), cell in tbl.get_celld().items():
            #         if r == 0:
            #             cell.set_text_props(fontweight="bold")
            #             cell.set_facecolor("#f4f4f4")
            #         cell.set_linewidth(0.0)
            #         cell.set_edgecolor((0, 0, 0, 0))

            #     # --- Measure & size ---
            #     fig.canvas.draw()
            #     renderer = fig.canvas.get_renderer()
            #     bb_pix = tbl.get_window_extent(renderer=renderer).expanded(1.05, 1.10)  # padding
            #     ax_w_pix, ax_h_pix = ax.bbox.width, ax.bbox.height
            #     w_frac = min(bb_pix.width  / ax_w_pix, 0.95)
            #     h_frac = min(bb_pix.height / ax_h_pix, 0.95)
                
            #     # --- Positioning by lower-left corner (no anchors) ---
            #     pad = 0.01
            #     if leg_pos == "upper left":
            #         x = pad
            #         y = 1.0 - pad - h_frac
            #     elif leg_pos == "upper right":
            #         x = 1.0 - pad - w_frac
            #         y = 1.0 - pad - h_frac
            #     elif leg_pos == "lower left":
            #         x = pad
            #         y = pad
            #     elif leg_pos == "lower right":
            #         x = 1.0 - pad - w_frac
            #         y = pad
            #     elif leg_pos == "center left":
            #         x = pad
            #         y = 0.5 - h_frac / 2.0
            #     elif leg_pos == "center right":
            #         x = 1.0 - pad - w_frac
            #         y = 0.5 - h_frac / 2.0
            #     else:
            #         # default: upper right
            #         x = 1.0 - pad - w_frac
            #         y = 1.0 - pad - h_frac

            #     # Clamp inside [0,1] just in case
            #     x = max(0.0, min(x, 1.0 - w_frac))
            #     y = max(0.0, min(y, 1.0 - h_frac))
                
            #     tbl_ax.set_position([x, y, w_frac, h_frac], which="active")
            #     tbl_ax.set_clip_on(True)
            #     tbl_ax.set_clip_path(ax.patch)

            # else:
            # === TEXT LEGEND (your original, now correctly separated) ===
            box = dict(boxstyle="round", fc="white", ec="black", alpha=0.8)
            pos_map = {
                "upper left":  (0.01, 0.99),
                "upper right": (0.99, 0.99),
                "lower left":  (0.01, 0.01),
                "lower right": (0.99, 0.01),
                "center left": (0.01, 0.50),
                "center right":(0.99, 0.50),
            }
            xp, yp = pos_map[leg_pos]
            lt = ax.text(
                xp, yp, leg_text, transform=ax.transAxes, fontsize=legend_f,
                ha=("left" if "left" in leg_pos else "right"),
                va=("top"  if "upper" in leg_pos else "bottom" if "lower" in leg_pos else "center"),
                bbox=box
            )
            lt.set_clip_on(True); lt.set_clip_path(ax.patch)

        # Scale-bar
        if sb_on:
            km_len = sb_len if sb_unit == "km" else sb_len * 1.60934
            draw_scale_bar(ax, bounds, km_len, sb_seg, sb_thk, sb_pos, sb_unit, sb_f)

        # North Arrow
        if na_on:
            pos = {"Top-Right": (0.95, 0.95), "Top-Left": (0.05, 0.95), "Bottom-Right": (0.95, 0.05), "Bottom-Left": (0.05, 0.05)}[na_pos]
            na = ax.annotate("N", xy=pos, xytext=(pos[0], pos[1] - 0.1), xycoords="axes fraction", ha="center", va="center", fontsize=north_f, color=na_col, arrowprops=dict(facecolor=na_col, width=5, headwidth=15))
            na.set_clip_on(True); na.set_clip_path(ax.patch)
          
        # Halo around the arrow patch
        patch = getattr(na, "arrow_patch", None)
        if patch is not None and na_arrow_halo_on and na_arrow_halo_w > 0:
            patch.set_path_effects([pe.withStroke(linewidth=na_arrow_halo_w, foreground=na_arrow_halo_col)])

            na.set_clip_on(True); na.set_clip_path(ax.patch)
            
        #Drawing for Custom Text
        if custom_on and custom_txt.strip():
            style = {}
            if custom_box:
                style = dict(boxstyle="round", fc=custom_box_fc, ec=custom_box_ec, alpha=custom_box_alpha)

            txt_obj = ax.text(
                custom_x, custom_y, custom_txt,
                transform=ax.transAxes, ha=custom_ha, va=custom_va,
                fontsize=custom_fs, color=custom_col, rotation=custom_rot,
                fontweight=("bold" if custom_bold else "normal"),
                style=("italic" if custom_ital else "normal"),
                bbox=(style if custom_box else None)
            )
            txt_obj.set_clip_on(True); txt_obj.set_clip_path(ax.patch)

            if custom_halo and custom_halo_w > 0:
                txt_obj.set_path_effects([pe.withStroke(linewidth=custom_halo_w, foreground=custom_halo_col)])


        # Watermark
        wm = ax.text(0.99, 0.01, "CartoZen Beta", transform=ax.transAxes, ha="right", va="bottom", fontsize=10, color="gray", alpha=0.6)
        wm.set_clip_on(True); wm.set_clip_path(ax.patch)

        # Export (avoid tight bbox when any inset present)
        tmp = tempfile.mkdtemp(); out = os.path.join(tmp, f"map.{fmt.lower()}")
        fig.canvas.draw()
        try:
            if inset_on or getattr(fig, "_cz_has_local_insets", False):
                fig.savefig(out, format=fmt.lower(), dpi=dpi)
            else:
                fig.savefig(out, bbox_inches="tight", pad_inches=0.3, format=fmt.lower(), dpi=dpi)
        except Exception:
            fig.savefig(out, format=fmt.lower(), dpi=dpi)
        plt.close()

        with open(out, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        st.markdown(
            f'<a href="data:image/{fmt.lower()};base64,{b64}" '
            f'download="station_map.{fmt.lower()}">📥 Download Map</a>',
            unsafe_allow_html=True,
        )

        # Fit image to screen height (~calc 85vh leaves room for sidebar/header)
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center;">
                <img src="data:image/{fmt.lower()};base64,{b64}"
                    style="max-width:100%; max-height:85vh; object-fit:contain;" />
            </div>
            """,
            unsafe_allow_html=True,
        )


elif view == "About":
    try:
        st.markdown(open("about.md","r",encoding="utf-8").read(), unsafe_allow_html=True)
    except Exception:
        st.info("about.md not found.")
elif view == "Changelog":
    try:
        st.markdown(open("changelog.md","r",encoding="utf-8").read(), unsafe_allow_html=True)
    except Exception:
        st.info("changelog.md not found.")
