"""Run the SWMM model of Piave built by build_swmm_piave.py.

Requires SWMManywhere, see build_swmm_piave.py. Uses SWMManywhere's ``run`` function
(pyswmm) with its default run settings: a 24 h simulation with SWMManywhere's bundled
design storm, storing node flooding and link flow. Writes the results to
swmm_piave/bbox_1/model_1/results.parquet, as SWMManywhere does with run_model=True.

Usage:
    python run_swmm_piave.py
"""

from pathlib import Path

from swmmanywhere.swmmanywhere import run

HERE = Path(__file__).parent
MODEL_DIR = HERE / "swmm_piave" / "bbox_1" / "model_1"

if __name__ == "__main__":
    inp = MODEL_DIR / "model_1.inp"
    if not inp.exists():
        raise FileNotFoundError(f"{inp} not found; run build_swmm_piave.py first.")
    results = run(inp, reporting_iters=100, duration=86400, storevars=["flooding", "flow"])
    results.to_parquet(MODEL_DIR / "results.parquet")
    print(f"{len(results)} results written to {MODEL_DIR / 'results.parquet'}")
