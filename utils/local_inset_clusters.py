# utils/local_inset_clusters.py — UPDATED
# • Labels inside mini‑insets (show_labels=True, label_col=...)
# • Slim frame (frame_lw)
# • Place mini‑insets ADJACENT to their cluster centroids (adjacent=True)
# • Optional connector line to centroid (link=True)
# • Marks fig._cz_has_local_insets for export logic (skip tight bbox)

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def _data_to_fig_xy(ax, lon, lat):
    """Convert data (lon,lat) to figure fraction coords."""
    disp = ax.transData.transform((lon, lat))
    fx, fy = ax.figure.transFigure.inverted().transform(disp)
    return fx, fy


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
    show_labels=False,
    label_col=None,
    label_fontsize=7,
    adjacent=True,
    frame_lw=0.6,
    link=True,
):
    """Create up to N small insets for the biggest clusters (size>1), placed near each cluster.
    Returns list[Axes].
    """
    fig = ax_main.figure
    setattr(fig, "_cz_has_local_insets", True)

    # Top clusters
    big = [(cid, len(idxs)) for cid, idxs in clusters.items() if len(idxs) > 1]
    big.sort(key=lambda x: x[1], reverse=True)
    big = big[:max(0, int(max_insets))]
    if not big:
        return []

    mb = ax_main.get_position()
    w = mb.width * float(box_frac)
    h = mb.height * float(box_frac)

    axes = []
    for k, (cid, size) in enumerate(big):
        sub = df.iloc[clusters[cid]][["Lon_DD", "Lat_DD"]]
        mnx, mxx = float(sub["Lon_DD"].min()), float(sub["Lon_DD"].max())
        mny, mxy = float(sub["Lat_DD"].min()), float(sub["Lat_DD"].max())
        cx, cy = float(sub["Lon_DD"].mean()), float(sub["Lat_DD"].mean())

        if adjacent:
            fx, fy = _data_to_fig_xy(ax_main, cx, cy)
            # small offset so the box does not cover the cluster itself
            fx += 0.012; fy += 0.012
            # clamp to main axes area
            fx = min(max(fx, mb.x0), mb.x0 + mb.width - w)
            fy = min(max(fy, mb.y0), mb.y0 + mb.height - h)
            rect = [fx, fy, w, h]
        else:
            # Right‑rail fallback layout
            left = mb.x0 + mb.width - w - 0.01
            bottom = mb.y0 + mb.height - (k + 1) * (h + 0.01)
            if bottom < mb.y0:
                break
            rect = [left, bottom, w, h]

        axx = fig.add_axes(rect, projection=ccrs.PlateCarree())
        axx.set_in_layout(False)
        axx.set_zorder(90)

        # Basemap
        axx.add_feature(cfeature.OCEAN.with_scale("110m"), fc=ocean_color, lw=0)
        axx.add_feature(cfeature.LAND.with_scale("110m"), fc=land_color, lw=0)
        axx.add_feature(cfeature.COASTLINE.with_scale("110m"), lw=0.5)
        axx.set_extent((mnx - pad_deg, mxx + pad_deg, mny - pad_deg, mxy + pad_deg))

        # Points
        axx.scatter(sub["Lon_DD"], sub["Lat_DD"], s=marker_size ** 2, c=marker_color, transform=ccrs.PlateCarree())

        # Optional labels inside inset
        if show_labels and label_col and (label_col in df.columns):
            for idx in clusters[cid]:
                axx.text(
                    float(df.iloc[idx]["Lon_DD"]), float(df.iloc[idx]["Lat_DD"]),
                    str(df.iloc[idx][label_col]), fontsize=label_fontsize,
                    transform=ccrs.PlateCarree(), ha="left", va="bottom",
                )

        # Ticks & frame
        axx.set_xticks([]); axx.set_yticks([])
        for spine in axx.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(frame_lw)

        # Optional connector from cluster centroid to inset center (figure coords)
        if link and adjacent:
            try:
                cx_fig, cy_fig = _data_to_fig_xy(ax_main, cx, cy)
                line = plt.Line2D(
                    [cx_fig, rect[0] + rect[2] / 2.0],
                    [cy_fig, rect[1] + rect[3] / 2.0],
                    transform=fig.transFigure, lw=0.6, alpha=0.6,
                )
                fig.add_artist(line)
            except Exception:
                pass

        axes.append(axx)

    return axes


