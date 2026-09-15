"""Plot high-resolution side-by-side comparison of N=2272 Dinosaur vs Nankai Emblem."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

def plot_dense_comparison():
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=200)

    # 1. Dense Dinosaur (Frame 0)
    df_dino = pd.read_csv("seed_2272.csv")
    ax0 = axes[0]
    ax0.scatter(df_dino["x"], df_dino["y"], s=8, color="#0d47a1", alpha=0.9, edgecolors="none")
    ax0.set_xlim(0, 100)
    ax0.set_ylim(0, 100)
    ax0.set_aspect("equal")
    ax0.set_title("Dense Dinosaur Initial Seed (N=2272)\nExact Signature: ['54.26', '47.83', '16.77', '26.94', '-0.06']", fontsize=11, fontweight="bold", pad=10)
    ax0.grid(True, linestyle=":", alpha=0.35)

    # 2. Target Slots Q (N=2272)
    df_slots = pd.read_csv("targets/repair_v2/target_slots_N2272.csv")
    ax1 = axes[1]
    ax1.scatter(df_slots["x"], df_slots["y"], s=8, color="#2e7d32", alpha=0.85, edgecolors="none")
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 100)
    ax1.set_aspect("equal")
    ax1.set_title("Moment-Compatible Target Slots Q (N=2272)\nMSE Lower Bound: 0.0033 | 100% 5-Layer Coverage", fontsize=11, fontweight="bold", pad=10)
    ax1.grid(True, linestyle=":", alpha=0.35)

    # 3. Final Optimized Emblem (Frame 60000)
    df_final = pd.read_csv("output/repair_v2/seed_42_N2272/snapshots/frame_060000.csv")
    ax2 = axes[2]
    ax2.scatter(df_final["x"], df_final["y"], s=8, color="#c2185b", alpha=0.9, edgecolors="none")
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.set_aspect("equal")
    ax2.set_title("Final Optimized Nankai Emblem (N=2272, Step 60k)\nMSE: 0.199 | Invariants: PASS | Geom: PASS", fontsize=11, fontweight="bold", pad=10)
    ax2.grid(True, linestyle=":", alpha=0.35)

    plt.tight_layout()
    out_path = Path("analysis/dense_evolution_N2272_comparison.png")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"Dense comparison plot saved to {out_path}")

if __name__ == "__main__":
    plot_dense_comparison()
