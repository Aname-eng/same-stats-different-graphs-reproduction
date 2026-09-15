"""Independent Verifier & Audit Pipeline for Nankai Emblem Evolution."""
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
from src.target_emblem import LAYER_NAMES

def get_git_commit_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def audit_snapshot_file(csv_path: Path, expected_n: int, ref_ids: np.ndarray, target_slots: np.ndarray, target_lids: np.ndarray) -> dict:
    df = pd.read_csv(csv_path)
    pts = df[["x", "y"]].to_numpy(float)
    p_ids = df["point_id"].to_numpy(int)

    # 1. Point count and ID constancy
    count_ok = (len(pts) == expected_n)
    ids_identical = np.array_equal(p_ids, ref_ids)
    ids_unique = (len(np.unique(p_ids)) == expected_n)

    # 2. Stats and Signatures from raw coordinates
    s5_ddof1 = stats5(pts, ddof=1)
    s5_ddof0 = stats5(pts, ddof=0)
    sig_ddof1 = list(signature2(pts, ddof=1))
    sig_ddof0 = list(signature2(pts, ddof=0))
    matches_ref = (tuple(sig_ddof1) == REF_SIGNATURE)

    # Max absolute drift from reference values
    ref_vals = np.array([54.26, 47.83, 16.77, 26.94, -0.06])
    drift_from_ref = np.abs(s5_ddof1 - ref_vals)

    # 3. Coordinate bounds
    x_min, x_max = float(pts[:, 0].min()), float(pts[:, 0].max())
    y_min, y_max = float(pts[:, 1].min()), float(pts[:, 1].max())
    in_bounds = (0.0 < x_min < 100.0) and (0.0 < x_max < 100.0) and (0.0 < y_min < 100.0) and (0.0 < y_max < 100.0)

    # 4. Point-to-Target and Target-to-Point distances
    tree_slots = cKDTree(target_slots)
    tree_pts = cKDTree(pts)

    d_pt_to_slot, _ = tree_slots.query(pts)
    d_slot_to_pt, _ = tree_pts.query(target_slots)

    # 5. Layer-by-layer coverage audit
    layer_coverage = {}
    for l_id, l_name in enumerate(LAYER_NAMES):
        m_slot = (target_lids == l_id)
        if np.any(m_slot):
            d_layer = d_slot_to_pt[m_slot]
            layer_coverage[l_name] = {
                "target_slot_count": int(np.sum(m_slot)),
                "mean_dist_to_point": float(np.mean(d_layer)),
                "median_dist_to_point": float(np.median(d_layer)),
                "p90_dist_to_point": float(np.percentile(d_layer, 90)),
                "max_dist_to_point": float(np.max(d_layer))
            }

    is_fully_accepted = (
        count_ok and ids_identical and ids_unique and matches_ref and in_bounds
    )

    return {
        "file": str(csv_path),
        "point_count": len(pts),
        "expected_n": expected_n,
        "count_ok": count_ok,
        "ids_identical_to_frame0": bool(ids_identical),
        "ids_strictly_unique": bool(ids_unique),
        "in_bounds_0_100": bool(in_bounds),
        "bounds": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
        "stats5_ddof1": s5_ddof1.tolist(),
        "stats5_ddof0": s5_ddof0.tolist(),
        "signature2_ddof1": sig_ddof1,
        "signature2_ddof0": sig_ddof0,
        "ref_signature": list(REF_SIGNATURE),
        "matches_ref_signature": bool(matches_ref),
        "max_stat_drift": float(np.max(drift_from_ref)),
        "point_to_slot_dist": {
            "mean": float(np.mean(d_pt_to_slot)),
            "max": float(np.max(d_pt_to_slot)),
            "p90": float(np.percentile(d_pt_to_slot, 90))
        },
        "slot_to_point_dist": {
            "mean": float(np.mean(d_slot_to_pt)),
            "max": float(np.max(d_slot_to_pt)),
            "p90": float(np.percentile(d_slot_to_pt, 90))
        },
        "layer_coverage": layer_coverage,
        "is_fully_accepted": bool(is_fully_accepted)
    }

def audit_run_directory(run_dir: Path, slots_csv: Path) -> dict:
    run_dir = Path(run_dir)
    snaps_dir = run_dir / "snapshots"
    csv_files = sorted(snaps_dir.glob("frame_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No snapshot CSVs found in {snaps_dir}")

    df_slots = pd.read_csv(slots_csv)
    target_slots = df_slots[["x", "y"]].to_numpy(float)
    target_lids = df_slots["layer_id"].to_numpy(int)
    n = len(target_slots)

    # Reference point IDs from frame 0
    df0 = pd.read_csv(csv_files[0])
    ref_ids = df0["point_id"].to_numpy(int)

    frame_audits = []
    for f in csv_files:
        audit = audit_snapshot_file(f, n, ref_ids, target_slots, target_lids)
        frame_audits.append(audit)

    all_accepted = all(fa["is_fully_accepted"] for fa in frame_audits)

    # Read metrics log if present
    metrics_file = run_dir / "metrics.json"
    metrics_data = {}
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as mf:
            metrics_data = json.load(mf)

    return {
        "run_directory": str(run_dir),
        "git_commit_sha": get_git_commit_sha(),
        "total_frames_audited": len(frame_audits),
        "all_frames_accepted": all_accepted,
        "initial_frame": frame_audits[0],
        "final_frame": frame_audits[-1],
        "frames": frame_audits,
        "metrics_summary": metrics_data
    }

def main():
    parser = argparse.ArgumentParser(description="Audit evolution runs independently.")
    parser.add_argument("--run-dirs", nargs="+", default=[
        "output/evolution_seed_42",
        "output/evolution_seed_101",
        "output/evolution_seed_20260915"
    ])
    parser.add_argument("--slots-csv", type=Path, default=Path("targets/target_slots_568.csv"))
    parser.add_argument("--output", type=Path, default=Path("analysis/independent_verification_report.json"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    for rdir in args.run_dirs:
        p = Path(rdir)
        if p.exists():
            print(f"Auditing run directory: {p}...")
            results[str(p)] = audit_run_directory(p, args.slots_csv)
        else:
            print(f"Skipping non-existent dir: {p}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Independent audit report saved to {args.output}")

if __name__ == "__main__":
    main()
