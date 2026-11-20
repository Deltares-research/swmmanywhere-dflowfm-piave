"""Build the D-Flow FM model of Piave with HydroMT-Delft3DFM, with temporary fixes.

Install HydroMT-Delft3DFM following its installation guide
(https://github.com/Deltares/hydromt_delft3dfm/blob/main/docs/getting_started/installation.rst).
Tested with a development install of hydromt_delft3dfm 0.4.0 and hydromt 1.4.1.

Builds dflowfm_piave/ from dflowfm_build_piave_swm.yml and
hydromt_inputs_piave/data_catalog.yml (written by export_swmm_piave.py). This is the
same as

    hydromt build dflowfm dflowfm_piave -i dflowfm_build_piave_swm.yml -d hydromt_inputs_piave/data_catalog.yml --fo -v

but with temporary fixes for two hydromt_delft3dfm bugs, applied as patches:

1. Deltares/hydromt_delft3dfm#365 (fix in PR #366):
   workflows/branches.py::_remove_branches_with_ring_geometries compares start and
   end points with np.isclose's default tolerance (about 51 m in y at UTM
   coordinates), so it removes ordinary short branches. Patched as in PR #366.
2. Deltares/hydromt_delft3dfm#367: setup_link1d2d links every mesh1d node, including
   nodes with a 1D boundary, and D-Flow FM rejects boundaries on linked nodes.
   Patched: links at 1D boundary nodes are removed after setup_link1d2d (requires
   setup_1dboundary before setup_link1d2d). allowBndAtBifurcation = 1 in the yml is
   still needed for the other D-Flow FM rule (no junction or link next to a boundary).

Once both issues are fixed, use the hydromt command above instead of this script.
An existing dflowfm_piave/ is overwritten.

Usage:
    python build_dflowfm_piave_withfixes.py
"""

import functools
import os
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from hydromt.cli.main import main

import hydromt_delft3dfm.workflows.branches as wb
from hydromt_delft3dfm import DFlowFMModel

HERE = Path(__file__).parent
MODEL_ROOT = "dflowfm_piave"
BUILD_CONFIG = "dflowfm_build_piave_swm.yml"
DATA_CATALOG = "hydromt_inputs_piave/data_catalog.yml"
BOUNDARY_SNAP = 0.5  # m


def _remove_branches_with_ring_geometries(branches):
    """Same as hydromt_delft3dfm, with the tolerance from PR #366."""
    first = np.array([line.coords[0][:2] for line in branches.geometry])
    last = np.array([line.coords[-1][:2] for line in branches.geometry])
    ring = np.all(np.isclose(first, last, atol=0, rtol=1e-10), axis=1)
    return branches.loc[~ring]


_setup_link1d2d = DFlowFMModel.setup_link1d2d


@functools.wraps(_setup_link1d2d)
def setup_link1d2d(self, *args, **kwargs):
    """Run setup_link1d2d, then remove links at 1D boundary nodes (#367)."""
    _setup_link1d2d(self, *args, **kwargs)
    bnd_xy = [
        np.c_[da["x"].values, da["y"].values]
        for name, da in self.forcing.data.items()
        if name.startswith("boundary1d") and "x" in da.coords
    ]
    if not bnd_xy or "link1d2d" not in self.mesh.data.data_vars:
        return
    bnd_xy = np.concatenate(bnd_xy)
    names = ["link1d2d", "link1d2d_id", "link1d2d_long_name", "link1d2d_contact_type"]
    links = xr.Dataset({n: getattr(self.mesh.data[n], "obj", self.mesh.data[n]) for n in names})
    grid1d = self.mesh.mesh_grids["mesh1d"]
    node_xy = np.c_[grid1d.node_x, grid1d.node_y][links["link1d2d"].values[:, 0]]
    dist = np.hypot(
        node_xy[:, None, 0] - bnd_xy[None, :, 0], node_xy[:, None, 1] - bnd_xy[None, :, 1]
    ).min(axis=1)
    dim = links["link1d2d"].dims[0]
    self.mesh.set_link1d2d(links.isel({dim: np.nonzero(dist > BOUNDARY_SNAP)[0]}))
    print(f"removed {int((dist <= BOUNDARY_SNAP).sum())} 1d2d links at 1D boundary nodes")


wb._remove_branches_with_ring_geometries = _remove_branches_with_ring_geometries
DFlowFMModel.setup_link1d2d = setup_link1d2d

if __name__ == "__main__":
    # The build configuration uses paths relative to this folder
    os.chdir(HERE)
    sys.argv = [
        sys.argv[0], "build", "dflowfm", MODEL_ROOT,
        "-i", BUILD_CONFIG, "-d", DATA_CATALOG, "--fo", "-v",
    ]  # fmt: skip
    main()
