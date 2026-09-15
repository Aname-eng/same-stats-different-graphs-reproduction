import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

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

# Fig 1
print("Generating Fig 1...")
fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), constrained_layout=True)
dino = pd.read_csv(ROOT / "course_source" / "seed_datasets" / "Datasaurus_data.csv", header=None, names=["x", "y"])
axes[0].scatter(dino.x, dino.y, color="#1f77b4", s=25, alpha=0.85, edgecolors="none")
axes[0].set_title("(a) 原始恐龙 (Datasaurus)", weight="bold")
axes[0].text(0.05, 0.05, stats_str(dino), transform=axes[0].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#1f77b4", alpha=0.9), fontsize=9)

circle_final = pd.read_csv(ROOT / "run_default_dino_to_circle" / "results" / "circle-data-00099.csv")
axes[1].scatter(circle_final.x, circle_final.y, color="#ff7f0e", s=25, alpha=0.85, edgecolors="none")
axes[1].set_title("(b) 默认目标：圆形 (Circle)", weight="bold")
axes[1].text(0.05, 0.05, stats_str(circle_final), transform=axes[1].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#ff7f0e", alpha=0.9), fontsize=9)

flower_final = pd.read_csv(ROOT / "custom_flower_142" / "data-00020.csv")
axes[2].scatter(flower_final.x, flower_final.y, color="#2ca02c", s=25, alpha=0.85, edgecolors="none")
axes[2].set_title("(c) 任意图形：五瓣花 (Flower)", weight="bold")
axes[2].text(0.05, 0.05, stats_str(flower_final), transform=axes[2].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#2ca02c", alpha=0.9), fontsize=9)

logo_final = pd.read_csv(ROOT / "custom_chain_568_logo" / "data-00020.csv")
axes[3].scatter(logo_final.x, logo_final.y, color="#7b1fa2", s=12, alpha=0.85, edgecolors="none")
axes[3].set_title("(d) 复杂目标：南开校徽 (Logo)", weight="bold")
axes[3].text(0.05, 0.05, stats_str(logo_final), transform=axes[3].transAxes,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#7b1fa2", alpha=0.9), fontsize=9)

for ax in axes:
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)

fig.savefig(OUT / "fig1_overview_concept.png", dpi=300)
plt.close(fig)

# Fig 2
print("Generating Fig 2...")
frames_circle = [0, 10, 20, 40, 60, 99]
iters_circle = [0, 10000, 20000, 40000, 60000, 99000]
fig, axes = plt.subplots(2, 3, figsize=(12, 8.2), constrained_layout=True)
axes = axes.flatten()
theta = np.linspace(0, 2*np.pi, 200)
cx, cy, r = 54.26, 47.83, 30.0
circle_x = cx + r * np.cos(theta)
circle_y = cy + r * np.sin(theta)
metrics_circle = pd.read_csv(ROOT / "analysis" / "default_run_metrics.csv")

for idx, (frame, it) in enumerate(zip(frames_circle, iters_circle)):
    ax = axes[idx]
    df = pd.read_csv(ROOT / "run_default_dino_to_circle" / "results" / f"circle-data-{frame:05d}.csv")
    ax.plot(circle_x, circle_y, "r--", lw=1.5, alpha=0.6, label="目标圆周")
    ax.scatter(df.x, df.y, color="#2b2b2b", s=22, alpha=0.85, label="当前点集")
    row_m = metrics_circle[metrics_circle.frame == frame].iloc[0]
    err = row_m.mean_absolute_radial_error
    stat_diff = row_m.max_abs_statistic_difference
    ax.set_title(f"迭代次数: {it:,}\n径向误差: {err:.3f} | 统计量最大偏差: {stat_diff:.4f}", fontsize=9.5)
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)
    if idx == 0:
        ax.legend(loc="upper right", frameon=True, fontsize=8)

fig.savefig(OUT / "fig2_default_dino_to_circle.png", dpi=300)
plt.close(fig)

# Fig 3
print("Generating Fig 3...")
fig, axes = plt.subplots(2, 4, figsize=(14, 7.2), constrained_layout=True)
f_frames = [0, 5, 10, 20]
f_iters = [0, 25000, 50000, 100000]
target_f142 = pd.read_csv(ROOT / "custom_flower_142" / "normalized_target.csv")
target_f284 = pd.read_csv(ROOT / "custom_flower_284" / "normalized_target.csv")
m_f142 = pd.read_csv(ROOT / "custom_flower_142" / "metrics.csv")
m_f284 = pd.read_csv(ROOT / "custom_flower_284" / "metrics.csv")

for col, (f, it) in enumerate(zip(f_frames, f_iters)):
    ax0 = axes[0, col]
    df142 = pd.read_csv(ROOT / "custom_flower_142" / f"data-{f:05d}.csv")
    ax0.scatter(target_f142.x, target_f142.y, color="#d62728", s=14, alpha=0.25, label="目标花形")
    ax0.scatter(df142.x, df142.y, color="#1f77b4", s=20, alpha=0.85, label="点集 (N=142)")
    err142 = m_f142[m_f142.frame == f].iloc[0].mean_nearest_target_error
    ax0.set_title(f"N=142 | 迭代: {it:,}\n最近邻均方误差: {err142:.2f}", fontsize=9)

    ax1 = axes[1, col]
    df284 = pd.read_csv(ROOT / "custom_flower_284" / f"data-{f:05d}.csv")
    ax1.scatter(target_f284.x, target_f284.y, color="#d62728", s=12, alpha=0.25, label="目标花形")
    ax1.scatter(df284.x, df284.y, color="#2ca02c", s=14, alpha=0.85, label="点集 (N=284)")
    err284 = m_f284[m_f284.frame == f].iloc[0].mean_nearest_target_error
    ax1.set_title(f"N=284 | 迭代: {it:,}\n最近邻均方误差: {err284:.2f}", fontsize=9)

for ax in axes.flatten():
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)

axes[0, 0].legend(loc="upper right", frameon=True, fontsize=8)
axes[1, 0].legend(loc="upper right", frameon=True, fontsize=8)
fig.savefig(OUT / "fig3_flower_density_comparison.png", dpi=300)
plt.close(fig)

# Fig 4
print("Generating Fig 4...")
fig, axes = plt.subplots(2, 5, figsize=(18, 7.5), constrained_layout=True)
img_logo = Image.open(ROOT / "南开校徽.jpg")
axes[0, 0].imshow(img_logo)
axes[0, 0].set_title("原始栅格：南开校徽", weight="bold")
axes[0, 0].axis("off")

chain_frames = [0, 5, 10, 20]
chain_iters = [0, 25000, 50000, 100000]
target_logo = pd.read_csv(ROOT / "custom_chain_568_logo" / "normalized_target.csv")
m_chain_logo = pd.read_csv(ROOT / "custom_chain_568_logo" / "metrics.csv")

for col, (f, it) in enumerate(zip(chain_frames, chain_iters), start=1):
    ax = axes[0, col]
    df = pd.read_csv(ROOT / "custom_chain_568_logo" / f"data-{f:05d}.csv")
    ax.scatter(target_logo.x, target_logo.y, color="#d62728", s=10, alpha=0.2, label="校徽轮廓")
    ax.scatter(df.x, df.y, color="#512da8", s=12, alpha=0.85, label="当前点集")
    err = m_chain_logo[m_chain_logo.frame == f].iloc[0].mean_nearest_target_error
    ax.set_title(f"阶段一(恐龙→校徽) | 迭代: {it:,}\n形状误差: {err:.2f}", fontsize=9)
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)

img_motto = Image.open(ROOT / "校训.jpg")
axes[1, 0].imshow(img_motto)
axes[1, 0].set_title("原始栅格：校训文字", weight="bold")
axes[1, 0].axis("off")

target_motto = pd.read_csv(ROOT / "custom_chain_568_motto" / "normalized_target.csv")
m_chain_motto = pd.read_csv(ROOT / "custom_chain_568_motto" / "metrics.csv")

for col, (f, it) in enumerate(zip(chain_frames, chain_iters), start=1):
    ax = axes[1, col]
    df = pd.read_csv(ROOT / "custom_chain_568_motto" / f"data-{f:05d}.csv")
    ax.scatter(target_motto.x, target_motto.y, color="#d62728", s=10, alpha=0.2, label="校训轮廓")
    ax.scatter(df.x, df.y, color="#00796b", s=12, alpha=0.85, label="当前点集")
    err = m_chain_motto[m_chain_motto.frame == f].iloc[0].mean_nearest_target_error
    ax.set_title(f"阶段二(校徽→校训) | 迭代: {it:,}\n形状误差: {err:.2f}", fontsize=9)
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", alpha=0.3)

axes[0, 1].legend(loc="upper right", frameon=True, fontsize=8)
axes[1, 1].legend(loc="upper right", frameon=True, fontsize=8)
fig.savefig(OUT / "fig4_dense_chain_logo_to_motto.png", dpi=300)
plt.close(fig)

# Fig 5
print("Generating Fig 5...")
fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)

ax0 = axes[0]
ax0.plot(m_f142.iteration, m_f142.mean_nearest_target_error, "o-", ms=3.5, lw=1.8, color="#2ca02c", label="花形 (N=142)")
ax0.plot(m_f284.iteration, m_f284.mean_nearest_target_error, "s-", ms=3.5, lw=1.8, color="#1f77b4", label="花形 (N=284)")
ax0.plot(m_chain_logo.iteration, m_chain_logo.mean_nearest_target_error, "^-", ms=3.5, lw=1.8, color="#7b1fa2", label="南开校徽 (N=568)")
ax0.plot(m_chain_motto.iteration, m_chain_motto.mean_nearest_target_error, "d-", ms=3.5, lw=1.8, color="#00796b", label="南开校训 (N=568)")
ax0.set_xlabel("扰动迭代次数 (Iterations)")
ax0.set_ylabel("形状目标误差 (最近邻均方误差)")
ax0.set_title("(a) 扰动次数与形状误差收敛动态", weight="bold")
ax0.grid(True, linestyle="--", alpha=0.4)
ax0.legend(frameon=True, loc="upper right")

ax1 = axes[1]
for m, label, col, marker in [
    (m_f142, "花形 (N=142)", "#2ca02c", "o"),
    (m_f284, "花形 (N=284)", "#1f77b4", "s"),
    (m_chain_logo, "南开校徽 (N=568)", "#7b1fa2", "^"),
    (m_chain_motto, "南开校训 (N=568)", "#00796b", "d")
]:
    e0 = m.mean_nearest_target_error.iloc[0]
    red = (1 - m.mean_nearest_target_error / e0) * 100
    ax1.plot(m.iteration, red, f"{marker}-", ms=3.5, lw=1.8, color=col, label=label)

ax1.axhline(80, color="gray", linestyle=":", alpha=0.7)
ax1.set_xlabel("扰动迭代次数 (Iterations)")
ax1.set_ylabel("形状吻合度提升率 (%)")
ax1.set_title("(b) 形状吻合提升幅度与边际递减效应", weight="bold")
ax1.grid(True, linestyle="--", alpha=0.4)
ax1.legend(frameon=True, loc="lower right")

ax2 = axes[2]
ax2.plot(metrics_circle.approx_iteration, metrics_circle.max_abs_statistic_difference, "-", lw=1.2, color="#ff7f0e", label="圆形默认复现")
ax2.plot(m_f142.iteration, m_f142.max_abs_statistic_difference, "o-", ms=3, lw=1.5, color="#2ca02c", label="花形 (N=142)")
ax2.plot(m_chain_logo.iteration, m_chain_logo.max_abs_statistic_difference, "^-", ms=3, lw=1.5, color="#7b1fa2", label="南开校徽 (N=568)")
ax2.plot(m_chain_motto.iteration, m_chain_motto.max_abs_statistic_difference, "d-", ms=3, lw=1.5, color="#00796b", label="南开校训 (N=568)")
ax2.axhline(0.01, color="red", linestyle="--", lw=1.5, label="2位小数硬阈值 (0.010)")
ax2.set_xlabel("扰动迭代次数 (Iterations)")
ax2.set_ylabel("相对初始五项统计量最大绝对差")
ax2.set_title("(c) 统计量不变性约束严格保持验证", weight="bold")
ax2.set_ylim(-0.0005, 0.012)
ax2.grid(True, linestyle="--", alpha=0.4)
ax2.legend(frameon=True, loc="upper right", fontsize=8.5)

fig.savefig(OUT / "fig5_performance_evaluation.png", dpi=300)
plt.close(fig)
print("All 5 figures generated successfully in paper_figures/!")
