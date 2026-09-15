"""Convert a hand-drawn PNG silhouette to a reproducible x,y point cloud.

Example:
    python image_to_points.py path\\to\\shape.png --output course_source\\seed_datasets\\mydata.csv --points 142

Draw a black shape on a white background in Paint.  The output uses the same
0--100 coordinate range expected by the course's same_stats.py script.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn a dark raster drawing into an x,y point cloud.")
    parser.add_argument("image", type=Path, help="PNG/JPG with dark ink on a light background")
    parser.add_argument("--output", type=Path, default=Path("seed_datasets/mydata.csv"))
    parser.add_argument("--points", type=int, default=142, help="Number of sampled points; 142 matches Datasaurus")
    parser.add_argument("--threshold", type=int, default=180, help="Grayscale values below this count as ink")
    parser.add_argument("--light-ink", action="store_true", help="Treat bright pixels as ink (for white text on a dark background)")
    parser.add_argument("--boundary", action="store_true", help="Sample the mask boundary with farthest-point sampling to preserve thin outlines")
    parser.add_argument("--components", action="store_true", help="Allocate boundary samples across connected components (useful for logos and lettering)")
    parser.add_argument("--seed", type=int, default=20260914, help="Fixed random seed for reproducibility")
    args = parser.parse_args()
    if args.points < 2:
        parser.error("--points must be at least 2")

    image = Image.open(args.image).convert("L")
    gray = np.asarray(image)
    rng = np.random.default_rng(args.seed)
    mask = gray > args.threshold if args.light_ink else gray < args.threshold
    if args.boundary:
        if args.components:
            # Keep each connected stroke/character represented instead of
            # letting the largest outline consume all farthest-point samples.
            labels, count = ndimage.label(mask)
            component_candidates = []
            for label in range(1, count + 1):
                component = labels == label
                boundary = component ^ ndimage.binary_erosion(component, structure=np.ones((3, 3)), border_value=0)
                r_part, c_part = np.where(boundary)
                if len(r_part):
                    component_candidates.append(np.column_stack((c_part, r_part)).astype(float))
            if not component_candidates:
                parser.error("No connected ink components found")
            weights = np.array([len(c) for c in component_candidates], dtype=float)
            quotas = np.ones(len(weights), dtype=int)
            remaining = args.points - len(quotas)
            if remaining < 0:
                parser.error("--points must be at least the number of connected components")
            raw = remaining * weights / weights.sum()
            quotas += np.floor(raw).astype(int)
            for idx in np.argsort(-(raw - np.floor(raw)))[:remaining - int(np.floor(raw).sum())]:
                quotas[idx] += 1
            selected_parts = []
            for candidates, quota in zip(component_candidates, quotas):
                if len(candidates) <= quota:
                    selected_parts.append(candidates)
                    continue
                selected = [int(rng.integers(0, len(candidates)))]
                min_dist = np.full(len(candidates), np.inf)
                for _ in range(1, quota):
                    last = candidates[selected[-1]]
                    min_dist = np.minimum(min_dist, np.sum((candidates - last) ** 2, axis=1))
                    min_dist[selected] = -1
                    selected.append(int(np.argmax(min_dist)))
                selected_parts.append(candidates[np.asarray(selected)])
            candidates = np.vstack(selected_parts)
            cols = candidates[:, 0].astype(int)
            rows = candidates[:, 1].astype(int)
            choose = np.arange(len(rows))
        else:
            mask = mask ^ ndimage.binary_erosion(mask, structure=np.ones((3, 3)), border_value=0)
            rows, cols = np.where(mask)
    else:
        rows, cols = np.where(mask)
    if len(rows) < args.points:
        parser.error(f"Only {len(rows)} dark pixels found; draw a thicker/darker shape or lower --points.")

    if args.boundary and not args.components:
        candidates = np.column_stack((cols, rows)).astype(float)
        chosen = [int(rng.integers(0, len(candidates)))]
        min_dist = np.full(len(candidates), np.inf)
        for _ in range(1, args.points):
            last = candidates[chosen[-1]]
            min_dist = np.minimum(min_dist, np.sum((candidates - last) ** 2, axis=1))
            min_dist[chosen] = -1
            chosen.append(int(np.argmax(min_dist)))
        choose = np.asarray(chosen)
    else:
        choose = rng.choice(len(rows), size=args.points, replace=False)
    # x is horizontal pixel position; y is flipped so the visual orientation is preserved.
    x = cols[choose] / (image.width - 1) * 100
    y = (image.height - 1 - rows[choose]) / (image.height - 1) * 100
    out = pd.DataFrame({"x": x, "y": y})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"Wrote {len(out)} points to {args.output.resolve()}")


if __name__ == "__main__":
    main()
