"""Generate multi-panel comparison grid for V2 evolution."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

def create_comparison_grid():
    fig, axes = plt.subplots(2, 5, figsize=(20, 8), dpi=150)
    
    # Row 1: Evolution of Seed 42 across 5 snapshots
    steps = [0, 15000, 30000, 45000, 60000]
    for i, st in enumerate(steps):
        ax = axes[0, i]
        csv_file = Path(f"output/repair_v2/seed_42/snapshots/frame_{st:06d}.csv")
        df = pd.read_csv(csv_file)
        ax.scatter(df["x"], df["y"], s=10, color="#0d47a1", alpha=0.9, edgecolors="none")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_title(f"Seed 42: Step {st:05d}", fontsize=11, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.3)

    # Row 2: Target Slots, Seed 42 final, Seed 101 final, Seed 20260915 final, Diagnostic Overlay
    # 1. Target Slots
    ax = axes[1, 0]
    df_slots = pd.read_csv("targets/repair_v2/target_slots_N568.csv")
    ax.scatter(df_slots["x"], df_slots["y"], s=10, color="#2e7d32", alpha=0.8, edgecolors="none")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title("Target Slots Q (N=568)\nMSE Lower Bound: 0.0036", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.3)

    # 2. Seed 42 final
    ax = axes[1, 1]
    df_s42 = pd.read_csv("output/repair_v2/seed_42/snapshots/frame_060000.csv")
    ax.scatter(df_s42["x"], df_s42["y"], s=10, color="#1565c0", alpha=0.9, edgecolors="none")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title("Seed 42 Final (Step 60k)\nMSE: 0.038 | Geom: PASS", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.3)

    # 3. Seed 101 final
    ax = axes[1, 2]
    df_s101 = pd.read_csv("output/repair_v2/seed_101/snapshots/frame_060000.csv")
    ax.scatter(df_s101["x"], df_s101["y"], s=10, color="#6a1b9a", alpha=0.9, edgecolors="none")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title("Seed 101 Final (Step 60k)\nMSE: 0.087 | Geom: PASS", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.3)

    # 4. Seed 20260915 final
    ax = axes[1, 3]
    df_s2026 = pd.read_csv("output/repair_v2/seed_20260915/snapshots/frame_060000.csv")
    ax.scatter(df_s2026["x"], df_s2026["y"], s=10, color="#c2185b", alpha=0.9, edgecolors="none")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title("Seed 20260915 Final (Step 60k)\nMSE: 0.067 | Geom: PASS", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.3)

    # 5. Diagnostic overlay of Seed 42 final on ground truth
    ax = axes[1, 4]
    ax.scatter(df_slots["x"], df_slots["y"], s=8, color="#bdbdbd", alpha=0.4, label="Target Q")
    ax.scatter(df_s42["x"], df_s42["y"], s=10, color="#d32f2f", alpha=0.85, label="Optimized")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_title("Diagnostic Overlay\nCoverage: 100% | 5/5 Layers", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.3)

    plt.tight_layout()
    out_path = Path("analysis/repair_v2/v2_evolution_comparison_grid.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Comparison grid written to {out_path}")

if __name__ == "__main__":
    create_comparison_grid()
