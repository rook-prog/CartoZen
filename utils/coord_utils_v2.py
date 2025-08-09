# utils/coord_utils_v2.py
# Robust coordinate conversion utilities for CartoZen
# - Auto-detects & fixes Degrees+Decimal Minutes (DMM) inside "Decimal Degrees" inputs
# - Parses DMS strings with N/S/E/W
# - Converts UTM (E, N, Zone, Hemisphere)
# - Always returns a DataFrame (never None)
# - Ensures numeric dtype before clip/round to avoid TypeError

import re
import numpy as np
import pandas as pd
import utm

# ─────────────────────────────────────────────────────────────────────────────
# Parsers & detectors
# ─────────────────────────────────────────────────────────────────────────────

def dms_to_dd(dms):
    """
    Parse DMS strings with cardinal letters (N/S/E/W) into decimal degrees.
    Examples: "20° 30' 15\" N", "72 30 15 W"
    Returns float or None on failure.
    """
    try:
        dms_clean = re.sub(r'[^\d\.NSEWnsew]+', ' ', str(dms)).strip()
        parts = dms_clean.split()
        direction = next((p.upper() for p in parts if p.upper() in ["N", "S", "E", "W"]), None)
        if not direction:
            return None
        nums = [float(p) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p)]
        deg = nums[0] if len(nums) > 0 else 0.0
        minute = nums[1] if len(nums) > 1 else 0.0
        second = nums[2] if len(nums) > 2 else 0.0
        dd = deg + minute / 60.0 + second / 3600.0
        return -dd if direction in ["S", "W"] else dd
    except Exception:
        return None


def dmm_to_dd(val):
    """
    Degrees + decimal-minutes -> decimal degrees.
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
    minutes = dec * 100.0
    return sign * (deg + minutes / 60.0)


def is_probably_dmm(val, kind="lat"):
    """
    Heuristic to flag values likely in DMM form:
    - numeric
    - degree bound valid (<=90 for lat, <=180 for lon)
    - decimal-part*100 < 60 (valid minutes)
    - differs noticeably if treated as DD vs DMM
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
        dd_as_dmm = dmm_to_dd(x)
        return abs(x - dd_as_dmm) > 0.05  # ~3 arc-min threshold
    return False


def _to_float_series(s: pd.Series) -> pd.Series:
    """
    Robust numeric coercion:
    - accepts comma decimal separators
    - strips spaces
    - returns NaN for non-numeric
    """
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(',', '.', regex=False),
        errors="coerce"
    )


def _auto_fix_dmm_inplace(df: pd.DataFrame, lat_col: str, lon_col: str) -> None:
    """
    Auto-detect & fix DMM values in-place for specific cells.
    Only a cell flagged by the heuristic is converted.
    """
    lat_mask = df[lat_col].apply(is_probably_dmm, kind="lat")
    if lat_mask.any():
        df.loc[lat_mask, lat_col] = df.loc[lat_mask, lat_col].apply(dmm_to_dd)

    lon_mask = df[lon_col].apply(is_probably_dmm, kind="lon")
    if lon_mask.any():
        df.loc[lon_mask, lon_col] = df.loc[lon_mask, lon_col].apply(dmm_to_dd)

# ─────────────────────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────────────────────
def loose_to_dd(val):
    """
    Best-effort parser for 'loose' coordinates:
    - Accepts: 72.3045  | 72 30.45 | 72°30.45' | 72 30 27 | '72° 30' 27"'
    - Returns decimal degrees (float) or NaN.
    """
    s = str(val).strip()
    if not s:
        return np.nan

    # Remove cardinal letters
    s = re.sub(r'[NnEeWw]', '', s)

    # Normalize degree/min/sec symbols to spaces, keep digits, dot, minus and spaces
    s = s.replace('°', ' ').replace('º', ' ')
    s = s.replace('′', ' ').replace("’", ' ').replace("'", ' ')
    s = s.replace('″', ' ').replace('”', ' ').replace('"', ' ')
    s = s.replace(',', '.')  # comma decimal to dot
    s = re.sub(r'[^0-9\.\-\s]', ' ', s)  # drop anything else
    parts = [p for p in s.split() if p]

    # 1 token: plain DD
    if len(parts) == 1:
        try:
            return float(parts[0])
        except Exception:
            return np.nan

    # 2–3 tokens: deg + minutes (+ seconds)
    try:
        deg = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0.0
        seconds = float(parts[2]) if len(parts) > 2 else 0.0
        dd = abs(deg) + minutes / 60.0 + seconds / 3600.0
        return -dd if deg < 0 else dd
    except Exception:
        return np.nan


def _fix_dmm_series(s: pd.Series, kind="lat") -> pd.Series:
    """
    Given a numeric-ish series, convert entries that 'look like' DMM to proper DD.
    """
    def _looks_dmm(x):
        try:
            return is_probably_dmm(x, kind=kind)
        except Exception:
            return False

    s = s.copy()
    mask = s.apply(_looks_dmm)
    if mask.any():
        s.loc[mask] = s.loc[mask].apply(dmm_to_dd)
    return s

def convert_coords(df, fmt, lat_col, lon_col):
    """
    Convert coordinates to decimal degrees with auto-cleaning.
    Returns a DataFrame with Lat_DD, Lon_DD (may be empty but never None).

    fmt:
      - "DMS": expects N/S/E/W style strings in lat_col/lon_col
      - "Decimal Degrees": accepts DD and auto-fixes cells that look like DMM
      - "UTM": expects first 4 columns as [E, N, Z, ZL] (hemisphere letter)
    """
    # Defensive input validation
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=["Lat_DD", "Lon_DD"])
    if lat_col not in df.columns or lon_col not in df.columns:
        return pd.DataFrame(columns=["Lat_DD", "Lon_DD"])

    df = df.copy()

    try:
        if fmt == "DMS":
            df["Lat_DD"] = df[lat_col].astype(str).apply(dms_to_dd)
            df["Lon_DD"] = df[lon_col].astype(str).apply(dms_to_dd)

        elif fmt == "Decimal Degrees":
            # Step 1: quick numeric coercion (handles commas/spaces)
            lat_num = _to_float_series(df[lat_col])
            lon_num = _to_float_series(df[lon_col])

            # Step 2: where still NaN, try loose parsing (tokens -> DD)
            lat_mask = lat_num.isna()
            if lat_mask.any():
                lat_num.loc[lat_mask] = df.loc[lat_mask, lat_col].apply(loose_to_dd)

            lon_mask = lon_num.isna()
            if lon_mask.any():
                lon_num.loc[lon_mask] = df.loc[lon_mask, lon_col].apply(loose_to_dd)

            # Step 3: auto-fix true DMM values
            lat_num = _fix_dmm_series(lat_num, kind="lat")
            lon_num = _fix_dmm_series(lon_num, kind="lon")

            # Assign to output columns
            df["Lat_DD"] = lat_num
            df["Lon_DD"] = lon_num)

        else:  # UTM
            # Expect first four columns as E, N, Z, ZL (hemisphere letter)
            try:
                df[["E", "N", "Z", "ZL"]] = df.iloc[:, :4]
            except Exception:
                # If missing, return empty result with expected columns
                return pd.DataFrame(columns=["Lat_DD", "Lon_DD"])

            df[["Lat_DD", "Lon_DD"]] = df.apply(
                lambda r: pd.Series(utm.to_latlon(r.E, r.N, int(r.Z), r.ZL)),
                axis=1
            )

        # Final cleanup: ensure numeric -> dropna -> clip -> round
        df["Lat_DD"] = pd.to_numeric(df["Lat_DD"], errors="coerce")
        df["Lon_DD"] = pd.to_numeric(df["Lon_DD"], errors="coerce")

        df = df.dropna(subset=["Lat_DD", "Lon_DD"]).copy()
        df["Lat_DD"] = df["Lat_DD"].clip(-90, 90).round(4)
        df["Lon_DD"] = df["Lon_DD"].clip(-180, 180).round(4)

    except Exception:
        # On any unexpected failure, return an empty but well-formed DataFrame
        return pd.DataFrame(columns=["Lat_DD", "Lon_DD"])

    return df


def get_buffered_extent(df, buffer_deg=5):
    """
    Returns [min_lon, max_lon, min_lat, max_lat] with a buffer
    around station coordinates. Assumes df has Lat_DD/Lon_DD.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return [-180, 180, -90, 90]

    min_lon = max(np.floor(df['Lon_DD'].min()) - buffer_deg, -180)
    max_lon = min(np.ceil(df['Lon_DD'].max()) + buffer_deg, 180)
    min_lat = max(np.floor(df['Lat_DD'].min()) - buffer_deg, -90)
    max_lat = min(np.ceil(df['Lat_DD'].max()) + buffer_deg, 90)
    return [min_lon, max_lon, min_lat, max_lat]
