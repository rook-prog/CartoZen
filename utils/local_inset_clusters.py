# utils/local_inset_clusters.py
"""Tiny in-figure insets for the largest clusters.

Usage in app.py:

from utils.local_inset_clusters import draw_cluster_insets

axes = draw_cluster_insets(ax, df, clusters, max_insets=2, pad_deg=0.2,
                           land_color=land_col, ocean_color=ocean_col,
                           marker_color=m_col)
"""
from __future__ import annotations
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def draw_cluster_insets(ax_main, df, clusters, max_insets: int = 2, pad_deg: float = 0.2,
                        box_frac: float = 0.22, land_color: str = "#f0e8d8",
                        ocean_color: str = "#cce6ff", marker_color: str = "#6a5acd",
                        marker_size: int = 16):
    """Create up to N small insets for the biggest clusters (size>1).
    Returns list of created inset axes.
    """
    fig = ax_main.figure
    # choose top clusters by size (>1)
    big = [(cid, len(idxs)) for cid, idxs in clusters.items() if len(idxs) > 1]
    big.sort(key=lambda x: x[1], reverse=True)
    big = big[:max(0, int(max_insets))]
    if not big:
        return []

    # layout along right side inside the main axes
    mb = ax_main.get_position()
    w = mb.width * box_frac
    h = mb.height * box_frac
    left = mb.x0 + mb.width - w - 0.01  # slight padding from right edge

    axes = []
    for k, (cid, size) in enumerate(big):
        bottom = mb.y0 + mb.height - (k + 1) * (h + 0.01)
        if bottom < mb.y0:
            break
        axx = fig.add_axes([left, bottom, w, h], projection=ccrs.PlateCarree())
        axx.set_in_layout(False)
        axx.set_zorder(90)
        # base
        axx.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
        axx.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
        axx.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)
        # extent from members
        sub = df.iloc[clusters[cid]][["Lon_DD", "Lat_DD"]]
        mnx, mxx = float(sub["Lon_DD"].min()), float(sub["Lon_DD"].max())
        mny, mxy = float(sub["Lat_DD"].min()), float(sub["Lat_DD"].max())
        axx.set_extent((mnx - pad_deg, mxx + pad_deg, mny - pad_deg, mxy + pad_deg))
        # points
        axx.scatter(sub["Lon_DD"], sub["Lat_DD"], s=marker_size ** 2, c=marker_color, transform=ccrs.PlateCarree())
        axx.set_xticks([])
        axx.set_yticks([])
        for spine in axx.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.8)
        axes.append(axx)
    return axes
