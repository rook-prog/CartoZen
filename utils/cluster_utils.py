# utils/cluster_utils.py
"""Greedy geographic clustering + helpers (no sklearn).

Usage in app.py (minimal):

from utils.cluster_utils import greedy_cluster

rep_df, clusters = greedy_cluster(df, lat_col="Lat_DD", lon_col="Lon_DD", threshold_km=12)
# plot with rep_df instead of df; clusters maps cluster_id -> original row indices

"""
from __future__ import annotations
import numpy as np
import pandas as pd

EARTH_R_KM = 6371.0088


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return EARTH_R_KM * c


def greedy_cluster(df: pd.DataFrame, lat_col: str = "Lat_DD", lon_col: str = "Lon_DD", threshold_km: float = 10.0):
    """Return (rep_df, clusters)

    - rep_df: one centroid row per cluster with columns: Lat_DD, Lon_DD, cluster_id, cluster_size
    - clusters: dict[int, list[int]] mapping cluster_id -> original df row indices

    Greedy single-linkage (O(n^2)), fine for up to a few thousand points.
    """
    coords = df[[lat_col, lon_col]].to_numpy()
    n = len(coords)
    unassigned = set(range(n))
    clusters: dict[int, list[int]] = {}
    cid = 0

    while unassigned:
        i = min(unassigned)
        unassigned.remove(i)
        members = [i]
        lat_i, lon_i = coords[i]
        # expand once around seed i
        for j in list(unassigned):
            lat_j, lon_j = coords[j]
            if _haversine_km(lat_i, lon_i, lat_j, lon_j) <= threshold_km:
                members.append(j)
                unassigned.remove(j)
        clusters[cid] = members
        cid += 1

    # build representatives
    rows = []
    for cid, idxs in clusters.items():
        sub = df.iloc[idxs]
        rows.append({
            "cluster_id": cid,
            "cluster_size": int(len(idxs)),
            "Lat_DD": float(sub[lat_col].mean()),
            "Lon_DD": float(sub[lon_col].mean()),
        })
    rep_df = pd.DataFrame(rows)
    return rep_df, clusters
