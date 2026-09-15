"""Run the same-statistics annealing algorithm toward an arbitrary target CSV.

The course version hard-codes its target shapes.  This companion runner keeps
the course acceptance rule (the five summary statistics must match to the
requested decimal precision) but reads a target point cloud from a CSV.  The
target is affine-normalized to the source statistics before annealing, so the
geometric target remains recognizable while the constraint is feasible.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def stats(df: pd.DataFrame) -> np.ndarray:
    return np.array([df.x.mean(), df.y.mean(), df.x.std(), df.y.std(), df.corr().iloc[0, 1]])


def stats_array(arr: np.ndarray) -> np.ndarray:
    """The same five statistics, without constructing a DataFrame per proposal."""
    return np.array([arr[:, 0].mean(), arr[:, 1].mean(), arr[:, 0].std(ddof=1),
                     arr[:, 1].std(ddof=1), np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]])


def stats_allowed(candidate: np.ndarray, reference: np.ndarray, decimals: int) -> bool:
    lhs = np.floor(stats_array(reference) * 10 ** decimals)
    rhs = np.floor(stats_array(candidate) * 10 ** decimals)
    return bool(np.max(np.abs(lhs - rhs)) == 0)


def _sqrt_cov(cov: np.ndarray, inverse: bool = False) -> np.ndarray:
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 1e-8)
    diagonal = np.diag(1.0 / np.sqrt(vals) if inverse else np.sqrt(vals))
    return vecs @ diagonal @ vecs.T


def match_source_moments(target: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    """Affine-normalize target to source mean and covariance (sample version)."""
    t = target[["x", "y"]].to_numpy(float)
    s = source[["x", "y"]].to_numpy(float)
    mt, ms = t.mean(axis=0), s.mean(axis=0)
    ct = np.cov(t, rowvar=False, ddof=1)
    cs = np.cov(s, rowvar=False, ddof=1)
    transform = _sqrt_cov(cs) @ _sqrt_cov(ct, inverse=True)
    mapped = (t - mt) @ transform.T + ms
    return pd.DataFrame(mapped, columns=["x", "y"])


def target_distance(point: np.ndarray, goal: np.ndarray) -> float:
    return float(np.sum((point - goal) ** 2))


def nearest_target_distance(point: np.ndarray, target: np.ndarray) -> float:
    return float(np.min(np.sum((target - point) ** 2, axis=1)))


def save_frame(current: pd.DataFrame, target: pd.DataFrame, path: Path, iteration: int) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(target.x, target.y, s=18, color="#d62728", alpha=.28, label="目标点阵")
    ax.scatter(current.x, current.y, s=22, color="#202020", alpha=.8, label="当前点阵")
    ax.set(xlim=(-5, 105), ylim=(-5, 105), aspect="equal", xlabel="x", ylabel="y")
    ax.set_title(f"iteration = {iteration:,}")
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run(source: pd.DataFrame, target: pd.DataFrame, output: Path, iterations: int, frames: int,
        decimals: int, seed: int, shake: float = .1) -> pd.DataFrame:
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    current = source[["x", "y"]].to_numpy(float).copy()
    # Keep an immutable reference for the five-statistic acceptance rule.
    # Comparing against the moving state would make the constraint ambiguous
    # if a proposal ever crossed a rounding bin.
    reference = current.copy()
    target = target[["x", "y"]].to_numpy(float).copy()
    if len(current) != len(target):
        raise ValueError(f"source and target must have the same number of points ({len(current)} != {len(target)})")
    # Save approximately uniform checkpoints, including the starting state.
    checkpoints = np.linspace(0, iterations, frames, dtype=int)
    checkpoint_set = set(int(x) for x in checkpoints)
    records = []
    initial_stats = stats_array(current)
    for i in range(iterations + 1):
        if i in checkpoint_set:
            tag = int(np.where(checkpoints == i)[0][0])
            current_df = pd.DataFrame(current, columns=["x", "y"])
            target_df = pd.DataFrame(target, columns=["x", "y"])
            current_df.to_csv(output / f"data-{tag:05d}.csv", index=False)
            save_frame(current_df, target_df, output / f"image-{tag:05d}.png", i)
            records.append({"frame": tag, "iteration": i,
                            "mean_squared_assignment_error": float(np.mean(np.sum((current - target) ** 2, axis=1))),
                            "mean_nearest_target_error": float(np.mean(np.min(np.sum((current[:, None, :] - target[None, :, :]) ** 2, axis=2), axis=1))),
                            "max_abs_statistic_difference": float(np.max(np.abs(stats_array(current) - initial_stats)))})
        if i == iterations:
            break
        row = int(rng.integers(0, len(current)))
        old = current[row].copy()
        proposed = old + rng.normal(0, shake, size=2)
        if not (0 < proposed[0] < 100 and 0 < proposed[1] < 100):
            continue
        temperature = .4 * (1 - i / iterations)
        # As in the course's built-in circle objective, a point is judged by
        # its distance to the nearest part of the target, not by a fixed label.
        old_error = nearest_target_distance(old, target)
        new_error = nearest_target_distance(proposed, target)
        accept_bad = rng.random() < temperature
        if (new_error < old_error or new_error < 4 or accept_bad):
            trial = current.copy()
            trial[row] = proposed
            if stats_allowed(trial, reference, decimals):
                current = trial
    pd.DataFrame(records).to_csv(output / "metrics.csv", index=False)
    return pd.DataFrame(current, columns=["x", "y"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--iterations", type=int, default=60000)
    parser.add_argument("--frames", type=int, default=61)
    parser.add_argument("--decimals", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260914)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    try:
        source = pd.read_csv(args.source)
        if "x" not in source.columns or "y" not in source.columns:
            source = pd.read_csv(args.source, header=None, names=["x", "y"])
        else:
            source = source[["x", "y"]].astype(float)
    except Exception:
        source = pd.read_csv(args.source, header=None, names=["x", "y"])
    target = pd.read_csv(args.target)
    target = match_source_moments(target, source)
    target.to_csv(args.output / "normalized_target.csv", index=False)
    final = run(source, target, args.output, args.iterations, args.frames, args.decimals, args.seed)
    print("source stats:", stats(source))
    print("normalized target stats:", stats(target))
    print("final stats:", stats(final))


if __name__ == "__main__":
    main()
