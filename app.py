from PIL import Image
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import numpy as np
import tempfile, os, base64
from matplotlib import ticker as mticker
from utils.coord_utils import convert_coords, dms_to_dd, get_buffered_extent
from utils.overlay_loader import overlay_gdf
from utils.plot_helpers import dd_fmt_lon, dd_fmt_lat, dms_fmt_lon, dms_fmt_lat, draw_scale_bar
from utils.config import shape_map, get_page_size

# Navigation selection at the top
view = st.selectbox("View", ["Map", "About", "Changelog"])

if view == "Map":
    # ⬇️ Place your entire existing map generation logic here
    # From file upload, coordinate handling, plotting, customization, etc.
    st.set_page_config(page_title="CartoZen Beta", page_icon="🗺️", layout="wide")

# Load logo
logo = Image.open("assets/logo_small.png")
st.columns([1,6,1])[1].image(logo, use_container_width=False)

st.title("🗺️ CartoZen – Station Map Generator (Beta)")
st.markdown("Welcome to the beta version of CartoZen. Upload your station data and generate custom maps easily.")

with st.sidebar:
    st.header("**⚙️ Controls**")
    with st.sidebar.expander("**Data upload**", expanded =False):
        up_file = st.file_uploader("CSV / XLSX", ["csv", "xlsx"])
        coord_fmt = st.selectbox("Coord format", ["DMS", "Decimal Degrees", "UTM"])
        auto_ext = st.checkbox("Auto-fit extent", True)
        margin = st.slider("Margin %", 1, 30, 10)

    buffer_deg = 5
    if not auto_ext:
        buffer_deg = st.slider("Buffer around data (°)", 1, 20, 5)

    with st.sidebar.expander("**Overlay**", expanded =False):
        ov_file = st.file_uploader("zip / GeoJSON / KML", ["zip", "geojson", "kml"])
        show_ov = st.checkbox("Show overlay", True)

    with st.sidebar.expander("**Map Colors**", expanded=False):
        land_col = st.color_picker("Land color", "#f0e8d8")
        ocean_col = st.color_picker("Water color", "#cce6ff")

    with st.sidebar.expander("**Marker**", expanded=False):
        shape = st.selectbox("Shape", list(shape_map.keys()))
        m_col = st.color_picker("Colour", "#00cc44")
        m_size = st.slider("Size", 5, 20, 10)
        show_lab = st.checkbox("Show labels", True)
        dx = st.slider("Label offset °lon", -1.00, 1.00, 0.01, 0.05) if show_lab else 0
        dy = st.slider("Label offset °lat", -1.00, 1.00, 0.01, 0.05) if show_lab else 0

    with st.sidebar.expander("**Grid & Axis**", expanded=False):
        grid_on = st.checkbox("Grid", True)
        g_int = st.selectbox("Interval °", [0.1, 0.25, 0.5, 1, 2, 5, 10], index=2)
        g_col = st.color_picker("Grid colour", "#666666")
        g_style = st.selectbox("Style", ["solid", "dashed", "dotted"])
        g_wid = st.slider("Line width", 0.5, 2.5, 1.0, 0.1)
        axis_fmt = st.radio("Label format", ["Decimal", "DMS"])

    with st.sidebar.expander("**Elements + Fonts**", expanded=False):
        leg_on = st.checkbox("Legend", True)
        leg_pos = st.selectbox("Legend pos", ["upper left","upper right","lower left","lower right","center left","center right"])
        sb_on = st.checkbox("Scale-bar", True)
        sb_len = st.slider("Bar length", 10, 500, 50, 10)
        sb_seg = st.slider("Segments", 2, 5, 3)
        sb_thk = st.slider("Bar thickness", 1, 50, 3)
        sb_pos = st.selectbox("Bar pos", ["Bottom-Left","Bottom-Right","Top-Left","Top-Right"])
        sb_unit = st.selectbox("Units", ["km", "miles"])
        na_on = st.checkbox("North arrow", True)
        na_pos = st.selectbox("North pos", ["Top-Right","Top-Left","Bottom-Right","Bottom-Left"])
        na_col = st.color_picker("North colour", "#000000")
   
    with st.sidebar.expander("**Font sizes**", expanded=False):
        axis_f = st.slider("Axis ticks", 6, 16, 8)
        label_f = st.slider("Labels", 6, 16, 8)
        legend_f = st.slider("Legend", 6, 16, 8)
        sb_f = st.slider("Scale-bar", 6, 16, 8)
        north_f = st.slider("North arrow", 10, 30, 18)

    if up_file:
        df0 = pd.read_csv(up_file) if up_file.name.endswith("csv") else pd.read_excel(up_file)
        df_cols = df0.columns
        with st.sidebar.expander("**Legend / Label columns**", expanded=False):
            stn = st.selectbox("Station ID", df_cols)
            at = st.selectbox("Attribute", df_cols)
            lab = st.selectbox("Label col", df_cols)
        with st.sidebar.expander("**Legend header**", expanded=False):
            head1 = st.text_input("Header line 1", value=f"{stn} – {at}")
            head2 = st.text_input("Header line 2 (optional)", value="")
    else:
        stn = at = lab = head1 = head2 = None

    with st.sidebar.expander("**Export**", expanded=False):
        fmt = st.selectbox("Format", ["PNG", "JPEG"])
        dpi = st.slider("DPI", 100, 600, 300)
        p_sz = st.selectbox("Page", ["A4", "A3", "Letter"])
        ori = st.selectbox("Orientation", ["Landscape", "Portrait"])
        full = st.checkbox("Full-width preview", False)

if up_file and stn and at and lab:
    lat_col = [c for c in df0.columns if c.lower() in ["lat", "latitude"]][0]
    lon_col = [c for c in df0.columns if c.lower() in ["long", "longitude"]][0]
    df = convert_coords(df0, coord_fmt, lat_col, lon_col)
    # ✅ Check that the converted columns exist
    if "Lat_DD" not in df.columns or "Lon_DD" not in df.columns:
        st.error("❌ Converted coordinate columns not found. Please verify your input and format.")
        st.stop()

    # ✅ Validate coordinate conversion
    if df["Lat_DD"].isnull().all() or df["Lon_DD"].isnull().all():
        st.error("❌ Coordinate conversion failed.\nPlease ensure that the selected coordinate format (DMS, Decimal Degrees, or UTM) matches your uploaded data.")
        st.stop()


    if auto_ext:
        lo, hi = df["Lon_DD"].agg(["min", "max"])
        la, lb = df["Lat_DD"].agg(["min", "max"])
        bounds = (lo - (hi - lo) * margin / 100,
                  hi + (hi - lo) * margin / 100,
                  la - (lb - la) * margin / 100,
                  lb + (lb - la) * margin / 100)
    else:
        bounds = get_buffered_extent(df, buffer_deg)

    halo = [pe.withStroke(linewidth=3, foreground="white")]
    fig = plt.figure(figsize=get_page_size(p_sz, ori), dpi=dpi)
    fig.set_size_inches(*get_page_size(p_sz, ori), forward=True)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent(bounds)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    ax.add_feature(cfeature.LAND.with_scale("50m"), fc=land_col)
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), fc=ocean_col)
    ax.add_feature(cfeature.BORDERS, ls=":")
    ax.add_feature(cfeature.COASTLINE)

    xt = np.arange(bounds[0], bounds[1] + g_int, g_int)
    yt = np.arange(bounds[2], bounds[3] + g_int, g_int)
    if not grid_on:
        ax.set_xticks(xt, crs=ccrs.PlateCarree())
        ax.set_yticks(yt, crs=ccrs.PlateCarree())
        ax.tick_params(length=4, width=g_wid, color=g_col, labelsize=axis_f)
    ax.tick_params(length=4, width=g_wid, color=g_col, labelsize=axis_f)

    if grid_on:
        gl = ax.gridlines(draw_labels=True, xlocs=xt, ylocs=yt,
                          color=g_col, ls=g_style, lw=g_wid)
        gl.top_labels = True
        gl.right_labels = True
        gl.xlabel_style = gl.ylabel_style = {'size': axis_f}
        if axis_fmt == "DMS":
            gl.xformatter = mticker.FuncFormatter(dms_fmt_lon)
            gl.yformatter = mticker.FuncFormatter(dms_fmt_lat)
        else:
            gl.xformatter = mticker.FuncFormatter(dd_fmt_lon)
            gl.yformatter = mticker.FuncFormatter(dd_fmt_lat)

    if ov_file and show_ov:
        overlay_gdf(ov_file).to_crs("EPSG:4326").plot(
            ax=ax, edgecolor="red", facecolor="none", lw=1)

    ax.scatter(df["Lon_DD"], df["Lat_DD"], s=m_size**2, c=m_col,
               marker=shape_map[shape], transform=ccrs.PlateCarree(), zorder=5)
    if show_lab:
        for _, r in df.iterrows():
            ax.text(r["Lon_DD"] + dx, r["Lat_DD"] + dy, str(r[lab]),
                    fontsize=label_f, transform=ccrs.PlateCarree(),
                    path_effects=halo)

    if sb_on:
        km_len = sb_len if sb_unit == "km" else sb_len * 1.60934
        draw_scale_bar(ax, bounds, km_len, sb_seg, sb_thk, sb_pos, sb_unit, sb_f)

    if na_on:
        x, y = {"Top-Right": (0.95, 0.95), "Top-Left": (0.05, 0.95),
                "Bottom-Right": (0.95, 0.05), "Bottom-Left": (0.05, 0.05)}[na_pos]
        ax.annotate("N", xy=(x, y), xytext=(x, y - 0.1), xycoords="axes fraction",
                    ha="center", va="center", fontsize=north_f, color=na_col,
                    arrowprops=dict(facecolor=na_col, width=5, headwidth=15))

    if leg_on:
        rows = df[[stn, at]].astype(str).agg(" – ".join, axis=1).tolist()
        header = [head1] if head1 else []
        if head2: header.append(head2)
        leg_text = "\n".join(header + rows)
        box = dict(boxstyle="round", fc="white", ec="black", alpha=0.8)
        pos_map = {
            "upper left": (0.01, 0.99), "upper right": (0.99, 0.99),
            "lower left": (0.01, 0.01), "lower right": (0.99, 0.01),
            "center left": (0.01, 0.5), "center right": (0.99, 0.5)
        }
        xp, yp = pos_map[leg_pos]
        ax.text(xp, yp, leg_text, transform=ax.transAxes, fontsize=legend_f,
                ha="left" if "left" in leg_pos else "right",
                va="top" if "upper" in leg_pos else "bottom" if "lower" in leg_pos else "center",
                bbox=box)

    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, f"map.{fmt.lower()}")
    add_wm = ax.text(0.99, 0.01, "CartoZen Beta", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=10, color="gray", alpha=0.6)

    fig.savefig(out, bbox_inches="tight", pad_inches=0.3, format=fmt.lower())
    plt.close()
    b64 = base64.b64encode(open(out, "rb").read()).decode()
    st.markdown(f'<a href="data:image/{fmt.lower()};base64,{b64}" '
                f'download="station_map.{fmt.lower()}">📥 Download Map</a>',
                unsafe_allow_html=True)
    st.image(out, use_container_width=full)

elif view == "About":
    st.markdown(open("about.md", "r").read(), unsafe_allow_html=True)

elif view == "Changelog":
    st.markdown(open("changelog.md", "r").read(), unsafe_allow_html=True)
