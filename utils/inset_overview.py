# utils/inset_overview.py (patched)
# Draw a reliable inset overview with AOI rectangle + optional overlay.
# - Keeps inset out of tight-layout math
# - Ensures it renders above other artists
# - Uses global view with clear land/ocean/coatline
# - Makes AOI clearly visible (dynamic linewidth, optional fill)

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.patches import Rectangle


def _inset_anchor_and_loc(inset_pos: str):
    pos_map = {
        "top right": ((1.0, 1.0), "upper right"),
        "top left": ((0.0, 1.0), "upper left"),
        "bottom right": ((1.0, 0.0), "lower right"),
        "bottom left": ((0.0, 0.0), "lower left"),
    }
    return pos_map.get(inset_pos, ((1.0, 1.0), "upper right"))


essential_cartopy = dict(projection=ccrs.PlateCarree())


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
    aoi_fill_alpha=0.0,   # 0 = no fill; set 0.1..0.3 to verify visibility
):
    """Draw a small global inset on top of ax_main with AOI rectangle and
    optional overlay outline.

    Parameters
    ----------
    ax_main : cartopy.mpl.geoaxes.GeoAxes
        Main map axes.
    bounds : (min_lon, max_lon, min_lat, max_lat)
        AOI extent in degrees.
    overlay_path : file-like or path, optional
        Streamlit-uploaded file for overlay_gdf.
    plot_overlay : bool
        Whether to plot overlay in inset.
    inset_pos : str
        One of {"top right","top left","bottom right","bottom left"}.
    inset_size_pct : int
        Inset size as percent of parent axes width/height (10–40 recommended).
    aoi_edge_color : str
        Color for AOI rectangle.
    land_color, ocean_color : str
        Fill colors for inset land/ocean.
    aoi_fill_alpha : float
        If > 0, AOI rectangle will have a translucent fill for visibility.
    """
    (anchor_xy, loc) = _inset_anchor_and_loc(inset_pos)

    ax_inset = inset_axes(
        ax_main,
        width=f"{inset_size_pct}%",
        height=f"{inset_size_pct}%",
        loc=loc,
        bbox_to_anchor=(anchor_xy[0], anchor_xy[1], 0, 0),
        bbox_transform=ax_main.transAxes,
        borderpad=0.8,
        axes_class=type(ax_main),
        axes_kwargs=essential_cartopy,
    )

    # Keep inset out of tight-layout/bbox math and render on top
    try:
        ax_inset.set_in_layout(False)
    except Exception:
        pass
    ax_inset.set_zorder(99)
    ax_inset.patch.set_alpha(1.0)

    # Base features (global view)
    ax_inset.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
    ax_inset.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
    ax_inset.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)
    ax_inset.set_global()

    # Optional overlay in inset
    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=aoi_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=100
            )
        except Exception:
            pass

    # AOI rectangle — dynamic linewidth for small insets
    min_lon, max_lon, min_lat, max_lat = bounds
    aoi_width = max_lon - min_lon
    aoi_height = max_lat - min_lat

    # Scale line width inversely with inset size (so it stays visible)
    base_lw = 1.2
    lw = max(base_lw, 0.8 * (40.0 / max(10.0, float(inset_size_pct))))

    rect = Rectangle(
        (min_lon, min_lat),
        width=aoi_width,
        height=aoi_height,
        linewidth=lw,
        edgecolor=aoi_edge_color,
        facecolor=(aoi_edge_color if aoi_fill_alpha > 0 else 'none'),
        alpha=aoi_fill_alpha if aoi_fill_alpha > 0 else 1.0,
        transform=ccrs.PlateCarree(),
        zorder=101,
    )
    ax_inset.add_patch(rect)

    # Minimal axes styling (make frame visible)
    try:
        ax_inset.set_xticks([])
        ax_inset.set_yticks([])
        for spine in ax_inset.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.8)
    except Exception:
        pass

    return ax_inset
