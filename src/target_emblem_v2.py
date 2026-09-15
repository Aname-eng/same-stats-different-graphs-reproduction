"""Moment-Compatible Target Emblem Generator (V2)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.linalg import sqrtm

from src.stats_audit import MU_0, COV_0, stats5, signature2
from src.geometry_ground_truth import GroundTruthGeometry, GEOMETRY_LAYERS

def compute_v2_quotas(n_target: int) -> dict[str, int]:
    """Allocate quotas across 5 verifiable layers ensuring integer sum == n_target."""
    q_nan = max(10, int(round(0.105 * n_target)))
    q_kai = max(10, int(round(0.105 * n_target)))
    q_oct = max(20, int(round(0.246 * n_target)))
    q_in = max(10, int(round(0.120 * n_target)))
    q_out = n_target - (q_nan + q_kai + q_oct + q_in)
    return {
        "stroke_nan": q_nan,
        "stroke_kai": q_kai,
        "octagram": q_oct,
        "inner_ring": q_in,
        "outer_ring": q_out
    }

def generate_moment_compatible_target(
    n_target: int,
    gt: GroundTruthGeometry | None = None,
    seed: int = 20260915,
    max_opt_iter: int = 3000
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Generate N equal-weight target points on true geometry with minimal moment lower bound."""
    if gt is None:
        gt = GroundTruthGeometry()

    quotas = compute_v2_quotas(n_target)
    assert sum(quotas.values()) == n_target

    rng = np.random.default_rng(seed)

    # 1. Sample character strokes (nan and kai) deterministically along medial lines
    pts_nan_all = gt.curves["stroke_nan"]
    pts_kai_all = gt.curves["stroke_kai"]

    idx_nan = np.linspace(0, len(pts_nan_all) - 1, quotas["stroke_nan"], dtype=int)
    idx_kai = np.linspace(0, len(pts_kai_all) - 1, quotas["stroke_kai"], dtype=int)
    q_nan = pts_nan_all[idx_nan]
    q_kai = pts_kai_all[idx_kai]

    # 2. Sample octagram deterministically along the 16 edges
    pts_oct_all = gt.curves["octagram"]
    idx_oct = np.linspace(0, len(pts_oct_all) - 1, quotas["octagram"], dtype=int)
    q_oct = pts_oct_all[idx_oct]

    # 3. Inner ring: perfectly uniform around circle for 100% gap-free coverage
    r_in = gt.r_in
    thetas_in = np.linspace(0, 2 * np.pi, quotas["inner_ring"], endpoint=False)
    q_in = np.column_stack((gt.mu_0[0] + r_in * np.cos(thetas_in), gt.mu_0[1] + r_in * np.sin(thetas_in)))

    # 4. Outer ring: parameterize by continuous smooth polar density to match sample moments
    n_out = quotas["outer_ring"]
    r_out = gt.r_out

    def sample_outer(params: np.ndarray) -> np.ndarray:
        theta_grid = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
        log_p = (
            params[0] * np.cos(2 * theta_grid) + params[1] * np.sin(2 * theta_grid) +
            params[2] * np.cos(4 * theta_grid) + params[3] * np.sin(4 * theta_grid) +
            params[4] * np.cos(theta_grid) + params[5] * np.sin(theta_grid)
        )
        p = np.exp(log_p - np.max(log_p))
        cdf = np.cumsum(p)
        cdf /= cdf[-1]
        u = (np.arange(n_out) + 0.5) / n_out
        thetas = np.interp(u, cdf, theta_grid)
        x = gt.mu_0[0] + r_out * np.cos(thetas)
        y = gt.mu_0[1] + r_out * np.sin(thetas)
        return np.column_stack((x, y))

    def loss(params: np.ndarray) -> float:
        q_o = sample_outer(params)
        Q_cand = np.vstack([q_o, q_in, q_oct, q_nan, q_kai])
        mu_Q = Q_cand.mean(axis=0)
        cov_Q = np.cov(Q_cand.T, ddof=1)
        e_mu = np.sum((mu_Q - gt.mu_0)**2)
        e_cov = np.sum((cov_Q - COV_0)**2)
        return float(1000.0 * e_mu + e_cov)

    init_params = np.zeros(6)
    init_params[0] = -0.5
    res = minimize(loss, init_params, method="Nelder-Mead", options={"maxiter": max_opt_iter})
    q_out = sample_outer(res.x)

    # Assemble target points Q and layer IDs
    Q = np.vstack([q_out, q_in, q_oct, q_nan, q_kai])
    layer_ids = np.concatenate([
        np.full(n_out, 0, dtype=int),  # outer_ring
        np.full(quotas["inner_ring"], 1, dtype=int),   # inner_ring
        np.full(quotas["octagram"], 2, dtype=int), # octagram
        np.full(quotas["stroke_nan"], 3, dtype=int), # stroke_nan
        np.full(quotas["stroke_kai"], 4, dtype=int)  # stroke_kai
    ])

    # Compute theoretical lower bounds
    mu_Q = Q.mean(axis=0)
    cov_Q = np.cov(Q.T, ddof=1)
    C_P = ((n_target - 1) / n_target) * COV_0
    C_Q = ((n_target - 1) / n_target) * cov_Q

    LB_mean = float(np.sum((mu_Q - gt.mu_0)**2))
    diff_cov = C_P + C_Q - 2 * sqrtm(sqrtm(C_P) @ C_Q @ sqrtm(C_P))
    LB_cov = float(np.real(np.trace(diff_cov)))
    LB_total = float(LB_mean + LB_cov)

    s5 = stats5(Q, ddof=1)
    sig = signature2(Q, ddof=1)

    # Geometry verification of the target itself
    geom_eval = gt.evaluate(Q)

    diag = {
        "n_target": n_target,
        "quotas": quotas,
        "mu_Q": mu_Q.tolist(),
        "cov_Q": cov_Q.tolist(),
        "stats5": s5.tolist(),
        "signature2": list(sig),
        "reference_signature": ["54.26", "47.83", "16.77", "26.94", "-0.06"],
        "LB_mean": round(LB_mean, 6),
        "LB_cov": round(LB_cov, 6),
        "LB_total": round(LB_total, 6),
        "geometry_check": geom_eval
    }

    return Q, layer_ids, diag

def main():
    parser = argparse.ArgumentParser(description="Generate V2 moment-compatible target.")
    parser.add_argument("--n", type=int, default=568)
    parser.add_argument("--output-dir", type=Path, default=Path("targets/repair_v2"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gt = GroundTruthGeometry()
    Q, l_ids, diag = generate_moment_compatible_target(args.n, gt=gt)

    csv_path = args.output_dir / f"target_slots_N{args.n}.csv"
    df = pd.DataFrame({
        "slot_id": np.arange(len(Q)),
        "x": Q[:, 0],
        "y": Q[:, 1],
        "layer_id": l_ids,
        "layer_name": [GEOMETRY_LAYERS[i] for i in l_ids]
    })
    df.to_csv(csv_path, index=False)

    diag_path = args.output_dir / f"target_slots_N{args.n}_diagnostics.json"
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, ensure_ascii=False)

    print(f"Target Q generated for N={args.n}:")
    print(f"  LB_mean: {diag['LB_mean']}, LB_cov: {diag['LB_cov']}, LB_total: {diag['LB_total']}")
    print(f"  Signature: {diag['signature2']}")
    print(f"  Geometry pass: {diag['geometry_check']['final_geometry_pass']}")
    print(f"  Saved to {csv_path} and {diag_path}")

if __name__ == "__main__":
    main()
