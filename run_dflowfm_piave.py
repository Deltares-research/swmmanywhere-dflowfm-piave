"""Run the D-Flow FM model of Piave with DIMR.

Requires a Delft3D FM / DIMR installation. Set DIMR_LATEST below to the folder that
contains x64/bin/run_dimr.bat (for example the "dimr_latest" folder). Tested with
D-Flow FM 1.2.184 on Windows.

Runs dflowfm_piave/dimr_config.xml, built by build_dflowfm_piave_withfixes.py. DIMR
output goes to dflowfm_piave/scherm.log, results to
dflowfm_piave/dflowfm/DFM_OUTPUT_DFlowFM/.

Usage:
    python run_dflowfm_piave.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
MODEL = HERE / "dflowfm_piave"
DIMR_LATEST = Path(r"path\to\dimr_latest")  # placeholder: set to your DIMR installation


def run(dimr_latest: Path = DIMR_LATEST, model: Path = MODEL) -> int:
    run_dimr = dimr_latest / "x64" / "bin" / "run_dimr.bat"
    if not run_dimr.exists():
        sys.exit(f"{run_dimr} not found; set DIMR_LATEST in {Path(__file__).name}.")
    if not (model / "dimr_config.xml").exists():
        sys.exit(f"{model / 'dimr_config.xml'} not found; run build_dflowfm_piave_withfixes.py first.")
    with open(model / "scherm.log", "w") as log:
        result = subprocess.run(
            ["cmd", "/c", str(run_dimr), "dimr_config.xml"],
            cwd=model,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    print(f"DIMR finished with exit code {result.returncode}; see {model / 'scherm.log'}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(run())
