# D-Flow FM sewer model for Piave from SWMManywhere

This repository builds a 1D2D D-Flow FM model of a synthetic urban drainage network for the Piave example area. It is part of [Deltares/hydromt_delft3dfm#364](https://github.com/Deltares/hydromt_delft3dfm/issues/364), which uses [SWMManywhere](https://github.com/ImperialCollegeLondon/SWMManywhere) (Dobson et al., 2025) as a benchmark for the urban sewer workflow.

## Workflow

| Step | What | Scripts | Environment | Output |
|---|---|---|---|---|
| 1 | Build and run a SWMM model with SWMManywhere | [build_swmm_piave.py](build_swmm_piave.py), [run_swmm_piave.py](run_swmm_piave.py) | SWMManywhere | `swmm_piave/bbox_1/model_1/` |
| 2 | Prepare the data for HydroMT | [export_swmm_piave.py](export_swmm_piave.py) | SWMManywhere | `hydromt_inputs_piave/` |
| 3 | Build and run the D-Flow FM model, with temporary fixes | [build_dflowfm_piave_withfixes.py](build_dflowfm_piave_withfixes.py), [run_dflowfm_piave.py](run_dflowfm_piave.py) | HydroMT-Delft3DFM, plus DIMR | `dflowfm_piave/` |

The repository includes the frozen inputs and outputs of steps 1 and 2, so step 3 can be run straight away.

The temporary fixes in step 3 cover two HydroMT-Delft3DFM bugs:

- [#365](https://github.com/Deltares/hydromt_delft3dfm/issues/365): ring filter tolerance, fixed in PR [#366](https://github.com/Deltares/hydromt_delft3dfm/pull/366);
- [#367](https://github.com/Deltares/hydromt_delft3dfm/issues/367): 1D–2D links at boundary nodes.

Once both are fixed, step 3 becomes a plain `hydromt build`.

## Quick start

From the repository folder:

```
:: Steps 1 and 2: environment with SWMManywhere (see Step 1)
python build_swmm_piave.py
python run_swmm_piave.py
python export_swmm_piave.py

:: Step 3: environment with HydroMT-Delft3DFM (see Step 3)
:: Set DIMR_LATEST in run_dflowfm_piave.py first
python build_dflowfm_piave_withfixes.py
python run_dflowfm_piave.py
```

## Files

| File | Step | Purpose |
|---|---|---|
| [build_swmm_piave.py](build_swmm_piave.py) | 1 | SWMManywhere configuration and network build |
| [run_swmm_piave.py](run_swmm_piave.py) | 1 | Runs the SWMM model |
| `swmm_piave/bbox_1/download/` | 1 | Frozen input data: DEM, buildings, streets and rivers |
| `swmm_piave/bbox_1/model_1/` | 1 | Frozen SWMManywhere outputs that step 2 reads (`nodes`, `edges`, `identify_outfalls_edges`), plus `subcatchments` and the resolved `config.yml`. A run also writes the graph after every step, the SWMM model and its results; `.gitignore` excludes those. |
| [export_swmm_piave.py](export_swmm_piave.py) | 2 | Writes `hydromt_inputs_piave/` |
| `hydromt_inputs_piave/` | 2 | GeoJSON inputs, `data_catalog.yml` and `export_stats.json` |
| [dflowfm_build_piave_swm.yml](dflowfm_build_piave_swm.yml) | 3 | HydroMT build configuration |
| [build_dflowfm_piave_withfixes.py](build_dflowfm_piave_withfixes.py) | 3 | Temporary fixes for #365 and #367, then `hydromt build` |
| [run_dflowfm_piave.py](run_dflowfm_piave.py) | 3 | Runs the model with DIMR |
| `dflowfm_piave/` | 3 | Built model and results, excluded by `.gitignore` |

---

## Step 1. Build and run a SWMM model with SWMManywhere

All network logic in this step is SWMManywhere's own code, run with its default settings. The scripts only set the area and the output folder.

### Installation

Install SWMManywhere following its [documentation](https://imperialcollegelondon.github.io/SWMManywhere/quickstart/):

```
pip install swmmanywhere
```

Tested with Python 3.12 and these packages:

| Package | Version |
|---|---|
| swmmanywhere | 0.2.4 (from PyPI; conda-forge only had 0.2.2, which predates the fix to the Overture building download in 0.2.3) |
| pyswmm / swmm-toolkit | 2.0.1 / 0.17.0 |
| pywbt | 0.3.0 |
| osmnx | 2.2.0 |
| networkx | 3.7 |
| geopandas | 1.2.0 |
| planetary-computer | 1.0.0 |

### Build: [build_swmm_piave.py](build_swmm_piave.py)

The script passes a minimal configuration to `swmmanywhere.swmmanywhere.swmmanywhere()`:

| Key | Value | Meaning |
|---|---|---|
| `base_dir` | Repository folder | Output root |
| `project` | `swmm_piave` | Project folder name |
| `bbox` | `[12.448261, 46.472383, 12.472671, 46.484434]` | West, south, east, north (EPSG:4326). Same extent as the Piave OSM example build. |
| `bbox_number`, `model_number` | `1`, `1` | Output subfolders `bbox_1/model_1` |
| `run_model` | `False` | The SWMM model is run with `run_swmm_piave.py` |

Nothing else is set:

- **No `parameter_overrides`.** All parameters keep their SWMManywhere defaults.
- **No `starting_graph`.** Streets and rivers come from OpenStreetMap through SWMManywhere's own download. The frozen files in `examples/data/piave_data/` of HydroMT-Delft3DFM are not used.
- **No `real` network.** SWMManywhere computes no comparison metrics.

`set_verbose(True)` makes SWMManywhere save the graph after every step. Step 2 needs one of these, `identify_outfalls_edges.geojson`, to tell real from dummy outfalls. The fully resolved configuration, including the default step list and the rainfall file, is written to `model_1/config.yml`.

With the committed downloads, a build takes about 15 s and reproduces the committed network exactly.

### Data downloads

SWMManywhere fetches its input data into `swmm_piave/bbox_1/download/` and reprojects it to UTM zone 33N (EPSG:32633). Files that already exist are not downloaded again, so the committed files are reused. Delete that folder to download fresh data, which may differ because OpenStreetMap changes.

| File | Source | Details | Download time |
|---|---|---|---|
| `elevation.tif` | NASADEM from the Microsoft Planetary Computer | About 23.5 m pixels after reprojection | ~3 s |
| `building.geoparquet` | Overture Maps buildings, latest release | Used for impervious area | ~80 s |
| `street.json` | OpenStreetMap via OSMnx `graph_from_bbox(..., truncate_by_edge=True)` | Network types `walk` and `drive` (default `allowable_networks`), merged into one graph | ~140 s |
| `river.json` | OpenStreetMap via OSMnx `graph_from_bbox(custom_filter='["waterway"]', retain_all=True)` | Four small streams (Rio Rive, Cridola, Sanavoi, Ramaiò), not the Piave itself | ~6.5 min |

The Overpass downloads were slow, and the river download once failed with an SSL error before succeeding on a restart.

Precipitation is not downloaded: that call is disabled in SWMManywhere 0.2.4. The SWMM model uses the bundled design storm `swmmanywhere/defs/storm.dat`: intensities of 28, 32 and 3 mm/h in 5-minute steps, about 5.3 mm in 15 minutes.

### Network derivation

The streets and rivers are combined into one starting graph. SWMManywhere then applies its default graph functions in this order (`graphfcn_list` in `config.yml`).

| # | Graph function | What it does (default parameters) |
|---|---|---|
| 1 | `assign_id` | Gives every edge a unique `id`. |
| 2 | `fix_geometries` | Recalculates edge geometries from node coordinates. |
| 3 | `remove_non_pipe_allowable_links` | Removes edges where pipes are not allowed: `motorway`, `motorway_link`, `bridge`, `tunnel`, `corridor`. |
| 4 | `calculate_streetcover` | Street width from the number of lanes × 3.5 m. Only `drive` streets count as impervious. Written to `streetcover.geoparquet`. |
| 5 | `remove_parallel_edges` | Keeps the shortest of any parallel edges. |
| 6 | `to_undirected` | Converts to an undirected graph. |
| 7 | `split_long_edges` | Splits streets into segments of at most 60 m (`max_street_length`). |
| 8 | `merge_street_nodes` | Merges street nodes within 10 m (`node_merge_distance`). |
| 9 | `assign_id` | Reassigns ids after merging. |
| 10 | `clip_to_catchments` | Derives DEM subbasins and removes street links between them (`subbasin_clip_method = subbasin`). Written to `subbasins.geoparquet`. |
| 11 | `calculate_contributing_area` | Derives a subcatchment per node from the DEM, with impervious area from buildings and street cover. Written to `subcatchments.geoparquet`. |
| 12 | `set_elevation` | Sets node elevation from the DEM. |
| 13 | `double_directed` | Adds a reverse copy of every edge, so flow direction can be chosen. |
| 14 | `fix_geometries` | Recalculates geometries for the new edges. |
| 15 | `set_surface_slope` | Surface slope per edge from node elevations. |
| 16 | `set_chahinian_slope` | Slope-based weight after Chahinian et al. (2019). |
| 17 | `set_chahinian_angle` | Angle-based weight after Chahinian et al. (2019). |
| 18 | `calculate_weights` | Combines the weights. Default scalings: slope 1, length 0.1, contributing area 0.1, angle 0. |
| 19 | `identify_outfalls` | Pairs street nodes with the nearest river node within 150 m (`river_buffer_distance`). A subnetwork with no river in range gets a "dummy river" at its lowest node. |
| 20 | `derive_topology` | Method `separate`: Dijkstra shortest path from every node to its nearest outfall, giving one tree per outfall. |
| 21 | `pipe_by_pipe` | Hydraulic design from upstream to downstream (see below). |
| 22 | `fix_geometries` | Final geometry fix. |
| 23 | `assign_id` | Final ids. |

`pipe_by_pipe` designs each pipe with these defaults:

- **Diameters:** 0.15–3.0 m in steps of 0.075 m.
- **Constraints:** filling ratio ≤ 0.8, velocity 0.75–5 m/s, wall shear stress ≥ 2 Pa, excavation depth 0.5–5 m.
- **Roughness:** Manning n = 0.012, fixed in the code.
- **Design flow:** contributing area × 0.006 m/h (6 mm/h, constant). The parameter is documented as a depth, but `calculate_flow` uses it as an hourly rate.

SWMManywhere then writes `model_1.inp`. It routes flow with dynamic waves, has zero link offsets, and adds an artificial outfall node for every outfall.

### Run: [run_swmm_piave.py](run_swmm_piave.py)

The script runs `model_1.inp` with SWMManywhere's `run` function (pyswmm) and its default run settings: 24 h with the bundled design storm, storing node flooding and link flow every 100 SWMM steps. The results are written to `model_1/results.parquet`, as SWMManywhere does itself with `run_model = True`.

### Outputs used in step 2

All outputs are in `swmm_piave/bbox_1/`, in EPSG:32633.

| File | Content |
|---|---|
| `model_1/nodes.geoparquet` | 601 nodes: `id`, `x`, `y`, `contributing_area`, `surface_elevation`, `chamber_floor_elevation`, `outfall`, `shortest_path` |
| `model_1/edges.geoparquet` | 560 pipes (15.0 km): `u`, `v`, `diameter`, `length`, `edge_type`, `cost_usd` and OSM attributes |
| `model_1/identify_outfalls_edges.geojson` | Outfall edges; `v` contains `dummy` for artificial outfalls |
| `download/river.json` | OSM waterway graph |
| `download/elevation.tif` | NASADEM |

`model_1/subcatchments.geoparquet` (593 subcatchments with `area`, `impervious_area`, `rc`, `slope`, `width`) is not used yet.

### Result for Piave

The network is the unmodified default result.

| Measure | Value |
|---|---|
| Pipes / nodes | 560 (15.0 km) / 601 |
| Street length removed by `clip_to_catchments` | 21.3 → 16.6 km |
| Outfalls | 40, of which 10 connect to a real stream and 30 drain to a dummy river |
| Pipes running uphill (invert) | 104 (19%) |
| Pipes at the minimum diameter (0.15 m) / at the maximum (3.0 m) | 403 / 7 |
| Downstream pipe smaller than an upstream pipe | 87 of 507 |

In this steep area the defaults give many artificial outfalls and uphill pipes. Parameters worth testing in a follow-up are `river_buffer_distance`, `max_depth`, the weight scalings, and running from the frozen HydroMT-Delft3DFM OSM data through `starting_graph`.

---

## Step 2. Data preparation: [export_swmm_piave.py](export_swmm_piave.py)

The script runs in the SWMManywhere environment and reads only SWMManywhere's output files. It holds every choice specific to SWMManywhere, and writes model-ready data to `hydromt_inputs_piave/`. The HydroMT side then needs no custom code.

It uses only packages that SWMManywhere already depends on: geopandas, numpy, pandas, pyarrow, rasterio, scipy and shapely. If your environment lacks any of them, install them with `pip install <package>`.

| Output | Content |
|---|---|
| `pipes.geojson` | 600 pipes with `branchid`, `branchtype = pipe`, `shape = circle`, `diameter`, `invlev_up` and `invlev_dn`, in three groups (below) |
| `rivers.geojson` | 83 river reaches (3.75 km) with `shape = rectangle`, `width`, `t_width`, `height`, `bedlev` and `closed = no` |
| `manholes.geojson` | 601 manholes with `bedlevel` = chamber floor and `streetlevel` = surface elevation |
| `region_1d.geojson` | Pipe network extent plus 150 m, the region for `setup_rivers` and `setup_pipes` |
| `region_2d.geojson` | DEM extent minus 60 m, the region for `setup_mesh2d`. With triangulation, the DEM must cover every 2D mesh node. |
| `data_catalog.yml` | Sources `swm_pipes`, `swm_rivers`, `swm_manholes` and `swm_dem` (the NASADEM file from step 1, renamed to `elevtn`) |
| `export_stats.json` | Counts and connector lengths |

The 600 pipes are:

- **SWMManywhere pipes (560):** invert levels are the chamber floors of the upstream and downstream nodes, because SWMManywhere writes zero offsets. Geometry is oriented from `u` to `v`.
- **Outlet pipes (30), one at each dummy outfall:** 10 m long, with a 0.5% slope. A 1D boundary needs an end node with a single pipe, but the lowest node of a tree can be a junction. SWMManywhere adds a similar outfall link in SWMM.
- **Connector pipes (10), one at each real outfall:** a straight pipe to the nearest point on the river. The river is split there, so the connector ends on a river node. The connector's downstream invert is DEM − 1 m. 2 of the 10 connectors run uphill.

River processing:

- Take the OSM waterways from `river.json` and drop the reversed copies that OSMnx adds.
- Clip them to the DEM extent minus 30 m, split them at the connector junctions, then split them into reaches of at most 50 m.
- Set the bed level to the DEM at the reach midpoint − 1 m, in a 4 m × 2.5 m rectangle. These are placeholders.

---

## Step 3. Build and run the D-Flow FM model

### Installation

Install HydroMT-Delft3DFM following its [installation guide](https://github.com/Deltares/hydromt_delft3dfm/blob/main/docs/getting_started/installation.rst), for example in a new conda environment:

```
conda create -n hydromt-delft3dfm python=3.11 -c conda-forge
conda activate hydromt-delft3dfm
pip install hydromt-delft3dfm
```

Tested with a development install of hydromt_delft3dfm 0.4.0 with hydromt 1.4.1, hydrolib-core 1.6.1, meshkernel 8.4.0 and xugrid 0.15.3, on Python 3.14.

Running the model also needs a Delft3D FM / DIMR installation. It was tested with D-Flow FM 1.2.184 (`dimr_latest`) on Windows.

### Build configuration: [dflowfm_build_piave_swm.yml](dflowfm_build_piave_swm.yml)

The configuration uses only existing HydroMT-Delft3DFM steps, with paths relative to the repository folder:

| Step | Settings |
|---|---|
| global | `crs: 32633`, `network_snap_offset: 0.5`, `snap_newbranches_to_branches_at_snapnodes: true`, `openwater_computation_node_distance: 40` |
| `setup_rivers` | `swm_rivers` in `region_1d`, Manning 0.023 |
| `setup_pipes` | `swm_pipes` in `region_1d`, circular sections, default White-Colebrook 0.003 |
| `setup_manholes` | `swm_manholes`, `bedlevel_shift: 0`, `snap_offset: 0.01` |
| `setup_1dboundary` (two steps) | Water level 0 m at the downstream river ends and at the pipe ends. The terrain is at 690–1140 m, so this is free outflow. |
| `setup_mesh2d` | `region_2d`, 25 m |
| `setup_maps_from_rasterdataset` | `swm_dem`, `fill_method: nearest`, default triangulation. `nearestNb`, as used in the HydroMT-Delft3DFM example configurations, leaves 2D bed levels empty with D-Flow FM 1.2.184. |
| `setup_constant_meteo` | Rainfall 300 mm/day on 2D |
| `setup_link1d2d` | `1d_to_2d`, after `setup_1dboundary` |
| `setup_config` | `time.tstop: 21600` (6 h), `geometry.allowbndatbifurcation: 1` |

### Build with temporary fixes: [build_dflowfm_piave_withfixes.py](build_dflowfm_piave_withfixes.py)

The script applies two fixes as patches, then runs the equivalent of

```
hydromt build dflowfm dflowfm_piave -i dflowfm_build_piave_swm.yml -d hydromt_inputs_piave/data_catalog.yml --fo -v
```

from the repository folder. An existing `dflowfm_piave/` is overwritten.

1. **Ring filter: [#365](https://github.com/Deltares/hydromt_delft3dfm/issues/365), fixed in PR [#366](https://github.com/Deltares/hydromt_delft3dfm/pull/366).**
   - **Problem:** `workflows/branches.py::_remove_branches_with_ring_geometries` compares start and end points with the default tolerance of `np.isclose`, which is about 51 m in y at UTM coordinates. Without the fix it removes 30 of the 600 pipes, including 2 outlet pipes. That leaves 16 loose pipe ends, which `setup_1dboundary` turns into extra boundaries.
   - **Patch:** the same tolerance as PR #366 (`atol=0, rtol=1e-10`).
2. **1D–2D links at boundary nodes: [#367](https://github.com/Deltares/hydromt_delft3dfm/issues/367).**
   - **Problem:** `setup_link1d2d` links every mesh1d node, contrary to its docstring ("except boundary locations"). D-Flow FM applies two separate rules to a 1D boundary:

     | Rule | Fixed by | Test (32 boundaries) |
     |---|---|---|
     | The boundary node has no 1D–2D link | Not creating that link (this patch) | With `allowBndAtBifurcation = 1` but without the patch: the 24 linked nodes are rejected |
     | The node next to the boundary is not a junction or linked node | `allowBndAtBifurcation = 1` in the yml | With the patch but the setting at 0: 28 are rejected |

     D-Flow FM's warning "AllowBndAtBifurcation=1 might solve this" appears in both cases, so both measures are needed.
   - **Patch:** after `setup_link1d2d`, links at nodes that have a 1D boundary condition are removed. This relies on `setup_1dboundary` running first. Links stay at other network ends, such as upstream pipe ends, so those manholes can still overflow to 2D.

Once both issues are fixed in a HydroMT-Delft3DFM release, use the `hydromt build` command above instead of the script.

### Run: [run_dflowfm_piave.py](run_dflowfm_piave.py)

Set `DIMR_LATEST` in the script to your DIMR installation, the folder that contains `x64\bin\run_dimr.bat`. The script runs `dflowfm_piave\dimr_config.xml`, writes the DIMR output to `dflowfm_piave\scherm.log`, and D-Flow FM writes its results to `dflowfm_piave\dflowfm\DFM_OUTPUT_DFlowFM\`. The 6 h simulation takes about a minute.

### Result

Both models ran for 6 h with D-Flow FM 1.2.184. "Without the fixes" is the plain `hydromt build` command above.

| | Without the fixes | With the temporary fixes |
|---|---:|---:|
| Pipe branches / river reaches | 570 / 83 | 600 / 83 |
| Manholes | 615 | 630 |
| 1D boundaries / rejected by D-Flow FM | 46 / 39 | 32 / 0 |
| Dummy outfalls with a working outlet | 5 of 30 | 30 of 30 |
| 1D–2D links | 685 | 675 |
| 2D cells / minimum bed level | 3,848 / 692.2 m | 3,848 / 692.2 m |
| Run time / errors / volume error | 60 s / 0 / 0 | 60 s / 0 / 0 |
| Rain / out through boundaries / stored | 181,463 / 78,385 / 103,079 m³ | 181,501 / 78,724 / 102,777 m³ |
| 1D links carrying > 1 l/s | 168 of 659 | 170 of 689 |

Total outflow is almost the same in both models because most of it leaves through the two river boundaries. Without the fixes, though, 25 of the 30 dummy-outfall networks have no outlet.

Known limitations of the model:

- Rain falls on the 2D grid only, so the pipes are loaded only where surface water reaches a manhole. SWMManywhere's subcatchments could be added as 1D laterals per manhole, but `setup_1dlateral_from_polygons` only supports one constant value for all polygons.
- About half of the water left in 2D at the end collects in cells along the closed 2D domain edge.
- River dimensions and bed levels are placeholders.

## Data sources and licences

The committed data in `swmm_piave/` and `hydromt_inputs_piave/` derive from these sources:

| Data | Source | Licence |
|---|---|---|
| Streets and waterways (`street.json`, `river.json`, and the pipes and rivers derived from them) | © OpenStreetMap contributors | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) |
| Buildings (`building.geoparquet`) | [Overture Maps Foundation](https://overturemaps.org), buildings theme | ODbL 1.0 for the parts derived from OpenStreetMap; see [Overture attribution](https://docs.overturemaps.org/attribution/) |
| Elevation (`elevation.tif`) | NASADEM (NASA JPL), via the Microsoft Planetary Computer | Public domain |
| Sewer network (`model_1/`) | Generated with SWMManywhere 0.2.4 | SWMManywhere code is [BSD-3-Clause](https://github.com/ImperialCollegeLondon/SWMManywhere/blob/main/LICENSE); none of its code is included here |

## References

- Dobson, B., Jovanovic, T., Alonso-Álvarez, D., & Chegini, T. (2025). SWMManywhere: A workflow for generation and sensitivity analysis of synthetic urban drainage models, anywhere. *Environmental Modelling & Software*. https://doi.org/10.1016/j.envsoft.2025.106358
- Dobson, B., Alonso-Álvarez, D., & Chegini, T. (2025). SWMManywhere: Synthesise Urban Drainage Network Models Anywhere in the World. *Journal of Open Source Software*, 10(110), 7729. https://doi.org/10.21105/joss.07729
- Chahinian, N., et al. (2019). Automatic mapping of urban wastewater networks based on manhole cover locations. *Computers, Environment and Urban Systems*, 78, 101370. https://doi.org/10.1016/j.compenvurbsys.2019.101370
