import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

ROOT = Path.cwd()
OUT = ROOT / "paper_figures"
OUT.mkdir(exist_ok=True)

def stats_str(df):
    mx = df["x"].mean()
    my = df["y"].mean()
    sx = df["x"].std(ddof=1)
    sy = df["y"].std(ddof=1)
    r = np.corrcoef(df["x"], df["y"])[0, 1]
    return f"Mean(x)={mx:.2f}, Mean(y)={my:.2f}\nStd(x)={sx:.2f}, Std(y)={sy:.2f}\nCorr(x,y)={r:.2f}"

# 1. Fig 1 Overview
print("Generating Fig 1...")
fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), constrained_layout=True)
dino = pd.read_csv(ROOT / "course_source" / "seed_datasets" / "Datasaurus_data.csv", header=None, names=["x", "y"])
axes[0].scatter(dino.x, dino.y, color="#1f77b4", s=25, alpha=0.85, edgecolors="none")
axes[0].set_title("(a) 原始恐龙 (Datasaurus, N=142)", weight="bold")
axes[0].text(0.05, 0.05, stats_str(dino), transform=axes[0].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#1f77b4", alpha=0.9), fontsize=9)

circle_final = pd.read_csv(ROOT / "run_default_dino_to_circle" / "results" / "circle-data-00099.csv")
axes[1].scatter(circle_final.x, circle_final.y, color="#ff7f0e", s=25, alpha=0.85, edgecolors="none")
axes[1].set_title("(b) 默认目标：圆形 (Circle, N=142)", weight="bold")
axes[1].text(0.05, 0.05, stats_str(circle_final), transform=axes[1].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#ff7f0e", alpha=0.9), fontsize=9)

flower_142 = pd.read_csv(ROOT / "custom_flower_142" / "data-00020.csv")
axes[2].scatter(flower_142.x, flower_142.y, color="#2ca02c", s=25, alpha=0.85, edgecolors="none")
axes[2].set_title("(c) 自定义目标：五瓣花 (Flower, N=142)", weight="bold")
axes[2].text(0.05, 0.05, stats_str(flower_142), transform=axes[2].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#2ca02c", alpha=0.9), fontsize=9)

flower_284 = pd.read_csv(ROOT / "custom_flower_284" / "data-00020.csv")
axes[3].scatter(flower_284.x, flower_284.y, color="#00796b", s=18, alpha=0.85, edgecolors="none")
axes[3].set_title("(d) 高密度目标：五瓣花 (Flower, N=284)", weight="bold")
axes[3].text(0.05, 0.05, stats_str(flower_284), transform=axes[3].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#00796b", alpha=0.9), fontsize=9)

for ax in axes:
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)

fig.savefig(OUT / "fig1_overview_concept.png", dpi=300)
plt.close(fig)

# 2. Fig 4 Performance Evaluation
print("Generating Fig 4 (Performance)...")
m_circle = pd.read_csv(ROOT / "analysis" / "default_run_metrics.csv")
m_f142 = pd.read_csv(ROOT / "custom_flower_142" / "metrics.csv")
m_f284 = pd.read_csv(ROOT / "custom_flower_284" / "metrics.csv")

fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)

# Subplot (a): Convergence curve
ax0 = axes[0]
ax0.plot(m_circle.approx_iteration, m_circle.mean_absolute_radial_error, "o-", ms=3.5, lw=1.8, color="#ff7f0e", label="默认圆形 (N=142)")
ax0.plot(m_f142.iteration, np.sqrt(m_f142.mean_nearest_target_error), "s-", ms=3.5, lw=1.8, color="#2ca02c", label="自定义花形 (N=142)")
ax0.plot(m_f284.iteration, np.sqrt(m_f284.mean_nearest_target_error), "^-", ms=3.5, lw=1.8, color="#00796b", label="高密度花形 (N=284)")
ax0.set_xlabel("扰动迭代次数 (Iterations)")
ax0.set_ylabel("形状目标平均距离误差 (单位)")
ax0.set_title("(a) 扰动次数与形状误差收敛动态", weight="bold")
ax0.grid(True, linestyle="--", alpha=0.4)
ax0.legend(frameon=True, loc="upper right")

# Subplot (b): Fitness improvement & diminishing returns
ax1 = axes[1]
for m, col, label, marker, err_col in [
    (m_circle, "#ff7f0e", "默认圆形 (N=142)", "o", "mean_absolute_radial_error"),
    (m_f142, "#2ca02c", "自定义花形 (N=142)", "s", "mean_nearest_target_error"),
    (m_f284, "#00796b", "高密度花形 (N=284)", "^", "mean_nearest_target_error")
]:
    vals = np.sqrt(m[err_col]) if "squared" in err_col or "nearest" in err_col else m[err_col]
    it_col = "approx_iteration" if "approx_iteration" in m.columns else "iteration"
    v0 = vals.iloc[0]
    improvement = (1 - vals / v0) * 100
    ax1.plot(m[it_col], improvement, f"{marker}-", ms=3.5, lw=1.8, color=col, label=label)

ax1.axhline(80, color="gray", linestyle=":", alpha=0.7, label="80% 吻合线")
ax1.set_xlabel("扰动迭代次数 (Iterations)")
ax1.set_ylabel("形状吻合度提升率 (%)")
ax1.set_title("(b) 形状吻合提升幅度与边际递减效应", weight="bold")
ax1.grid(True, linestyle="--", alpha=0.4)
ax1.legend(frameon=True, loc="lower right")

# Subplot (c): Strict statistical invariance verification
ax2 = axes[2]
ax2.plot(m_circle.approx_iteration, m_circle.max_abs_statistic_difference, "-", lw=1.2, color="#ff7f0e", label="默认圆形 (N=142)")
ax2.plot(m_f142.iteration, m_f142.max_abs_statistic_difference, "s-", ms=3, lw=1.5, color="#2ca02c", label="自定义花形 (N=142)")
ax2.plot(m_f284.iteration, m_f284.max_abs_statistic_difference, "^-", ms=3, lw=1.5, color="#00796b", label="高密度花形 (N=284)")
ax2.axhline(0.01, color="red", linestyle="--", lw=1.5, label="2位小数硬阈值 (0.010)")
ax2.set_xlabel("扰动迭代次数 (Iterations)")
ax2.set_ylabel("相对初始五项统计量最大绝对偏差")
ax2.set_title("(c) 统计量不变性严格保持验证", weight="bold")
ax2.set_ylim(-0.0005, 0.012)
ax2.grid(True, linestyle="--", alpha=0.4)
ax2.legend(frameon=True, loc="upper right", fontsize=8.5)

fig.savefig(OUT / "fig4_performance_evaluation.png", dpi=300)
fig.savefig(OUT / "fig5_performance_evaluation.png", dpi=300)
plt.close(fig)
print("Updated fig1 and performance evaluation figures successfully!")
