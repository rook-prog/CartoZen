import pandas as pd
import utm
import re

def dms_to_dd(dms):
    try:
        dms_clean = re.sub(r'[^\d\.NSEWnsew]+', ' ', dms).strip()
        parts = dms_clean.split()
        direction = next((p.upper() for p in parts if p.upper() in ["N", "S", "E", "W"]), None)
        if not direction:
            return None
        nums = [float(p) for p in parts if re.match(r'^-?\d+(\.\d+)?$', p)]
        deg = nums[0] if len(nums) > 0 else 0
        min_ = nums[1] if len(nums) > 1 else 0
        sec = nums[2] if len(nums) > 2 else 0
        dd = deg + min_ / 60 + sec / 3600
        return -dd if direction in ["S", "W"] else dd
    except:
        return None

def convert_coords(df, fmt, lat_col, lon_col):
    if fmt == "DMS":
        df["Lat_DD"] = df[lat_col].astype(str).apply(dms_to_dd)
        df["Lon_DD"] = df[lon_col].astype(str).apply(dms_to_dd)
    elif fmt == "Decimal Degrees":
        df["Lat_DD"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["Lon_DD"] = pd.to_numeric(df[lon_col], errors="coerce")
    else:
        df[["E", "N", "Z", "ZL"]] = df.iloc[:, :4]
        df[["Lat_DD", "Lon_DD"]] = df.apply(lambda r: pd.Series(
            utm.to_latlon(r.E, r.N, int(r.Z), r.ZL)), axis=1)
    return df.dropna(subset=["Lat_DD", "Lon_DD"])
