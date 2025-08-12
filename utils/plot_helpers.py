import matplotlib.patches as mpatches
from math import cos, radians
from matplotlib.ticker import FuncFormatter

def dd_fmt_lon(x, pos): return f"{abs(x):.2f}°{'E' if x >= 0 else 'W'}"

def dd_fmt_lat(y, pos): return f"{abs(y):.2f}°{'N' if y >= 0 else 'S'}"

def dms_fmt_lon(x, pos):
    d, m, s = int(abs(x)), int((abs(x) % 1) * 60), int((((abs(x) % 1) * 60) % 1) * 60)
    return f"{d}°{m}'{s}\"{'E' if x >= 0 else 'W'}"

def dms_fmt_lat(y, pos):
    d, m, s = int(abs(y)), int((abs(y) % 1) * 60), int((((abs(y) % 1) * 60) % 1) * 60)
    return f"{d}°{m}'{s}\"{'N' if y >= 0 else 'S'}"

def draw_scale_bar(ax, bounds, length_km, segments, thickness, pos, unit, fontsize,
                   fontweight=None, fontstyle=None):
    from cartopy import crs as ccrs
    rx, ry = {"Bottom-Left": (0.05, 0.05), "Bottom-Right": (0.75, 0.05),
              "Top-Left": (0.05, 0.95), "Top-Right": (0.75, 0.95)}[pos]
    lon0 = bounds[0] + rx * (bounds[1] - bounds[0])
    lat0 = bounds[2] + ry * (bounds[3] - bounds[2])
    kmdeg = 111.32 * cos(radians(lat0))
    width = length_km / kmdeg
    seg = width / segments
    for i in range(segments):
        color = "black" if i % 2 == 0 else "white"
        ax.add_patch(mpatches.Rectangle((lon0 + i * seg, lat0), seg, 0.01 * thickness,
                    transform=ccrs.PlateCarree(), fc=color, ec="black", zorder=5))
    ax.text(lon0 + width / 2, lat0 + 0.02 * thickness, unit,
            ha="center", fontsize=fontsize, transform=ccrs.PlateCarree(),
            fontweight=fontweight, fontstyle=fontstyle)
    for i in range(segments + 1):
        ax.text(lon0 + i * seg, lat0 - 0.01 * thickness, f"{int(i * length_km / segments)}",
                ha="center", va="top", fontsize=fontsize, transform=ccrs.PlateCarree(),
                fontweight=fontweight, fontstyle=fontstyle)
