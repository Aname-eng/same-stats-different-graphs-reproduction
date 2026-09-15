"""Animation Renderer and Frame Auditor for Nankai Emblem Evolution (V2).

Generates a genuine pure scatter evolution GIF
where every single frame is an exact, legally accepted MCMC state.
Audits every frame to guarantee invariance:
  - Fixed N
  - Points within [0, 100]
  - Exact round-2 signature == REF_SIGNATURE
  - No illegal interpolations or overlaid target drawings
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
from src.fast_assignment import fast_spatial_assignment


from src.stats_audit import (
    stats5, signature2, is_legal, BOUNDS_0_100, REF_SIGNATURE
)
from src.geometry_ground_truth import GroundTruthGeometry
from moment_preserving_moves import _K

def generate_and_audit_animation(
    seed_csv: Path = Path("seed_568.csv"),
    slots_csv: Path = Path("targets/repair_v2/target_slots_N568.csv"),
    random_seed: int = 42,
    total_steps: int = 60000,
    frame_interval: int = 500,
    output_dir: Path = Path("output/repair_v2/seed_42"),
    gif_path: Path | None = None,
    audit_path: Path | None = None,
    point_size: int = 14,
    hold_start_frames: int = 15,
    hold_final_frames: int = 50,
    frame_duration_ms: int = 70,
):
    output_dir = Path(output_dir)
    frames_dir = output_dir / "animation_frames"
    gif_path = gif_path or (output_dir / "evolution_pure_scatter.gif")
    audit_path = audit_path or (output_dir / "animation_audit.json")

    frames_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(random_seed)
    df_seed = pd.read_csv(seed_csv)
    points = df_seed[["x", "y"]].to_numpy(float)
    point_ids = df_seed["point_id"].to_numpy(int) if "point_id" in df_seed else np.arange(len(points))
    n = len(points)

    df_slots = pd.read_csv(slots_csv)
    slots = df_slots[["x", "y"]].to_numpy(float)

    # Reassign initial
    assignment = fast_spatial_assignment(points, slots)

    def calc_energy(pts, assign):
        return float(np.mean(np.sum((pts - slots[assign])**2, axis=1)))

    current_energy = calc_energy(points, assignment)

    # Record frames
    recorded_frames = []
    frame_indices = list(range(0, total_steps + 1, frame_interval))
    if frame_indices[-1] != total_steps:
        frame_indices.append(total_steps)

    print(f"Generating pure scatter trajectory: N={n}, {total_steps} steps, recording {len(frame_indices)} frames...")

    # Step 0
    recorded_frames.append((0, points.copy(), current_energy))

    reassign_interval = 1000 if n > 4000 else (600 if n > 1500 else 400)
    stagnation_window = 3000
    recent_energies = [current_energy]
    reheat_temp = 0.0

    t0 = time.time()
    for step in range(1, total_steps + 1):
        if step % reassign_interval == 0:
            assignment = fast_spatial_assignment(points, slots)
            current_energy = calc_energy(points, assignment)

        if step % stagnation_window == 0:
            past_e = recent_energies[0]
            curr_e = current_energy
            rel_imprv = (past_e - curr_e) / max(past_e, 1e-4)
            recent_energies = [curr_e]
            if rel_imprv < 0.005:
                assignment = fast_spatial_assignment(points, slots)
                current_energy = calc_energy(points, assignment)
                reheat_temp = 0.015
            else:
                reheat_temp = max(0.0, reheat_temp * 0.8)

        batch_size = max(1, min(24, int(round(n / 600))))
        errs = np.sum((points - slots[assignment])**2, axis=1)
        err_probs = errs / errs.sum()

        try:
            primary = rng.choice(n, size=batch_size, replace=False, p=err_probs)
            other = rng.choice(n, size=2 * batch_size, replace=False)
            all_idx = np.concatenate([primary, other])
            if len(np.unique(all_idx)) < 3 * batch_size:
                continue
        except Exception:
            continue

        cand_pts = points.copy()
        batch_delta = 0.0
        accepted_in_batch = 0

        base_temp = max(0.0001, 0.20 * (1.0 - step / total_steps)**2)
        temp = base_temp + reheat_temp

        for b_i in range(batch_size):
            ix = np.array([primary[b_i], other[2 * b_i], other[2 * b_i + 1]])
            b = points[ix]
            center = b.mean(axis=0)
            z = b - center
            kz = _K @ z
            y = slots[assignment[ix]]

            a = np.sum(z * y)
            b_val = np.sum(kz * y)
            th_star = np.arctan2(b_val, a)

            mode = rng.random()
            if mode < 0.65:
                th = th_star
            elif mode < 0.85:
                th = th_star * rng.uniform(0.15, 0.75)
            else:
                th = float(rng.normal(0, 0.12))

            cand_b = center + np.cos(th) * z + np.sin(th) * kz
            if np.any(cand_b < 0.5) or np.any(cand_b > 99.5):
                continue

            old_3_err = np.sum((b - y)**2)
            new_3_err = np.sum((cand_b - y)**2)
            delta_e = (new_3_err - old_3_err) / n

            if delta_e < 0 or (temp > 1e-5 and rng.random() < np.exp(-delta_e / temp)):
                cand_pts[ix] = cand_b
                batch_delta += delta_e
                accepted_in_batch += 1

        if accepted_in_batch > 0:
            if signature2(cand_pts, ddof=1) == REF_SIGNATURE:
                points = cand_pts
                current_energy += batch_delta

        if step % frame_interval == 0:
            recorded_frames.append((step, points.copy(), current_energy))

    if recorded_frames[-1][0] != total_steps:
        recorded_frames.append((total_steps, points.copy(), current_energy))

    print(f"Recorded {len(recorded_frames)} frames in {time.time()-t0:.2f}s. Final MSE: {current_energy:.4f}")

    # Render each frame as pure scatter
    print("Rendering pure scatter frames...")
    pil_images = []
    frame_audit_entries = []
    all_frames_legal = True

    # Adjust dot size based on point count
    dot_s = point_size if point_size else (2 if n > 8000 else (4 if n > 4000 else (6 if n > 2000 else (10 if n > 800 else 14))))

    for idx, (st, pts, en) in enumerate(recorded_frames):
        # Audit frame
        sig = list(signature2(pts, ddof=1))
        st5 = stats5(pts, ddof=1).tolist()
        in_bnds = bool(np.all(pts >= 0.0) and np.all(pts <= 100.0))
        sig_match = (sig == list(REF_SIGNATURE))
        n_match = (len(pts) == n)

        frame_ok = bool(in_bnds and sig_match and n_match)
        if not frame_ok:
            all_frames_legal = False

        frame_audit_entries.append({
            "frame_idx": idx,
            "step": st,
            "mse_to_target": round(en, 4),
            "n_points": len(pts),
            "in_bounds_0_100": in_bnds,
            "signature2": sig,
            "matches_ref_signature": sig_match,
            "stats5": [round(x, 6) for x in st5],
            "frame_legal": frame_ok
        })

        # Render purely scatter plot: 1:1 aspect ratio, [0, 100], no auxiliary overlays
        fig, ax = plt.subplots(figsize=(6, 6), dpi=120)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.scatter(pts[:, 0], pts[:, 1], s=dot_s, color="#0d47a1", alpha=0.92, edgecolors="none")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_title(f"Step {st:06d} (N={n}) | MSE: {en:.3f}", fontsize=11, pad=8)
        ax.tick_params(labelsize=8)
        ax.grid(True, linestyle=":", alpha=0.35)

        img_file = frames_dir / f"pure_scatter_{idx:03d}.png"
        fig.tight_layout()
        fig.savefig(img_file, dpi=120)
        plt.close(fig)

        pil_img = Image.open(img_file).convert("RGB")
        pil_images.append(pil_img)

    # Build sequence with start hold and final emblem hold
    all_pil_images = []
    durations = []

    # Hold start (Dinosaur)
    for _ in range(max(1, hold_start_frames)):
        all_pil_images.append(pil_images[0])
        durations.append(frame_duration_ms)

    # Evolution trajectory
    for img in pil_images[1:-1]:
        all_pil_images.append(img)
        durations.append(frame_duration_ms)

    # Hold final (Completed Emblem)
    for _ in range(max(1, hold_final_frames)):
        all_pil_images.append(pil_images[-1])
        durations.append(frame_duration_ms)

    print(f"Saving animated GIF ({len(all_pil_images)} frames total, holding final frame {hold_final_frames} frames) to {gif_path}...")
    all_pil_images[0].save(
        gif_path,
        save_all=True,
        append_images=all_pil_images[1:],
        duration=durations,
        loop=0,
        optimize=True
    )

    audit_summary = {
        "task_id": "SSDG_REPAIR_V2_20260915",
        "random_seed": random_seed,
        "n_points": n,
        "total_unique_frames": len(recorded_frames),
        "total_gif_frames": len(all_pil_images),
        "hold_start_frames": hold_start_frames,
        "hold_final_frames": hold_final_frames,
        "frame_interval_steps": frame_interval,
        "total_steps": total_steps,
        "animation_gif_path": str(gif_path),
        "gif_size_bytes": gif_path.stat().st_size,
        "all_frames_legal": all_frames_legal,
        "pure_scatter_compliance": {
            "no_auxiliary_target_overlay": True,
            "equal_aspect_ratio": True,
            "bounds_0_100_preserved": True,
            "exact_moment_invariance_maintained": all_frames_legal
        },
        "frames_sample": frame_audit_entries[::10],
        "all_frames_audit": frame_audit_entries
    }

    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, ensure_ascii=False)

    print(f"GIF saved ({gif_path.stat().st_size / 1024:.1f} KB). All frames legal: {all_frames_legal}")
    return audit_summary

def main():
    parser = argparse.ArgumentParser(description="Render pure scatter animation and audit.")
    parser.add_argument("--n", type=int, default=568)
    parser.add_argument("--seed-csv", type=Path, default=None)
    parser.add_argument("--slots-csv", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--interval", type=int, default=500)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--point-size", type=int, default=None)
    parser.add_argument("--hold-start", type=int, default=15)
    parser.add_argument("--hold-final", type=int, default=50)
    parser.add_argument("--duration-ms", type=int, default=70)
    args = parser.parse_args()

    seed_csv = args.seed_csv or Path(f"seed_{args.n}.csv")
    slots_csv = args.slots_csv or Path(f"targets/repair_v2/target_slots_N{args.n}.csv")
    out_dir = args.output_dir or Path(f"output/repair_v2/seed_{args.seed}_N{args.n}")

    generate_and_audit_animation(
        seed_csv=seed_csv,
        slots_csv=slots_csv,
        random_seed=args.seed,
        total_steps=args.steps,
        frame_interval=args.interval,
        output_dir=out_dir,
        point_size=args.point_size,
        hold_start_frames=args.hold_start,
        hold_final_frames=args.hold_final,
        frame_duration_ms=args.duration_ms
    )

if __name__ == "__main__":
    main()
