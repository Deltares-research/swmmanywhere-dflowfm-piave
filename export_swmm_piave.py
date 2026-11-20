"""Prepare HydroMT-Delft3DFM inputs from SWMManywhere's Piave network.

Runs in the SWMManywhere environment (see build_swmm_piave.py) after
build_swmm_piave.py. It uses only packages that SWMManywhere already depends on
(geopandas, numpy, pandas, pyarrow, rasterio, scipy and shapely); install any that
your environment lacks.

Writes GeoJSON files and a HydroMT data catalog to hydromt_inputs_piave/, so that
the D-Flow FM model can be built from dflowfm_build_piave_swm.yml with HydroMT
(build_dflowfm_piave_withfixes.py).

Mapping (SWMManywhere writes SWMM conduits with zero offsets):
- pipe invlev_up/invlev_dn = chamber_floor_elevation of its upstream/downstream node
- manhole bedlevel = chamber_floor_elevation, streetlevel = surface_elevation
- outfalls paired with a real river: a straight connector pipe to the nearest point on
  the river, where the river is split so that the connector ends on a river node
- outfalls paired with a SWMManywhere "dummy river": a short outlet pipe, whose end
  node gets a water-level boundary in the build yml
- rivers: OSM waterways downloaded by SWMManywhere, split into reaches of at most
  RIVER_REACH; bed level = DEM at the reach midpoint minus RIVER_DEPTH (placeholder)

Usage:
    python export_swmm_piave.py
"""

import json
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage
from shapely import STRtree
from shapely.geometry import LineString, Point, box
from shapely.ops import substring

from swmmanywhere.utilities import load_graph

HERE = Path(__file__).parent
BBOX_DIR = HERE / "swmm_piave" / "bbox_1"
MODEL = BBOX_DIR / "model_1"
DEM = BBOX_DIR / "download" / "elevation.tif"
OUT = HERE / "hydromt_inputs_piave"

RIVER_REACH = 50.0  # m, max river reach length so that bed levels follow the DEM
RIVER_DEPTH = 1.0  # m below DEM, placeholder
RIVER_WIDTH = 4.0  # m, placeholder (all OSM waterways here are mountain streams)
RIVER_HEIGHT = 2.5  # m, placeholder
RIVER_DEM_MARGIN = 30.0  # m, rivers are clipped to the DEM extent minus this margin
MESH_DEM_MARGIN = 60.0  # m, 2D mesh inside the DEM: two 25 m cells plus half a pixel
REGION_BUFFER = 150.0  # m, 1D model region around the pipe network
OUTLET_STUB = 10.0  # m, outlet pipe length at dummy outfalls
OUTLET_SLOPE = 0.005  # -, outlet pipe slope
JUNCTION_END_SNAP = 1.0  # m, connect to the river end node if the junction is closer


# ------------------------------------------------------------------ DEM
with rasterio.open(DEM) as src:
    dem = src.read(1).astype(float)
    transform = src.transform
    dem_bounds = src.bounds
    dem_nodata = src.nodata
if dem_nodata is not None and (dem == dem_nodata).any():
    # Fill the reprojection edges with the nearest valid value
    idx = ndimage.distance_transform_edt(
        dem == dem_nodata, return_distances=False, return_indices=True
    )
    dem = dem[tuple(idx)]


def sample_dem(points):
    """Nearest-pixel DEM value at shapely points."""
    x = np.array([p.x for p in points])
    y = np.array([p.y for p in points])
    col = np.clip(np.floor((x - transform.c) / transform.a).astype(int), 0, dem.shape[1] - 1)
    row = np.clip(np.floor((y - transform.f) / transform.e).astype(int), 0, dem.shape[0] - 1)
    return dem[row, col]


def split_line(line, max_length):
    n = max(1, int(np.ceil(line.length / max_length)))
    step = line.length / n
    return [substring(line, i * step, (i + 1) * step) for i in range(n)]


# ------------------------------------------------------------------ SWMManywhere network
nodes = gpd.read_parquet(MODEL / "nodes.geoparquet")
edges = gpd.read_parquet(MODEL / "edges.geoparquet")
CRS = nodes.crs
nodes["id"] = nodes["id"].astype(str)
edges["u"] = edges["u"].astype(str)
edges["v"] = edges["v"].astype(str)
nodes = nodes.set_index("id", drop=False)
floor = nodes["chamber_floor_elevation"].astype(float)
STATS = {}

# Orient pipe geometry from u to v
starts_at_u = [
    Point(g.coords[0]).distance(nodes.loc[u, "geometry"])
    <= Point(g.coords[-1]).distance(nodes.loc[u, "geometry"])
    for g, u in zip(edges.geometry, edges["u"])
]
edges["geometry"] = [
    g if ok else LineString(g.coords[::-1]) for g, ok in zip(edges.geometry, starts_at_u)
]

outfall_edges = gpd.read_file(MODEL / "identify_outfalls_edges.geojson")
outfall_edges = outfall_edges[outfall_edges["edge_type"] == "outfall"]
dummy = outfall_edges["v"].astype(str).str.contains("dummy")
real_outfalls = set(outfall_edges.loc[~dummy, "u"].astype(str))
outfall_nodes = nodes.loc[~nodes["id"].isin(edges["u"]) & nodes["id"].isin(edges["v"])]
STATS["outfalls"] = len(outfall_nodes)
STATS["outfalls_to_river"] = int(outfall_nodes["id"].isin(real_outfalls).sum())

# ------------------------------------------------------------------ rivers
graph = load_graph(BBOX_DIR / "download" / "river.json")
river = gpd.GeoDataFrame(
    {"reversed": [str(d.get("reversed")) for _, _, d in graph.edges(data=True)]},
    geometry=[d["geometry"] for _, _, d in graph.edges(data=True)],
    crs=graph.graph["crs"],
).to_crs(CRS)
# OSMnx adds a reversed copy of every waterway; keep the digitised (flow) direction
river = river[river["reversed"] == "False"]
key = river.geometry.apply(lambda line: min(tuple(line.coords), tuple(line.coords[::-1])))
river = river.loc[~key.duplicated()]
dem_extent = box(*dem_bounds).buffer(-RIVER_DEM_MARGIN, join_style=2)
river = gpd.clip(river, dem_extent).explode(index_parts=False)
river_lines = [g for g in river.geometry if g.geom_type == "LineString" and g.length > 0]

# Connectors from real outfalls to the nearest point on a river
tree = STRtree(river_lines)
split_at = defaultdict(set)
connectors = []
for node_id, node in outfall_nodes[outfall_nodes["id"].isin(real_outfalls)].iterrows():
    i = int(tree.nearest(node.geometry))
    line = river_lines[i]
    dist = line.project(node.geometry)
    if dist < JUNCTION_END_SNAP:
        dist = 0.0
    elif line.length - dist < JUNCTION_END_SNAP:
        dist = line.length
    else:
        split_at[i].add(dist)
    junction = line.interpolate(dist)
    connectors.append(
        {
            "branchid": f"outfall_{node_id}",
            "branchtype": "pipe",
            "shape": "circle",
            "diameter": float(edges.loc[edges["v"] == node_id, "diameter"].max()),
            "invlev_up": floor.loc[node_id],
            "invlev_dn": float(sample_dem([junction])[0] - RIVER_DEPTH),
            "geometry": LineString([node.geometry, junction]),
        }
    )
connectors = gpd.GeoDataFrame(connectors, crs=CRS)
STATS["connector_length_m"] = connectors.length.round(1).tolist()
STATS["connectors_uphill"] = int((connectors.invlev_dn > connectors.invlev_up).sum())

# Split rivers at the connector junctions, then into short reaches
reaches = []
for i, line in enumerate(river_lines):
    cuts = sorted({0.0, line.length, *split_at[i]})
    for start, end in zip(cuts[:-1], cuts[1:]):
        reaches.extend(split_line(substring(line, start, end), RIVER_REACH))
reaches = gpd.GeoSeries(reaches, crs=CRS)
rivers = gpd.GeoDataFrame(
    {
        "branchid": [f"river_{i}" for i in range(len(reaches))],
        "branchtype": "river",
        "shape": "rectangle",
        "width": RIVER_WIDTH,
        "t_width": RIVER_WIDTH,
        "height": RIVER_HEIGHT,
        "bedlev": sample_dem(reaches.interpolate(0.5, normalized=True)) - RIVER_DEPTH,
        "closed": "no",
    },
    geometry=reaches.values,
    crs=CRS,
)
STATS["river_reaches"] = len(rivers)
STATS["river_km"] = round(rivers.length.sum() / 1000, 3)

# ------------------------------------------------------------------ pipes
pipes = gpd.GeoDataFrame(
    {
        "branchid": [f"pipe_{u}_{v}" for u, v in zip(edges["u"], edges["v"])],
        "branchtype": "pipe",
        "shape": "circle",
        "diameter": edges["diameter"].astype(float).values,
        "invlev_up": floor.loc[edges["u"]].values,
        "invlev_dn": floor.loc[edges["v"]].values,
    },
    geometry=edges.geometry.values,
    crs=CRS,
)
STATS["swm_pipes"] = len(pipes)

# Outlet pipes at dummy outfalls (SWMManywhere also adds an outfall link in SWMM):
# a 1D boundary needs an end node with a single pipe, but the lowest node of a tree
# can be a junction.
stubs = []
for node_id, node in outfall_nodes[~outfall_nodes["id"].isin(real_outfalls)].iterrows():
    incoming = edges[edges["v"] == node_id]
    (x0, y0), (x1, y1) = incoming.geometry.iloc[0].coords[-2:]
    direction = np.array([x1 - x0, y1 - y0]) / np.hypot(x1 - x0, y1 - y0)
    end = Point(np.array(node.geometry.coords[0]) + OUTLET_STUB * direction)
    stubs.append(
        {
            "branchid": f"outlet_{node_id}",
            "branchtype": "pipe",
            "shape": "circle",
            "diameter": float(incoming["diameter"].max()),
            "invlev_up": floor.loc[node_id],
            "invlev_dn": floor.loc[node_id] - OUTLET_SLOPE * OUTLET_STUB,
            "geometry": LineString([node.geometry, end]),
        }
    )
stubs = gpd.GeoDataFrame(stubs, crs=CRS)
STATS["outlet_pipes"] = len(stubs)
pipes = gpd.GeoDataFrame(pd.concat([pipes, stubs, connectors], ignore_index=True), crs=CRS)

# ------------------------------------------------------------------ manholes
manholes = gpd.GeoDataFrame(
    {
        "manholeid": nodes["id"].values,
        "bedlevel": floor.values,
        "streetlevel": nodes["surface_elevation"].astype(float).values,
    },
    geometry=nodes.geometry.values,
    crs=CRS,
)
STATS["manholes"] = len(manholes)

# ------------------------------------------------------------------ regions
region_1d = box(*pipes.total_bounds).buffer(REGION_BUFFER, join_style=2)
region_2d = box(*dem_bounds).buffer(-MESH_DEM_MARGIN, join_style=2)

# ------------------------------------------------------------------ write
OUT.mkdir(exist_ok=True)
for name, gdf in {
    "pipes": pipes,
    "rivers": rivers,
    "manholes": manholes,
    "region_1d": gpd.GeoDataFrame(geometry=[region_1d], crs=CRS),
    "region_2d": gpd.GeoDataFrame(geometry=[region_2d], crs=CRS),
}.items():
    path = OUT / f"{name}.geojson"
    path.unlink(missing_ok=True)
    gdf.to_file(path, driver="GeoJSON")

epsg = CRS.to_epsg()
swm_url = "https://github.com/ImperialCollegeLondon/SWMManywhere"
catalog = f"""\
# HydroMT data catalog for the SWMManywhere Piave network, written by export_swmm_piave.py.
# Relative uris are resolved from the folder of this file.
swm_pipes:
  data_type: GeoDataFrame
  uri: pipes.geojson
  driver:
    name: pyogrio
  metadata:
    crs: {epsg}
    category: sewer
    source_url: {swm_url}
swm_rivers:
  data_type: GeoDataFrame
  uri: rivers.geojson
  driver:
    name: pyogrio
  metadata:
    crs: {epsg}
    category: hydrography
    source_url: https://www.openstreetmap.org
swm_manholes:
  data_type: GeoDataFrame
  uri: manholes.geojson
  driver:
    name: pyogrio
  metadata:
    crs: {epsg}
    category: sewer
    source_url: {swm_url}
swm_dem:
  data_type: RasterDataset
  uri: ../swmm_piave/bbox_1/download/elevation.tif
  driver:
    name: rasterio
  metadata:
    crs: {epsg}
    category: topography
    source_url: https://planetarycomputer.microsoft.com/dataset/nasadem
  data_adapter:
    rename:
      elevation: elevtn
"""
(OUT / "data_catalog.yml").write_text(catalog, encoding="utf-8")
(OUT / "export_stats.json").write_text(json.dumps(STATS, indent=1))
print(json.dumps(STATS, indent=1))
