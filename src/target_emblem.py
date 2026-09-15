"""Target Emblem Decomposition into 5 Verifiable Layers with Slot Allocation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
import matplotlib.pyplot as plt
from src.stats_audit import MU_0, COV_0, stats5, signature2

LAYER_NAMES = ["nan", "kai", "octagram", "mid_ring", "outer_ring"]

def extract_raw_layers(image_path: Path = Path("南开校徽.jpg")):
    if not image_path.exists():
        raise FileNotFoundError(f"Emblem image not found at {image_path}")
    img = Image.open(image_path).convert("L")
    arr = np.asarray(img)
    mask = (arr < 150)
    h, w = mask.shape
    cy, cx = 395.0, 400.5
    y_grid, x_grid = np.indices((h, w))
    dist_c = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)

    # 1:1 true aspect ratio scaling
    scale = 41.5 / 365.0

    # Layer masks
    masks = {
        "nan": mask & (dist_c < 145) & (x_grid < 400),
        "kai": mask & (dist_c < 145) & (x_grid >= 400),
        "octagram": mask & (dist_c >= 145) & (dist_c < 240),
        "mid_ring": mask & (dist_c >= 240) & (dist_c < 335),
        "outer_ring": mask & (dist_c >= 335) & (dist_c < 390)
    }

    def get_skeleton(m, thresh=1.2):
        dt = ndimage.distance_transform_edt(m)
        h_max = (dt > thresh) & (dt >= np.roll(dt, 1, axis=1)) & (dt >= np.roll(dt, -1, axis=1))
        v_max = (dt > thresh) & (dt >= np.roll(dt, 1, axis=0)) & (dt >= np.roll(dt, -1, axis=0))
        d1_max = (dt > thresh) & (dt >= np.roll(np.roll(dt, 1, axis=0), 1, axis=1)) & (dt >= np.roll(np.roll(dt, -1, axis=0), -1, axis=1))
        d2_max = (dt > thresh) & (dt >= np.roll(np.roll(dt, 1, axis=0), -1, axis=1)) & (dt >= np.roll(np.roll(dt, -1, axis=0), 1, axis=1))
        return (h_max | v_max | d1_max | d2_max)

    layer_points = {}
    for name in LAYER_NAMES:
        thresh = 1.5 if "ring" in name or name == "octagram" else 1.2
        skel = get_skeleton(masks[name], thresh=thresh)
        ys, xs = np.where(skel)
        dx = (xs - cx) * scale
        dy = -(ys - cy) * scale
        pts = np.column_stack((dx + MU_0[0], dy + MU_0[1]))
        layer_points[name] = pts

    return layer_points

def compute_default_quotas(n_target: int) -> dict[str, int]:
    """Allocate quotas across 5 layers ensuring text readability and boundary definition."""
    # Proportions: nan: ~10.5%, kai: ~10.5%, octagram: ~24.6%, mid_ring: ~12.0%, outer_ring: ~42.4%
    q_nan = int(round(0.105 * n_target))
    q_kai = int(round(0.105 * n_target))
    q_oct = int(round(0.246 * n_target))
    q_mid = int(round(0.120 * n_target))
    q_out = n_target - (q_nan + q_kai + q_oct + q_mid)
    return {
        "nan": q_nan,
        "kai": q_kai,
        "octagram": q_oct,
        "mid_ring": q_mid,
        "outer_ring": q_out
    }

def generate_target_slots(n_target: int, seed: int = 20260915, quotas: dict[str, int] | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Generate N target slots with 1-to-1 capacity."""
    if quotas is None:
        quotas = compute_default_quotas(n_target)
    assert sum(quotas.values()) == n_target, f"Quotas sum {sum(quotas.values())} != {n_target}"

    layer_points = extract_raw_layers()
    rng = np.random.default_rng(seed)

    slots_list = []
    layer_ids_list = []

    for l_id, name in enumerate(LAYER_NAMES):
        q = quotas[name]
        pts = layer_points[name]
        if q <= 0:
            continue
        if len(pts) < q:
            idx = rng.choice(len(pts), size=q, replace=True)
            chosen = pts[idx] + rng.normal(0, 0.05, size=(q, 2))
        else:
            if name in ["outer_ring", "mid_ring", "octagram"]:
                d = pts - MU_0
                theta = np.arctan2(d[:, 1], d[:, 0])
                w = 1.0 - 0.75 * np.cos(2 * theta) - 0.12 * np.sin(2 * theta)
                w = np.clip(w, 0.08, None)
                w /= w.sum()
                idx = rng.choice(len(pts), size=q, replace=False, p=w)
                chosen = pts[idx]
            else:
                idx = rng.choice(len(pts), size=q, replace=False)
                chosen = pts[idx]

        slots_list.append(chosen)
        layer_ids_list.append(np.full(q, l_id, dtype=int))

    slots = np.vstack(slots_list)
    slot_layer_ids = np.concatenate(layer_ids_list)

    s5 = stats5(slots, ddof=1)
    sig = signature2(slots, ddof=1)

    diag = {
        "n_target": n_target,
        "quotas": quotas,
        "slot_stats5": s5.tolist(),
        "slot_signature2": list(sig),
        "target_reference_signature": ["54.26", "47.83", "16.77", "26.94", "-0.06"],
        "coord_bounds": {
            "x_min": float(slots[:, 0].min()),
            "x_max": float(slots[:, 0].max()),
            "y_min": float(slots[:, 1].min()),
            "y_max": float(slots[:, 1].max())
        }
    }
    return slots, slot_layer_ids, diag

def main():
    parser = argparse.ArgumentParser(description="Extract Nankai emblem layers and slots.")
    parser.add_argument("--n", type=int, default=568, help="Target point count")
    parser.add_argument("--seed", type=int, default=20260915, help="Random seed")
    parser.add_argument("--output", type=Path, default=Path("targets/target_slots_568.csv"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    slots, layer_ids, diag = generate_target_slots(args.n, seed=args.seed)

    df = pd.DataFrame({
        "slot_id": np.arange(len(slots)),
        "x": slots[:, 0],
        "y": slots[:, 1],
        "layer_id": layer_ids,
        "layer_name": [LAYER_NAMES[i] for i in layer_ids]
    })
    df.to_csv(args.output, index=False)

    diag_path = args.output.with_name(f"target_slots_{args.n}_diagnostics.json")
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, ensure_ascii=False)

    # Visualization
    fig, ax = plt.subplots(figsize=(7, 7))
    colors = ["#d62728", "#9467bd", "#ff7f0e", "#2ca02c", "#1f77b4"]
    for l_id, name in enumerate(LAYER_NAMES):
        m = (layer_ids == l_id)
        ax.scatter(slots[m, 0], slots[m, 1], s=16, color=colors[l_id], label=f"{name} ({np.sum(m)})", alpha=0.85)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title(f"Nankai Emblem 5-Layer Target Slots (N={args.n})\nTrue 1:1 Aspect Ratio", fontsize=11)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3)

    plot_path = Path("analysis") / f"target_slots_N{args.n}.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)

    print(f"Generated {len(slots)} target slots saved to {args.output} and {plot_path}")
    print(f"  Diagnostics: {diag}")

if __name__ == "__main__":
    main()
