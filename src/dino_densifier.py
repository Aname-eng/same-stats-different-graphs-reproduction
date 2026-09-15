"""Dense Dinosaur Seed Generator preserving anatomy and exact moments."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
from src.stats_audit import (
    MU_0, COV_0, REF_SIGNATURE, check_points, stats5, signature2, is_legal, BOUNDS_0_100
)

def densify_dino(n_target: int, seed: int = 20260915) -> tuple[np.ndarray, dict]:
    dino_path = Path("course_source/seed_datasets/Datasaurus_data.csv")
    df_raw = pd.read_csv(dino_path, header=None, names=["x", "y"])
    p0 = df_raw[["x", "y"]].to_numpy(float)
    n0 = len(p0)
    if n_target < n0:
        raise ValueError(f"n_target must be at least original point count {n0}")

    rng = np.random.default_rng(seed)
    tree = cKDTree(p0)
    # Find nearest neighbors along the local manifold
    dists, indices = tree.query(p0, k=4)

    # 1. Stratified manifold densification
    k_full = n_target // n0
    rem = n_target % n0

    raw_points = [p0.copy()]
    for k in range(1, k_full):
        # Choose a neighbor along the manifold
        neighbor_choices = np.array([indices[i, rng.choice([1, 2])] for i in range(n0)])
        tangents = p0[neighbor_choices] - p0
        lengths = np.linalg.norm(tangents, axis=1, keepdims=True) + 1e-8
        unit_tangents = tangents / lengths
        unit_normals = np.column_stack((-unit_tangents[:, 1], unit_tangents[:, 0]))

        # Position along the segment
        alphas = rng.uniform(0.15, 0.85, size=(n0, 1))
        # Small orthogonal jitter
        normal_noise = rng.normal(0, 0.08, size=(n0, 1)) * unit_normals
        layer = p0 + alphas * tangents + normal_noise
        raw_points.append(layer)

    if rem > 0:
        # Stratify remainder across the dataset to maintain covariance balance
        rem_idx = rng.choice(n0, size=rem, replace=False)
        rem_neighbors = np.array([indices[i, rng.choice([1, 2])] for i in rem_idx])
        tangents = p0[rem_neighbors] - p0[rem_idx]
        lengths = np.linalg.norm(tangents, axis=1, keepdims=True) + 1e-8
        unit_tangents = tangents / lengths
        unit_normals = np.column_stack((-unit_tangents[:, 1], unit_tangents[:, 0]))
        alphas = rng.uniform(0.15, 0.85, size=(rem, 1))
        normal_noise = rng.normal(0, 0.08, size=(rem, 1)) * unit_normals
        layer = p0[rem_idx] + alphas * tangents + normal_noise
        raw_points.append(layer)

    p_raw = np.vstack(raw_points)
    assert len(p_raw) == n_target

    # 2. Exact moment calibration to MU_0 and COV_0 (ddof=1)
    mu_raw = p_raw.mean(axis=0)
    z_raw = p_raw - mu_raw
    cov_raw = np.cov(p_raw.T, ddof=1)

    L_raw = np.linalg.cholesky(cov_raw)
    L_0 = np.linalg.cholesky(COV_0)

    # Affine transformation: p_cal = mu_0 + z_raw * (L_raw^-1)^T * L_0^T
    p_cal = MU_0 + z_raw @ np.linalg.inv(L_raw).T @ L_0.T

    # 3. Check legality
    if not is_legal(p_cal, n_target, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100):
        # Fallback if a point is right on the edge: contract raw points by tiny factor towards mean
        contract_factor = 0.995
        z_adj = z_raw * contract_factor
        cov_adj = np.cov((mu_raw + z_adj).T, ddof=1)
        L_adj = np.linalg.cholesky(cov_adj)
        p_cal = MU_0 + z_adj @ np.linalg.inv(L_adj).T @ L_0.T
        if not is_legal(p_cal, n_target, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100):
            raise RuntimeError("Densified dinosaur failed legal verification gate")

    s5 = stats5(p_cal, ddof=1)
    sig = signature2(p_cal, ddof=1)
    drift = np.linalg.norm(p_cal - p_raw, axis=1)

    # Nearest neighbor distance analysis
    cal_tree = cKDTree(p_cal)
    cal_dists, _ = cal_tree.query(p_cal, k=2)
    min_nn = float(np.min(cal_dists[:, 1]))
    mean_nn = float(np.mean(cal_dists[:, 1]))

    diag = {
        "n_target": n_target,
        "seed": seed,
        "stats5_unrounded": s5.tolist(),
        "signature2": list(sig),
        "calibration_shift_mean": float(drift.mean()),
        "calibration_shift_max": float(drift.max()),
        "nearest_neighbor_min": min_nn,
        "nearest_neighbor_mean": mean_nn,
        "coord_bounds": {
            "x_min": float(p_cal[:, 0].min()),
            "x_max": float(p_cal[:, 0].max()),
            "y_min": float(p_cal[:, 1].min()),
            "y_max": float(p_cal[:, 1].max())
        },
        "is_legal": True
    }
    return p_cal, diag

def main():
    parser = argparse.ArgumentParser(description="Generate dense dinosaur seed.")
    parser.add_argument("--n", type=int, default=568, help="Target point count")
    parser.add_argument("--seed", type=int, default=20260915, help="Random seed")
    parser.add_argument("--output", type=Path, default=Path("seed_568.csv"), help="Output CSV path")
    args = parser.parse_args()

    pts, diag = densify_dino(args.n, seed=args.seed)
    df = pd.DataFrame(pts, columns=["x", "y"])
    df.insert(0, "point_id", np.arange(len(pts)))
    df.to_csv(args.output, index=False)
    
    diag_path = args.output.with_name(f"seed_{args.n}_diagnostics.json")
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, ensure_ascii=False)

    # Plot pure scatter frame 0
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(pts[:, 0], pts[:, 1], s=12, color="#1f77b4", alpha=0.85, edgecolors="none")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title(f"Dense Dinosaur Frame 0 (N={args.n})\nSig: {diag['signature2']}", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    
    plot_path = Path("analysis") / f"seed_dino_frame0_N{args.n}.png"
    plot_path.parent.mkdir(exist_ok=True)
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)
    print(f"Generated dense seed N={args.n} saved to {args.output} and {plot_path}")
    print(f"  Diagnostics: {diag}")

if __name__ == "__main__":
    main()
