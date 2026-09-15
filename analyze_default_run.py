from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
RUN = ROOT / "run_default_dino_to_circle"
RESULTS = RUN / "results"
OUT = ROOT / "analysis"
OUT.mkdir(exist_ok=True)

base = pd.read_csv(RUN / "seed_datasets" / "Datasaurus_data.csv", header=None, names=["x", "y"])
base_stats = np.array([base.x.mean(), base.y.mean(), base.x.std(), base.y.std(), base.corr().iloc[0,1]])
rows = []
for path in sorted(RESULTS.glob("circle-data-*.csv")):
    frame = int(path.stem.rsplit("-", 1)[1])
    df = pd.read_csv(path, index_col=0)
    radius_error = np.abs(np.hypot(df.x - 54.26, df.y - 47.83) - 30).mean()
    stats = np.array([df.x.mean(), df.y.mean(), df.x.std(), df.y.std(), df.corr().iloc[0,1]])
    rows.append({"frame": frame, "approx_iteration": frame * 1000, "mean_absolute_radial_error": radius_error,
                 "max_abs_statistic_difference": np.abs(stats - base_stats).max()})
metrics = pd.DataFrame(rows).sort_values("frame")
metrics.to_csv(OUT / "default_run_metrics.csv", index=False)

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
ax[0].plot(metrics.approx_iteration, metrics.mean_absolute_radial_error, marker="o", ms=3)
ax[0].set(title="Circle fit improves with perturbations", xlabel="Perturbation iterations", ylabel="Mean absolute radial error")
ax[0].grid(alpha=.3)
ax[1].plot(metrics.approx_iteration, metrics.max_abs_statistic_difference, marker="o", ms=3, color="#c44e52")
ax[1].axhline(.01, ls="--", color="black", lw=1, label="2-decimal tolerance scale")
ax[1].set(title="Summary-statistic preservation", xlabel="Perturbation iterations", ylabel="Max absolute difference vs. dino")
ax[1].grid(alpha=.3); ax[1].legend()
fig.tight_layout(); fig.savefig(OUT / "performance_vs_iterations.png", dpi=180); plt.close(fig)

frames = [0, 20, 40, 60, 80, 99]
fig, axes = plt.subplots(2, 3, figsize=(12, 8))
for a, frame in zip(axes.ravel(), frames):
    df = pd.read_csv(RESULTS / f"circle-data-{frame:05d}.csv", index_col=0)
    a.scatter(df.x, df.y, s=12, alpha=.7, color="#202020")
    a.add_patch(plt.Circle((54.26, 47.83), 30, fill=False, color="#d62728", lw=1.2))
    a.set(xlim=(-5,105), ylim=(-5,105), aspect="equal", title=f"{frame*1000:,} iterations")
fig.suptitle("Datasaurus: dino to circle under simulated annealing", y=.98)
fig.tight_layout(); fig.savefig(OUT / "dino_to_circle_progress.png", dpi=180); plt.close(fig)

print(metrics.iloc[[0, -1]].to_string(index=False))
