# coord_utils.py

import pandas as pd
import utm
import re
import numpy as np

# ----------------------------- Helpers: parsing & detection -----------------------------

def dms_to_dd(dms):
    """
    Parse strings like: 20° 30' 15" N, 72 30 15 W, etc. -> decimal degrees.
    Returns None if no N/S/E/W direction found.
    """
    try:
        dms_clean = re.sub(r'[^\d\.NSEWnsew]+', ' ', str(dms)).strip()
        parts = dms_clean.split()
        direction = next((p.upper() for p in parts if p.upper() in ["N", "S", "E", "W"]), None)
        if not direction:
            return None
        nums = [float(p) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p)]
        deg = nums[0] if len(nums) > 0 else 0.0
        min_ = nums[1] if len(nums) > 1 else 0.0
        sec = nums[2] if len(nums) > 2 else 0.0
        dd = deg + min_ / 60.0 + sec / 3600.0
        return -dd if direction in ["S", "W"] else dd
    except Exception:
        return None


def dmm_to_dd(val):
    """
    Degrees + decimal-minutes (DMM) -> decimal degrees.
    Example: 72.3045 means 72° 30.45' -> 72 + 30.45/60
    """
    try:
        x = float(val)
    except Exception:
        return np.nan

    sign = -1.0 if x < 0 else 1.0
    ax = abs(x)
    deg = int(np.floor(ax))
    dec = ax - deg
    minutes = dec * 100.0  # decimal part encodes minutes
    dd = deg + (minutes / 60.0)
    return sign * dd


def is_probably_dmm(val, kind="lat"):
    """
    Heuristic detection for DMM:
    - value is numeric,
    - degrees within bounds (<=90 for lat, <=180 for lon),
    - decimal-part*100 < 60 (valid minutes),
    - and differs noticeably from treating it as DD (helps catch mixed rows).
    """
    try:
        x = float(val)
    except Exception:
        return False

    ax = abs(x)
    deg = int(np.floor(ax))
    dec = ax - deg
    minutes = dec * 100.0

    if kind == "lat":
        if deg > 90:
            return False
    else:
        if deg > 180:
            return False

    if 0.0 <= minutes < 60.0:
        dd_as_dd = x
        dd_as_dmm = dmm_to_dd(x)
        return abs(dd_as_dd - dd_as_dmm) > 0.05  # ~3 arc-min difference
    return False


def _to_float_series(s: pd.Series) -> pd.Series:
    """
    Robust numeric coercion:
    - accepts comma decimal separators,
    - strips spaces,
    - returns NaN for non-numeric.
    """
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(',', '.', regex=False),
        errors="coerce"
    )


def _auto_fix_dmm_inplace(df: pd.DataFrame, lat_col: str, lon_col: str) -> None:
    """
    Auto-detect and fix DMM cells IN-PLACE for the provided lat/lon columns.
    Only converts a cell if that specific cell looks like DMM.
    """
    # Fix latitude cells that look like DMM
    lat_mask = df[lat_col].apply(is_probably_dmm, kind="lat")
    if lat_mask.any():
        df.loc[lat_mask, lat_col] = df.loc[lat_mask, lat_col].apply(dmm_to_dd)

    # Fix longitude cells that look like DMM
    lon_mask = df[lon_col].apply(is_probably_dmm, kind="lon")
    if lon_mask.any():
        df.loc[lon_mask, lon_col] = df.loc[lon_mask, lon_col].apply(dmm_to_dd)


# ----------------------------- Main converter -----------------------------

def convert_coords(df, fmt, lat_col, lon_col):
    """
    Convert coordinates to decimal degrees with auto-cleaning:
    - fmt == "DMS": parse DMS strings using N/S/E/W.
    - fmt == "Decimal Degrees": ALWAYS auto-detect & fix DMM cells, then coerce to float.
    - else (UTM): expects first 4 columns as E, N, Z, ZL and converts via utm.to_latlon.

    Returns df with Lat_DD, Lon_DD (rounded to 4 dp), rows with NaNs dropped.
    """
    df = df.copy()

    if fmt == "DMS":
        df["Lat_DD"] = df[lat_col].astype(str).apply(dms_to_dd)
        df["Lon_DD"] = df[lon_col].astype(str).apply(dms_to_dd)

    elif fmt == "Decimal Degrees":
        # 1) Try to fix any mixed-in DMM cells (works on original text)
        _auto_fix_dmm_inplace(df, lat_col, lon_col)

        # 2) Coerce to floats robustly (handles comma decimals, stray spaces)
        df["Lat_DD"] = _to_float_series(df[lat_col])
        df["Lon_DD"] = _to_float_series(df[lon_col])

    else:  # UTM branch (assumes first four columns are E, N, Z, ZL)
        df[["E", "N", "Z", "ZL"]] = df.iloc[:, :4]
        df[["Lat_DD", "Lon_DD"]] = df.apply(
            lambda r: pd.Series(utm.to_latlon(r.E, r.N, int(r.Z), r.ZL)), axis=1
        )

    # Final cleanup: drop incomplete, clip to valid ranges, standardize precision
    df = df.dropna(subset=["Lat_DD", "Lon_DD"]).copy()
    df["Lat_DD"] = df["Lat_DD"].clip(-90, 90).round(4)
    df["Lon_DD"] = df["Lon_DD"].clip(-180, 180).round(4)
    return df


# ----------------------------- Map extent helper -----------------------------

def get_buffered_extent(df, buffer_deg=5):
    """
    Returns a bounding box [min_lon, max_lon, min_lat, max_lat] with a buffer
    around station coordinates. Assumes df has 'Lat_DD' and 'Lon_DD'.
    """
    min_lon = max(np.floor(df['Lon_DD'].min()) - buffer_deg, -180)
    max_lon = min(np.ceil(df['Lon_DD'].max()) + buffer_deg, 180)
    min_lat = max(np.floor(df['Lat_DD'].min()) - buffer_deg, -90)
    max_lat = min(np.ceil(df['Lat_DD'].max()) + buffer_deg, 90)
    return [min_lon, max_lon, min_lat, max_lat]
