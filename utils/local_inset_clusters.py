# utils/local_inset_clusters.py — ADVANCED
# New features
# • Label styling in mini‑insets (color, halo, size, alignment)
# • Anchor the inset around each cluster: top/bottom/left/right/center variants
# • Custom connector color & thickness
# • Still sets fig._cz_has_local_insets for export logic

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def _data_to_fig_xy(ax, lon, lat):
    disp = ax.transData.transform((lon, lat))
    fx, fy = ax.figure.transFigure.inverted().transform(disp)
    return fx, fy


def _resolve_anchor(anchor: str):
    a = (anchor or "top right").strip().lower()
    # support a few synonyms
    aliases = {
        "right": "center right",
        "left": "center left",
        "top": "top center",
        "bottom": "bottom center",
        "centre": "center",
    }
    a = aliases.get(a, a)
    allowed = {
        "top left", "top center", "top right",
        "center left", "center", "center right",
        "bottom left", "bottom center", "bottom right",
    }
    return a if a in allowed else "top right"


def _place_rect_near(ax_main, cx, cy, w, h, anchor: str, offset: float):
    """Return [left, bottom, w, h] in figure coords for a rect anchored near (cx,cy)."""
    fig = ax_main.figure
    mb = ax_main.get_position()
    fx, fy = _data_to_fig_xy(ax_main, cx, cy)
    # anchor → bottom-left corner relative to centroid
    anchor = _resolve_anchor(anchor)
    # initial left/bottom around centroid
    if anchor == "top left":
        left, bottom = fx - w - offset, fy + offset
    elif anchor == "top center":
        left, bottom = fx - w/2, fy + offset
    elif anchor == "top right":
        left, bottom = fx + offset, fy + offset
    elif anchor == "center left":
        left, bottom = fx - w - offset, fy - h/2
    elif anchor == "center":
        left, bottom = fx - w/2, fy - h/2
    elif anchor == "center right":
        left, bottom = fx + offset, fy - h/2
    elif anchor == "bottom left":
        left, bottom = fx - w - offset, fy - h - offset
    elif anchor == "bottom center":
        left, bottom = fx - w/2, fy - h - offset
    else:  # bottom right
        left, bottom = fx + offset, fy - h - offset

    # clamp fully inside main axes rectangle
    left = max(mb.x0, min(mb.x0 + mb.width - w, left))
    bottom = max(mb.y0, min(mb.y0 + mb.height - h, bottom))
    return [left, bottom, w, h]


def draw_cluster_insets(
    ax_main,
    df,
    clusters,
    max_insets=2,
    pad_deg=0.2,
    box_frac=0.18,
    land_color="#f0e8d8",
    ocean_color="#cce6ff",
    marker_color="#6a5acd",
    marker_size=16,
    # label options inside the mini‑inset
    show_labels=False,
    label_col=None,
    label_fontsize=7,
    label_color=None,            # default: marker_color
    label_align="left",         # left|center|right
    label_halo=True,
    label_halo_width=2.5,
    label_halo_color="white",
    label_offset_px=(6,4),    # <— NEW: (dx, dy) in points
    # placement around each cluster
    anchor="top right",         # e.g. top left/top center/top right/center left/center/center right/bottom left/bottom center/bottom right
    offset_frac=0.012,
    # frame & connector
    frame_lw=0.6,
    link=True,
    link_color="#444444",
    link_lw=0.8,
):
    """Create up to N small insets for the biggest clusters (size>1).
    Returns list[Axes].
    """
    fig = ax_main.figure
    setattr(fig, "_cz_has_local_insets", True)

    # pick largest clusters (>1 members)
    big = [(cid, len(idxs)) for cid, idxs in clusters.items() if len(idxs) > 1]
    big.sort(key=lambda x: x[1], reverse=True)
    big = big[:max(0, int(max_insets))]
    if not big:
        return []

    mb = ax_main.get_position()
    w = mb.width * float(box_frac)
    h = mb.height * float(box_frac)

    axes = []
    for cid, size in big:
        sub = df.iloc[clusters[cid]][["Lon_DD", "Lat_DD"]]
        mnx, mxx = float(sub["Lon_DD"].min()), float(sub["Lon_DD"].max())
        mny, mxy = float(sub["Lat_DD"].min()), float(sub["Lat_DD"].max())
        cx, cy   = float(sub["Lon_DD"].mean()), float(sub["Lat_DD"].mean())

        rect = _place_rect_near(ax_main, cx, cy, w, h, anchor=_resolve_anchor(anchor), offset=float(offset_frac))
        axx = fig.add_axes(rect, projection=ccrs.PlateCarree())
        axx.set_in_layout(False)
        axx.set_zorder(90)

        # basemap
        axx.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
        axx.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
        axx.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)

        # extent
        axx.set_extent((mnx - pad_deg, mxx + pad_deg, mny - pad_deg, mxy + pad_deg), crs=ccrs.PlateCarree())

        # points
        axx.scatter(sub["Lon_DD"], sub["Lat_DD"], s=marker_size**2, c=marker_color, transform=ccrs.PlateCarree())

        # labels (optional) — style similar to marker: same color by default + white halo
        if show_labels and label_col and (label_col in df.columns):
            ha = {"left": "left", "center": "center", "right": "right"}.get(str(label_align).lower(), "left")
            peff = [pe.withStroke(linewidth=label_halo_width, foreground=label_halo_color)] if label_halo else None
            col = label_color or marker_color
            dx_px, dy_px = label_offset_px
            for idx in clusters[cid]:
                axx.text(
                    float(df.iloc[idx]["Lon_DD"]), float(df.iloc[idx]["Lat_DD"]),
                    str(df.iloc[idx][label_col]), fontsize=label_fontsize,
                    color=col, transform=ccrs.PlateCarree(), ha=ha, va="bottom",
                    path_effects=peff,
                )

        # frame
        axx.set_xticks([]); axx.set_yticks([])
        for spine in axx.spines.values():
            spine.set_visible(True); spine.set_linewidth(frame_lw)

        # connector line from centroid to inset center
        if link:
            try:
                fx, fy = _data_to_fig_xy(ax_main, cx, cy)
                cx_box = rect[0] + rect[2] / 2.0
                cy_box = rect[1] + rect[3] / 2.0
                line = plt.Line2D([fx, cx_box], [fy, cy_box], transform=fig.transFigure, lw=link_lw, color=link_color, alpha=0.85)
                fig.add_artist(line)
            except Exception:
                pass

        axes.append(axx)

    return axes



