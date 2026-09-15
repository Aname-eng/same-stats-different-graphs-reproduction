"""6-Layer Moment-Compatible Target Emblem Generator (including NANKAI UNIVERSITY 1919)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
from scipy.optimize import minimize
from scipy.linalg import sqrtm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.stats_audit import MU_0, COV_0, stats5, signature2
from src.geometry_ground_truth import GroundTruthGeometry

GEOMETRY_6_LAYERS = [
    "outer_ring",
    "inner_ring",
    "octagram",
    "stroke_nan",
    "stroke_kai",
    "text_en_1919"
]

def extract_text_skeleton(image_path: Path = Path("南开校徽.jpg")) -> np.ndarray:
    """Extract clean skeleton points of 'NANKAI UNIVERSITY 1919' from emblem image."""
    img = Image.open(image_path).convert("L")
    arr = np.asarray(img)
    mask = (arr < 140)
    h, w = mask.shape
    y_grid, x_grid = np.indices((h, w))
    cy, cx = 395.0, 400.5
    scale = 41.9 / 358.0
    dist = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)

    # Annulus containing NANKAI UNIVERSITY and 1919 (excluding circle lines)
    m_text = mask & (dist > 260) & (dist < 335)

    dt = ndimage.distance_transform_edt(m_text)
    sk = (
        (dt > 1.2) & (dt >= np.roll(dt, 1, axis=1)) & (dt >= np.roll(dt, -1, axis=1)) |
        (dt > 1.2) & (dt >= np.roll(dt, 1, axis=0)) & (dt >= np.roll(dt, -1, axis=0))
    )
    ys, xs = np.where(sk)
    dx = (xs - cx) * scale
    dy = -(ys - cy) * scale
    pts = np.column_stack((dx + MU_0[0], dy + MU_0[1]))
    return pts

def compute_6layer_quotas(n_target: int) -> dict[str, int]:
    """Allocate quotas across 6 layers ensuring integer sum == n_target."""
    q_txt = max(200, int(round(0.245 * n_target)))  # English & 1919 text
    q_nan = max(20, int(round(0.088 * n_target)))   # 'nan' stroke
    q_kai = max(20, int(round(0.088 * n_target)))   # 'kai' stroke
    q_oct = max(50, int(round(0.190 * n_target)))   # octagram
    q_in = max(30, int(round(0.105 * n_target)))    # inner ring
    q_out = n_target - (q_txt + q_nan + q_kai + q_oct + q_in) # outer ring
    return {
        "outer_ring": q_out,
        "inner_ring": q_in,
        "octagram": q_oct,
        "stroke_nan": q_nan,
        "stroke_kai": q_kai,
        "text_en_1919": q_txt
    }

def generate_6layer_target(
    n_target: int = 2840,
    seed: int = 20260915,
    max_opt_iter: int = 3500
) -> tuple[np.ndarray, np.ndarray, dict]:
    gt = GroundTruthGeometry()
    quotas = compute_6layer_quotas(n_target)
    assert sum(quotas.values()) == n_target

    # 1. Chinese strokes
    pts_nan_all = gt.curves["stroke_nan"]
    pts_kai_all = gt.curves["stroke_kai"]
    idx_nan = np.linspace(0, len(pts_nan_all) - 1, quotas["stroke_nan"], dtype=int)
    idx_kai = np.linspace(0, len(pts_kai_all) - 1, quotas["stroke_kai"], dtype=int)
    q_nan = pts_nan_all[idx_nan]
    q_kai = pts_kai_all[idx_kai]

    # 2. Octagram
    pts_oct_all = gt.curves["octagram"]
    idx_oct = np.linspace(0, len(pts_oct_all) - 1, quotas["octagram"], dtype=int)
    q_oct = pts_oct_all[idx_oct]

    # 3. Inner ring
    r_in = gt.r_in
    thetas_in = np.linspace(0, 2 * np.pi, quotas["inner_ring"], endpoint=False)
    q_in = np.column_stack((MU_0[0] + r_in * np.cos(thetas_in), MU_0[1] + r_in * np.sin(thetas_in)))

    # 4. English text & 1919
    pts_txt_all = extract_text_skeleton()
    idx_txt = np.linspace(0, len(pts_txt_all) - 1, quotas["text_en_1919"], dtype=int)
    q_txt = pts_txt_all[idx_txt]

    # 5. Outer ring polar density optimization
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
        return np.column_stack((MU_0[0] + r_out * np.cos(thetas), MU_0[1] + r_out * np.sin(thetas)))

    def loss(params: np.ndarray) -> float:
        q_o = sample_outer(params)
        Q_cand = np.vstack([q_o, q_in, q_oct, q_nan, q_kai, q_txt])
        mu_Q = Q_cand.mean(axis=0)
        cov_Q = np.cov(Q_cand.T, ddof=1)
        e_mu = np.sum((mu_Q - MU_0)**2)
        e_cov = np.sum((cov_Q - COV_0)**2)
        return float(1000.0 * e_mu + e_cov)

    init_params = np.zeros(6)
    init_params[0] = -0.5
    res = minimize(loss, init_params, method="Nelder-Mead", options={"maxiter": max_opt_iter})
    q_out = sample_outer(res.x)

    # Assemble target points Q and layer IDs
    Q = np.vstack([q_out, q_in, q_oct, q_nan, q_kai, q_txt])
    layer_ids = np.concatenate([
        np.full(quotas["outer_ring"], 0, dtype=int),
        np.full(quotas["inner_ring"], 1, dtype=int),
        np.full(quotas["octagram"], 2, dtype=int),
        np.full(quotas["stroke_nan"], 3, dtype=int),
        np.full(quotas["stroke_kai"], 4, dtype=int),
        np.full(quotas["text_en_1919"], 5, dtype=int)
    ])

    mu_Q = Q.mean(axis=0)
    cov_Q = np.cov(Q.T, ddof=1)
    C_P = ((n_target - 1) / n_target) * COV_0
    C_Q = ((n_target - 1) / n_target) * cov_Q

    LB_mean = float(np.sum((mu_Q - MU_0)**2))
    diff_cov = C_P + C_Q - 2 * sqrtm(sqrtm(C_P) @ C_Q @ sqrtm(C_P))
    LB_cov = float(np.real(np.trace(diff_cov)))
    LB_total = float(LB_mean + LB_cov)

    s5 = stats5(Q, ddof=1)
    sig = signature2(Q, ddof=1)

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
    }
    return Q, layer_ids, diag

def main():
    parser = argparse.ArgumentParser(description="Generate 6-layer target slots (with English and 1919).")
    parser.add_argument("--n", type=int, default=2840)
    parser.add_argument("--output-dir", type=Path, default=Path("targets/repair_v2"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    Q, l_ids, diag = generate_6layer_target(args.n)

    csv_path = args.output_dir / f"target_slots_6layer_N{args.n}.csv"
    df = pd.DataFrame({
        "slot_id": np.arange(len(Q)),
        "x": Q[:, 0],
        "y": Q[:, 1],
        "layer_id": l_ids,
        "layer_name": [GEOMETRY_6_LAYERS[i] for i in l_ids]
    })
    df.to_csv(csv_path, index=False)

    diag_path = args.output_dir / f"target_slots_6layer_N{args.n}_diagnostics.json"
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, ensure_ascii=False)

    print(f"6-Layer Target Q generated for N={args.n}:")
    print(f"  LB_mean: {diag['LB_mean']}, LB_cov: {diag['LB_cov']}, LB_total: {diag['LB_total']}")
    print(f"  Signature: {diag['signature2']}")
    print(f"  Quotas: {diag['quotas']}")

    # Plot 6-layer target breakdown
    fig, ax = plt.subplots(figsize=(8, 8), dpi=200)
    colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b"]
    for lid, lname in enumerate(GEOMETRY_6_LAYERS):
        m = (l_ids == lid)
        ax.scatter(Q[m, 0], Q[m, 1], s=8, color=colors[lid], label=f"{lname} ({np.sum(m)})", alpha=0.9)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title(f"Full 6-Layer Target Slots Q (N={args.n})\nLB_total: {diag['LB_total']:.4f}", fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.35)
    
    fig_path = Path("analysis") / f"target_slots_6layer_N{args.n}.png"
    fig.savefig(fig_path, dpi=200)
    plt.close(fig)
    print(f"Saved 6-layer target diagnostic plot to {fig_path}")

if __name__ == "__main__":
    main()
