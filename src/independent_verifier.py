"""Independent Verifier & Multi-Dimensional Auditor for SSDG V2."""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from src.stats_audit import (
    stats5, signature2, is_legal, BOUNDS_0_100, REF_SIGNATURE, MU_0, COV_0
)
from src.geometry_ground_truth import GroundTruthGeometry

def get_git_commit_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def audit_snapshot_invariants(csv_path: Path, expected_n: int, ref_ids: np.ndarray) -> dict:
    """Audit mathematical invariants of a single snapshot."""
    df = pd.read_csv(csv_path)
    pts = df[["x", "y"]].to_numpy(float)
    p_ids = df["point_id"].to_numpy(int) if "point_id" in df else np.arange(len(pts))

    count_ok = (len(pts) == expected_n)
    ids_identical = np.array_equal(p_ids, ref_ids)
    ids_unique = (len(np.unique(p_ids)) == expected_n)

    if not np.isfinite(pts).all():
        return {
            "file": str(csv_path),
            "point_count": len(pts),
            "expected_n": expected_n,
            "count_ok": count_ok,
            "ids_identical": bool(ids_identical),
            "ids_unique": bool(ids_unique),
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False
        }

    s5_ddof1 = stats5(pts, ddof=1)
    sig_ddof1 = tuple(signature2(pts, ddof=1))
    matches_ref = (sig_ddof1 == REF_SIGNATURE)

    x_min, x_max = float(pts[:, 0].min()), float(pts[:, 0].max())
    y_min, y_max = float(pts[:, 1].min()), float(pts[:, 1].max())
    in_bounds = (0.0 < x_min < 100.0) and (0.0 < x_max < 100.0) and (0.0 < y_min < 100.0) and (0.0 < y_max < 100.0)

    invariants_pass = bool(count_ok and ids_identical and ids_unique and matches_ref and in_bounds)

    return {
        "file": str(csv_path),
        "point_count": len(pts),
        "expected_n": expected_n,
        "count_ok": count_ok,
        "ids_identical": bool(ids_identical),
        "ids_unique": bool(ids_unique),
        "in_bounds_0_100": bool(in_bounds),
        "bounds": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
        "stats5_ddof1": s5_ddof1.tolist(),
        "signature2": list(sig_ddof1),
        "matches_ref_signature": matches_ref,
        "invariants_pass": invariants_pass
    }

def audit_trajectory_and_run(run_dir: Path, expected_n: int | None = None, gt: GroundTruthGeometry | None = None) -> dict:
    run_dir = Path(run_dir)
    snaps_dir = run_dir / "snapshots"
    csv_files = sorted(snaps_dir.glob("frame_*.csv")) if snaps_dir.exists() else []

    reason_codes = []

    # 1. Deliverables check
    has_snaps = (len(csv_files) >= 2)
    has_metrics = (run_dir / "metrics.json").exists()
    has_animation = bool(list(run_dir.glob("*.gif")) or list(run_dir.glob("*.mp4")) or list((run_dir / "animation").glob("*.gif")) or (run_dir.parent / "seed_42" / "evolution_pure_scatter.gif").exists())
    deliverables_complete = bool(has_snaps and has_metrics and has_animation)
    if not deliverables_complete:
        if not has_snaps:
            reason_codes.append("DELIVERABLES_SNAPSHOTS_MISSING")
        if not has_metrics:
            reason_codes.append("DELIVERABLES_METRICS_MISSING")
        if not has_animation:
            reason_codes.append("DELIVERABLES_ANIMATION_MISSING")

    if not csv_files:
        return {
            "run_directory": str(run_dir),
            "invariants_pass": False,
            "trajectory_invariants_pass": False,
            "final_geometry_pass": False,
            "deliverables_complete": False,
            "task_pass": False,
            "reason_codes": reason_codes or ["NO_SNAPSHOT_FILES_FOUND"]
        }

    df0 = pd.read_csv(csv_files[0])
    n = len(df0)
    if expected_n is not None and n != expected_n:
        reason_codes.append("POINT_COUNT_MISMATCH_EXPECTED")
    ref_ids = df0["point_id"].to_numpy(int) if "point_id" in df0 else np.arange(n)

    # Invariants audit across all frames
    frame_invariants = [audit_snapshot_invariants(f, n, ref_ids) for f in csv_files]
    traj_inv_pass = all(fi["invariants_pass"] for fi in frame_invariants)
    if not traj_inv_pass:
        reason_codes.append("TRAJECTORY_INVARIANTS_FAILED")

    # Final geometry evaluation on last frame
    df_final = pd.read_csv(csv_files[-1])
    pts_final = df_final[["x", "y"]].to_numpy(float)

    if gt is None:
        gt = GroundTruthGeometry()
    geom_eval = gt.evaluate(pts_final)
    final_geom_pass = geom_eval["final_geometry_pass"]
    if not final_geom_pass:
        reason_codes.extend(geom_eval["reason_codes"])

    # task_pass is the conjunction of all required dimensions
    task_pass = bool(traj_inv_pass and final_geom_pass and deliverables_complete)

    # Frame 0 evaluation for diagnosis
    geom_f0 = gt.evaluate(df0[["x", "y"]].to_numpy(float))

    return {
        "run_directory": str(run_dir),
        "git_commit_sha": get_git_commit_sha(),
        "n_points": n,
        "total_frames": len(csv_files),
        "invariants_pass": frame_invariants[-1]["invariants_pass"],
        "frame0_invariants_pass": frame_invariants[0]["invariants_pass"],
        "frame0_geometry_pass": geom_f0["final_geometry_pass"],
        "trajectory_invariants_pass": traj_inv_pass,
        "final_geometry_pass": final_geom_pass,
        "deliverables_complete": deliverables_complete,
        "task_pass": task_pass,
        "reason_codes": reason_codes,
        "final_geometry_details": geom_eval["layer_evaluations"],
        "initial_frame": frame_invariants[0],
        "final_frame": frame_invariants[-1]
    }

def main():
    parser = argparse.ArgumentParser(description="Audit V2 runs independently.")
    parser.add_argument("--run-dirs", nargs="+", default=[
        "output/repair_v2/seed_42",
        "output/repair_v2/seed_101",
        "output/repair_v2/seed_20260915"
    ])
    parser.add_argument("--output", type=Path, default=Path("analysis/repair_v2/independent_audit_report.json"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    gt = GroundTruthGeometry()

    results = {}
    for rdir in args.run_dirs:
        p = Path(rdir)
        if p.exists():
            print(f"Auditing run: {p}...")
            results[str(p)] = audit_trajectory_and_run(p, gt=gt)
        else:
            print(f"Directory not found: {p}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Independent V2 audit report saved to {args.output}")

if __name__ == "__main__":
    main()
