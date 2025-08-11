# utils/inset_overview.py
# Utility for drawing an inset overview map with AOI rectangle and optional overlay.

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
    try:
        ax_inset.set_in_layout(False)
    except Exception:
        pass

    ax_inset.set_global()
    ax_inset.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
    ax_inset.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
    ax_inset.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)

    # Optional overlay in inset
    if plot_overlay and overlay_path is not None:
        try:
            from utils.overlay_loader import overlay_gdf
            overlay_gdf(overlay_path).to_crs("EPSG:4326").plot(
                ax=ax_inset, edgecolor=aoi_edge_color, facecolor="none", lw=1.0,
                transform=ccrs.PlateCarree(), zorder=9
            )
        except Exception:
            pass

    # AOI rectangle
    min_lon, max_lon, min_lat, max_lat = bounds
    rect = Rectangle(
        (min_lon, min_lat),
        width=(max_lon - min_lon),
        height=(max_lat - min_lat),
        linewidth=1.2,
        edgecolor=aoi_edge_color,
        facecolor="none",
        transform=ccrs.PlateCarree(),
        zorder=10,
    )
    ax_inset.add_patch(rect)

    # Minimal axes styling
    try:
        ax_inset.set_xticks([])
        ax_inset.set_yticks([])
        for spine in ax_inset.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.8)
    except Exception:
        pass

    return ax_inset
