"""Create reproducible flower targets and equal-size Datasaurus sources.

The original Datasaurus has 142 observations.  Repeating every observation
twice creates a 284-point source without changing its mean, sample standard
deviations, or Pearson correlation.  The same construction is used for the
target point cloud, so the annealing runner can compare equal-sized clouds.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from run_custom_target import match_source_moments


ROOT = Path.cwd()
SOURCE = ROOT / "course_source" / "seed_datasets" / "Datasaurus_data.csv"
TARGETS = ROOT / "targets"


def flower(n: int, petals: int = 5) -> pd.DataFrame:
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    radius = 28.0 + 11.0 * np.cos(petals * theta)
    return pd.DataFrame({"x": 50.0 + radius * np.cos(theta),
                         "y": 50.0 + radius * np.sin(theta)})


def main() -> None:
    TARGETS.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(SOURCE, header=None, names=["x", "y"])
    flower(142).to_csv(TARGETS / "flower_142.csv", index=False)
    flower(284).to_csv(TARGETS / "flower_284.csv", index=False)
    # Duplication preserves the mean and correlation, but pandas' sample
    # standard deviation has an (N-1) denominator.  Affine-normalize the
    # duplicated cloud back to the 142-point mean/covariance before saving;
    # this makes the point-count change explicit while keeping all five
    # reference statistics unchanged.
    expanded = pd.concat([base, base], ignore_index=True)
    expanded = match_source_moments(expanded, base)
    expanded.to_csv(TARGETS / "dino_284.csv", index=False, header=False)
    print("created flower_142.csv, flower_284.csv, and dino_284.csv")


if __name__ == "__main__":
    main()
