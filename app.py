# app.py — CartoZen main app with Inset fixes, clean color wiring, and Declutter/Cluster
# NOTE: This expects the three utils from the other canvas to be present:
#   utils/cluster_utils.py, utils/label_declutter.py, utils/local_inset_clusters.py
# and the inset module from the Inset & Color patch:
#   utils/inset_overview.py

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

st.set_page_config(page_title="CartoZen Beta", page_icon="🗺️", layout="wide")

# Helper: case-insensitive column resolver
def _find_col(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in lower: return lower[cand]
    return None

# UI
view = st.selectbox("View", ["Map", "About", "Changelog"])
try:
    logo = Image.open("assets/logo_small.png"); st.columns([1,6,1])[1].image(logo, use_container_width=False)
except Exception:
    pass
st.title("🗺️ CartoZen – Station Map Generator (Beta)")
st.markdown("Upload your station data and generate custom maps easily.")

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
            buffer_deg = st.slider("Buffer around data (°)", 1, 20, 5)
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
            show_lab = st.checkbox("Show labels", True)
            dx = st.slider("Label offset °lon", -1.00, 1.00, 0.01, 0.05) if show_lab else 0
            dy = st.slider("Label offset °lat", -1.00, 1.00, 0.01, 0.05) if show_lab else 0
        with st.expander("**Grid & Axis**", expanded=False):
            grid_on = st.checkbox("Grid", True)
            g_int = st.selectbox("Interval °", [0.1,0.25,0.5,1,2,5,10], index=2)
            g_col = st.color_picker("Grid colour", "#666666")
            g_style = st.selectbox("Style", ["solid","dashed","dotted"])
            g_wid = st.slider("Line width", 0.5, 2.5, 1.0, 0.1)
            axis_fmt = st.radio("Label format", ["Decimal","DMS"])
        with st.expander("**Elements + Fonts**", expanded=False):
            leg_on = st.checkbox("Legend", True)
            leg_pos = st.selectbox("Legend pos", ["upper left","upper right","lower left","lower right","center left","center right"]) 
            sb_on = st.checkbox("Scale-bar", True)
            sb_len = st.slider("Bar length", 10, 500, 50, 10)
            sb_seg = st.slider("Segments", 2, 5, 3)
            sb_thk = st.slider("Bar thickness", 1, 50, 3)
            sb_pos = st.selectbox("Bar pos", ["Bottom-Left","Bottom-Right","Top-Left","Top-Right"]) 
            sb_unit = st.selectbox("Units", ["km","miles"]) 
            na_on = st.checkbox("North arrow", True)
            na_pos = st.selectbox("North pos", ["Top-Right","Top-Left","Bottom-Right","Bottom-Left"]) 
            na_col = st.color_picker("North colour", "#000000")
        with st.expander("**Inset overview**", expanded=False):
            inset_on = st.checkbox("Show inset", False)
            inset_pos = st.selectbox("Inset pos", ["top right","top left","bottom right","bottom left"], index=0)
            inset_size = st.slider("Inset size (%)", 10, 40, 20)
            extent_mode = st.selectbox("Inset extent", ["global","aoi","country","continent"], index=0)
            extent_pad = st.slider("Inset extent padding (°)", 0.0, 10.0, 3.0, 0.5)
            inset_rect_color = st.color_picker("AOI rectangle colour", "#ff0000")
            inset_ov = st.checkbox("Plot overlay in inset", True)
            inset_ov_color = st.color_picker("Inset overlay colour", "#0000ff")
            frame_on = st.checkbox("Inset frame", True)
            frame_lw = st.slider("Inset frame width", 0.5, 3.0, 0.8, 0.1)
        # NEW: Declutter & Cluster
        with st.expander("**Declutter & Cluster**", expanded=False):
            declutter_on = st.checkbox("Avoid label overlap (repel)", False)
            cluster_on = st.checkbox("Cluster nearby stations", False)
            cluster_km = st.slider("Cluster distance (km)", 1, 50, 12)
            show_cluster_counts = st.checkbox("Show cluster counts on map", True)
            local_insets = st.checkbox("Local insets for largest clusters", False)
            max_insets = st.slider("Number of local insets", 0, 3, 2)
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

        # Extent
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

        # Figure
        halo = [pe.withStroke(linewidth=3, foreground="white")]
        fig = plt.figure(figsize=get_page_size(p_sz, ori), dpi=dpi)
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
        ax.set_extent(bounds)
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Base
        ax.add_feature(cfeature.LAND.with_scale("50m"), fc=land_col)
        ax.add_feature(cfeature.OCEAN.with_scale("50m"), fc=ocean_col)
        ax.add_feature(cfeature.BORDERS, ls=":"); ax.add_feature(cfeature.COASTLINE)

        # Grid
        xt = np.arange(bounds[0], bounds[1] + g_int, g_int)
        yt = np.arange(bounds[2], bounds[3] + g_int, g_int)
        if grid_on:
            gl = ax.gridlines(draw_labels=True, xlocs=xt, ylocs=yt, color=g_col, ls=g_style, lw=g_wid)
            gl.top_labels = gl.right_labels = True
            gl.xlabel_style = gl.ylabel_style = {"size": axis_f}
            gl.xformatter = (mticker.FuncFormatter(dms_fmt_lon) if axis_fmt=="DMS" else mticker.FuncFormatter(dd_fmt_lon))
            gl.yformatter = (mticker.FuncFormatter(dms_fmt_lat) if axis_fmt=="DMS" else mticker.FuncFormatter(dd_fmt_lat))
        else:
            ax.set_xticks(xt, crs=ccrs.PlateCarree()); ax.set_yticks(yt, crs=ccrs.PlateCarree())
            ax.tick_params(length=4, width=g_wid, color=g_col, labelsize=axis_f)

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
        ax.scatter(plot_df["Lon_DD"], plot_df["Lat_DD"], s=m_size**2, c=m_col, marker=shape_map[shape], transform=ccrs.PlateCarree(), zorder=5)

        # Labels (optionally counts for clusters)
        texts = []
        if show_lab:
            if cluster_on and clusters is not None:
                for _, r in plot_df.iterrows():
                    cid = int(r.get("cluster_id", -1))
                    size = int(r.get("cluster_size", 1))
                    # representative original row index for this cluster
                    rep_idx = clusters.get(cid, [None])[0]

                    if size > 1 and show_cluster_counts:
                        label = str(size)  # show cluster size
                    else:
                        # fall back to a representative station's label from the original df
                        label = (
                            str(df.iloc[rep_idx][lab])
                            if rep_idx is not None and lab in df.columns
                            else ""
                        )

                    t = ax.text(
                        r["Lon_DD"] + dx,
                        r["Lat_DD"] + dy,
                        label,
                        fontsize=label_f,
                        transform=ccrs.PlateCarree(),
                        path_effects=halo,
                    )
                    texts.append(t)

            else:
                for _, r in plot_df.iterrows():
                    t = ax.text(r["Lon_DD"] + dx, r["Lat_DD"] + dy, str(r[lab]), fontsize=label_f, transform=ccrs.PlateCarree(), path_effects=halo)
                    texts.append(t)
        if show_lab and declutter_on and texts:
            declutter_texts(ax, texts)

        # Optional local mini-insets for biggest clusters
        if cluster_on and local_insets and clusters:
            draw_cluster_insets(ax, df, clusters, max_insets=max_insets, land_color=land_col, ocean_color=ocean_col, marker_color=m_col)

        # Global inset overview
        if inset_on:
            draw_inset_overview(
                ax_main=ax,
                bounds=bounds,
                overlay_path=ov_file if inset_ov else None,
                plot_overlay=inset_ov,
                inset_pos=inset_pos,
                inset_size_pct=inset_size,
                aoi_edge_color=inset_rect_color,
                overlay_edge_color=inset_ov_color,
                land_color=land_col,
                ocean_color=ocean_col,
                extent_mode=extent_mode,
                extent_pad_deg=extent_pad,
                inset_frame=frame_on,
                inset_frame_lw=frame_lw,
                ne_countries_path=NE_COUNTRIES_ZIP,
            )

        # Watermark
        ax.text(0.99, 0.01, "CartoZen Beta", transform=ax.transAxes, ha="right", va="bottom", fontsize=10, color="gray", alpha=0.6)

        # Export
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
        st.markdown(f'<a href="data:image/{fmt.lower()};base64,{b64}" download="station_map.{fmt.lower()}">📥 Download Map</a>', unsafe_allow_html=True)
        st.image(out, use_container_width=full)

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
