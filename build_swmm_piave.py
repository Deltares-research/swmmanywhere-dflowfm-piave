"""Build a synthetic sewer network and SWMM model for Piave with SWMManywhere.

Install SWMManywhere following its documentation, for example ``pip install
swmmanywhere`` (https://imperialcollegelondon.github.io/SWMManywhere/quickstart/).
Tested with SWMManywhere 0.2.4 and Python 3.12.

Runs SWMManywhere's default workflow, without parameter overrides, for the bounding box
below. Writes the network and the SWMM input file to swmm_piave/bbox_1/model_1/.
Input data in swmm_piave/bbox_1/download/ are reused when present. Delete that folder
to download fresh data (OpenStreetMap streets and waterways, Overture buildings and
NASADEM elevation), which may differ because OpenStreetMap changes.

Next: run_swmm_piave.py runs the SWMM model, export_swmm_piave.py prepares the
D-Flow FM inputs.

Usage:
    python build_swmm_piave.py
"""

from pathlib import Path

from swmmanywhere.logging import set_verbose
from swmmanywhere.swmmanywhere import swmmanywhere

HERE = Path(__file__).parent

CONFIG = {
    "base_dir": HERE,
    "project": "swmm_piave",
    # West, south, east, north (EPSG:4326)
    "bbox": [12.448261, 46.472383, 12.472671, 46.484434],
    "bbox_number": 1,
    "model_number": 1,
    # The SWMM model is run separately with run_swmm_piave.py
    "run_model": False,
}

if __name__ == "__main__":
    # Verbose mode also saves the graph after every step; export_swmm_piave.py needs
    # identify_outfalls_edges.geojson to tell real from dummy outfalls.
    set_verbose(True)
    inp, _ = swmmanywhere(CONFIG)
    print(f"SWMM model written to {inp}")
