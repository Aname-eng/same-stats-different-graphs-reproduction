import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
from moment_preserving_moves import stats5, signature2

def legacy_floor_pass(pts, ref_stats):
    r1 = [math.floor(r * 100) for r in ref_stats]
    r2 = [math.floor(r * 100) for r in stats5(pts, ddof=1)]
    return max([abs(a - b) for a, b in zip(r1, r2)]) == 0

dino_df = pd.read_csv("course_source/seed_datasets/Datasaurus_data.csv", header=None, names=["x", "y"])
dino_pts = dino_df[["x", "y"]].to_numpy(float)
ref_s5 = stats5(dino_pts, ddof=1)
ref_sig = signature2(dino_pts, ddof=1)

snapshots = {
    "Datasaurus_original": ("course_source/seed_datasets/Datasaurus_data.csv", None),
    "Circle_final_99k": ("run_default_dino_to_circle/results/circle-data-00099.csv", 0),
    "Flower_142_final": ("custom_flower_142/data-00020.csv", 0),
    "Flower_284_final": ("custom_flower_284/data-00020.csv", 0)
}

results = {}
for name, (rel_path, hdr) in snapshots.items():
    p = Path(rel_path)
    if not p.exists():
        continue
    if hdr is None:
        df = pd.read_csv(p, header=None, names=["x", "y"])
    else:
        df = pd.read_csv(p, header=hdr)
    pts = df[["x", "y"]].to_numpy(float)
    s5 = stats5(pts, ddof=1)
    sig = signature2(pts, ddof=1)
    l_pass = legacy_floor_pass(pts, ref_s5)
    r_pass = (sig == ref_sig)
    results[name] = {
        "file": str(rel_path),
        "n_points": len(pts),
        "stats5_unrounded": s5.tolist(),
        "signature2": list(sig),
        "legacy_floor_pass": l_pass,
        "round2_pass": r_pass,
        "max_abs_diff_from_ref": float(np.max(np.abs(s5 - ref_s5)))
    }

out_path = Path("analysis/existing_snapshots_audit.json")
out_path.parent.mkdir(exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Audited {len(results)} snapshots. Results saved to {out_path}:")
for k, v in results.items():
    print(f"  {k}: N={v['n_points']}, legacy_floor={v['legacy_floor_pass']}, round2={v['round2_pass']}, max_diff={v['max_abs_diff_from_ref']:.5f}")
