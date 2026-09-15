"""Ground Truth Verification Geometry (G_verify) and Structural Acceptance."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree
from src.stats_audit import MU_0

GEOMETRY_LAYERS = ["outer_ring", "inner_ring", "octagram", "stroke_nan", "stroke_kai"]

# Frozen acceptance thresholds for final geometry
THRESHOLDS = {
    "outer_ring": {"max_mean_dist": 2.0, "max_p95_dist": 3.5, "min_coverage_ratio": 0.85, "max_gap_length": 6.0},
    "inner_ring": {"max_mean_dist": 2.2, "max_p95_dist": 3.8, "min_coverage_ratio": 0.80, "max_gap_length": 6.0},
    "octagram":   {"max_mean_dist": 2.2, "max_p95_dist": 3.8, "min_coverage_ratio": 0.80, "max_gap_length": 5.0},
    "stroke_nan": {"max_mean_dist": 2.0, "max_p95_dist": 3.5, "min_coverage_ratio": 0.80, "max_gap_length": 4.0},
    "stroke_kai": {"max_mean_dist": 2.0, "max_p95_dist": 3.5, "min_coverage_ratio": 0.80, "max_gap_length": 4.0},
    "tolerance_tau": 2.5  # distance threshold in data units to consider a curve point 'covered'
}

class GroundTruthGeometry:
    def __init__(self, image_path: Path = Path("南开校徽.jpg")):
        self.scale = 41.9 / 358.0
        self.r_out = 41.9
        self.r_in = 28.0
        self.r_star_in = 19.95
        self.mu_0 = MU_0.copy()

        self.curves: dict[str, np.ndarray] = {}
        self.arc_lengths: dict[str, float] = {}
        self._build_ground_truth(image_path)

    def _build_ground_truth(self, image_path: Path):
        # 1. Outer Ring (circle) - 600 points
        theta_out = np.linspace(0, 2 * np.pi, 600, endpoint=False)
        pts_out = np.column_stack((
            self.mu_0[0] + self.r_out * np.cos(theta_out),
            self.mu_0[1] + self.r_out * np.sin(theta_out)
        ))
        self.curves["outer_ring"] = pts_out
        self.arc_lengths["outer_ring"] = float(2 * np.pi * self.r_out)

        # 2. Inner Ring (circle) - 400 points
        theta_in = np.linspace(0, 2 * np.pi, 400, endpoint=False)
        pts_in = np.column_stack((
            self.mu_0[0] + self.r_in * np.cos(theta_in),
            self.mu_0[1] + self.r_in * np.sin(theta_in)
        ))
        self.curves["inner_ring"] = pts_in
        self.arc_lengths["inner_ring"] = float(2 * np.pi * self.r_in)

        # 3. Octagram (16 star edges) - 480 points (30 per edge)
        angles_outer = np.linspace(0, 2 * np.pi, 8, endpoint=False) + np.pi / 8
        angles_inner = angles_outer + np.pi / 8
        verts = []
        for k in range(8):
            verts.append([self.mu_0[0] + self.r_in * np.cos(angles_outer[k]), self.mu_0[1] + self.r_in * np.sin(angles_outer[k])])
            verts.append([self.mu_0[0] + self.r_star_in * np.cos(angles_inner[k]), self.mu_0[1] + self.r_star_in * np.sin(angles_inner[k])])
        verts = np.array(verts)

        star_pts = []
        total_star_len = 0.0
        for k in range(16):
            v1 = verts[k]
            v2 = verts[(k + 1) % 16]
            total_star_len += float(np.linalg.norm(v2 - v1))
            t = np.linspace(0, 1, 30, endpoint=False)
            star_pts.append(v1[None, :] + t[:, None] * (v2 - v1)[None, :])
        self.curves["octagram"] = np.vstack(star_pts)
        self.arc_lengths["octagram"] = total_star_len

        # 4 & 5. Medial axis strokes for 'nan' and 'kai' from original image
        if not image_path.exists():
            raise FileNotFoundError(f"Original image not found: {image_path}")
        img = Image.open(image_path).convert("L")
        arr = np.asarray(img)
        mask = (arr < 150)
        h, w = mask.shape
        cy, cx = 395.0, 400.5
        y_grid, x_grid = np.indices((h, w))
        dist_c = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)

        m_nan = mask & (dist_c < 140) & (x_grid < 400)
        m_kai = mask & (dist_c < 140) & (x_grid >= 400)

        def get_medial(m: np.ndarray, thresh: float = 1.0) -> np.ndarray:
            dt = ndimage.distance_transform_edt(m)
            h_max = (dt > thresh) & (dt >= np.roll(dt, 1, axis=1)) & (dt >= np.roll(dt, -1, axis=1))
            v_max = (dt > thresh) & (dt >= np.roll(dt, 1, axis=0)) & (dt >= np.roll(dt, -1, axis=0))
            d1_max = (dt > thresh) & (dt >= np.roll(np.roll(dt, 1, axis=0), 1, axis=1)) & (dt >= np.roll(np.roll(dt, -1, axis=0), -1, axis=1))
            d2_max = (dt > thresh) & (dt >= np.roll(np.roll(dt, 1, axis=0), -1, axis=1)) & (dt >= np.roll(np.roll(dt, -1, axis=0), 1, axis=1))
            sk = h_max | v_max | d1_max | d2_max
            ys, xs = np.where(sk)
            dx = (xs - cx) * self.scale
            dy = -(ys - cy) * self.scale
            pts = np.column_stack((dx + self.mu_0[0], dy + self.mu_0[1]))
            # Subsample to deterministic dense set (~400 points each)
            step = max(1, len(pts) // 400)
            return pts[::step]

        self.curves["stroke_nan"] = get_medial(m_nan)
        self.curves["stroke_kai"] = get_medial(m_kai)
        self.arc_lengths["stroke_nan"] = float(len(self.curves["stroke_nan"]) * 0.25)
        self.arc_lengths["stroke_kai"] = float(len(self.curves["stroke_kai"]) * 0.25)

    def evaluate(self, points: np.ndarray) -> dict:
        """Evaluate point cloud against ground truth verification geometry."""
        p = np.asarray(points, dtype=np.float64)
        tree_p = cKDTree(p)
        tau = THRESHOLDS["tolerance_tau"]

        layer_results = {}
        all_passed = True
        reason_codes = []

        for name in GEOMETRY_LAYERS:
            curve = self.curves[name]
            dists, _ = tree_p.query(curve)

            mean_d = float(np.mean(dists))
            p95_d = float(np.percentile(dists, 95))
            max_d = float(np.max(dists))
            cov_ratio = float(np.mean(dists <= tau))

            # Max contiguous gap length
            is_gap = (dists > tau)
            max_gap_count = 0
            curr_gap = 0
            for val in is_gap:
                if val:
                    curr_gap += 1
                    max_gap_count = max(max_gap_count, curr_gap)
                else:
                    curr_gap = 0
            # Convert count to approximate arc length
            seg_len = self.arc_lengths[name] / len(curve)
            max_gap_len = float(max_gap_count * seg_len)

            thresh = THRESHOLDS[name]
            layer_ok = (
                mean_d <= thresh["max_mean_dist"] and
                p95_d <= thresh["max_p95_dist"] and
                cov_ratio >= thresh["min_coverage_ratio"] and
                max_gap_len <= thresh["max_gap_length"]
            )

            if not layer_ok:
                all_passed = False
                reason_codes.append(f"GEOMETRY_{name.upper()}_FAILED")

            layer_results[name] = {
                "mean_dist": round(mean_d, 3),
                "p95_dist": round(p95_d, 3),
                "max_dist": round(max_d, 3),
                "coverage_ratio": round(cov_ratio, 3),
                "max_gap_length": round(max_gap_len, 3),
                "thresholds": thresh,
                "passed": layer_ok
            }

        return {
            "final_geometry_pass": all_passed,
            "reason_codes": reason_codes,
            "layer_evaluations": layer_results
        }
