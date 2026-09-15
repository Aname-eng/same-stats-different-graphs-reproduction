from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image
import pandas as pd

# The README runs this script from the reproduction directory.  Using the
# working directory also avoids a Windows code-page round trip for Chinese
# characters in the absolute `__file__` path.
ROOT = Path.cwd()
OUT = ROOT / "analysis"
OUT.mkdir(exist_ok=True)
RUNS = {
    "Nankai emblem": ROOT / "custom_logo_anneal_boundary",
    "Motto": ROOT / "custom_motto_anneal_boundary",
}

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
colors = {"Nankai emblem": "#4c72b0", "Motto": "#dd8452"}
for name, run in RUNS.items():
    m = pd.read_csv(run / "metrics.csv")
    ax[0].plot(m.iteration, m.mean_nearest_target_error, marker="o", ms=3,
                label=name, color=colors[name])
    ax[1].plot(m.iteration, m.max_abs_statistic_difference, marker="o", ms=3,
                label=name, color=colors[name])
ax[0].set(title="Custom target distance", xlabel="Iterations", ylabel="Mean nearest-target squared error")
ax[1].set(title="Statistic preservation", xlabel="Iterations", ylabel="Maximum absolute difference")
for a in ax:
    a.grid(alpha=.3)
    a.legend()
fig.tight_layout()
fig.savefig(OUT / "custom_target_performance.png", dpi=180)
plt.close(fig)

fig, ax = plt.subplots(2, 2, figsize=(10, 9))
for col, (name, run) in enumerate(RUNS.items()):
    target = pd.read_csv(run / "normalized_target.csv")
    metrics = pd.read_csv(run / "metrics.csv")
    final_tag = int(metrics.iloc[-1].frame)
    final = pd.read_csv(run / f"data-{final_tag:05d}.csv")
    ax[0, col].scatter(target.x, target.y, s=24, color="#d62728", alpha=.85)
    ax[0, col].set(title=f"Target: {name}")
    ax[1, col].scatter(final.x, final.y, s=24, color="#202020", alpha=.85)
    ax[1, col].set(title=f"Annealed output: {name}")
    for a in (ax[0, col], ax[1, col]):
        a.set(xlim=(-5, 105), ylim=(-5, 105), aspect="equal", xlabel="x", ylabel="y")
fig.tight_layout()
fig.savefig(OUT / "custom_target_final_comparison.png", dpi=180)
plt.close(fig)

# A reader-facing figure that keeps the original raster beside the sampled
# target and the final point cloud.  The raster and point clouds are not put
# on a common metric scale; the panel is a provenance aid, not a pixel-level
# similarity score.
jpgs = list(ROOT.glob("*.jpg"))
if len(jpgs) < 2:
    raise FileNotFoundError("Expected the two course-folder JPG target images")
# The seal is almost square; the motto image is a wide, short strip.  Using
# aspect ratio avoids relying on the Windows console's filename encoding.
logo_path = max(jpgs, key=lambda p: Image.open(p).height / Image.open(p).width)
motto_path = min(jpgs, key=lambda p: Image.open(p).height / Image.open(p).width)
SOURCE_IMAGES = {"Nankai emblem": logo_path, "Motto": motto_path}
fig, ax = plt.subplots(2, 3, figsize=(12, 7.2), constrained_layout=True)
for row, (name, run) in enumerate(RUNS.items()):
    source_image = Image.open(SOURCE_IMAGES[name]).convert("RGB")
    ax[row, 0].imshow(source_image)
    ax[row, 0].set_title(f"Original raster: {name}")
    ax[row, 0].axis("off")
    target = pd.read_csv(run / "normalized_target.csv")
    metrics = pd.read_csv(run / "metrics.csv")
    final_tag = int(metrics.iloc[-1].frame)
    final = pd.read_csv(run / f"data-{final_tag:05d}.csv")
    ax[row, 1].scatter(target.x, target.y, s=18, color="#d62728", alpha=.85)
    ax[row, 1].set_title("Sampled target (normalized)")
    ax[row, 2].scatter(final.x, final.y, s=18, color="#202020", alpha=.85)
    ax[row, 2].set_title(f"Output after {int(metrics.iloc[-1].iteration):,} iterations")
    for col in (1, 2):
        ax[row, col].set(xlim=(-5, 105), ylim=(-5, 105), aspect="equal",
                         xlabel="x", ylabel="y")
fig.savefig(OUT / "custom_target_source_and_output.png", dpi=180)
plt.close(fig)

summary = []
for name, run in RUNS.items():
    m = pd.read_csv(run / "metrics.csv")
    summary.append({"target": name, "iterations": int(m.iloc[-1].iteration),
                    "initial_nearest_target_error": float(m.iloc[0].mean_nearest_target_error),
                    "final_nearest_target_error": float(m.iloc[-1].mean_nearest_target_error),
                    "relative_reduction": float(1 - m.iloc[-1].mean_nearest_target_error / m.iloc[0].mean_nearest_target_error),
                    "final_max_abs_statistic_difference": float(m.iloc[-1].max_abs_statistic_difference)})
pd.DataFrame(summary).to_csv(OUT / "custom_target_summary.csv", index=False)
print(pd.DataFrame(summary).to_string(index=False))
