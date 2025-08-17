import geopandas as gpd
import tempfile

def overlay_gdf(file_obj):
    name = file_obj.name.lower()
    if name.endswith(".geojson"):
        return gpd.read_file(file_obj)
    elif name.endswith(".kml"):
        return gpd.read_file(f"/vsizip/{file_obj.name}")
    elif name.endswith(".zip"):
        tmp = tempfile.mktemp(suffix=".zip")
        with open(tmp, "wb") as f:
            f.write(file_obj.getbuffer())
        return gpd.read_file(f"zip://{tmp}")
    else:
        return gpd.read_file(file_obj)
