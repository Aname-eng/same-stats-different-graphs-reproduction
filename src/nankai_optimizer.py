"""Full Multi-Seed Nankai Emblem Evolution Optimizer with 3-Point Invariant Kernel."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt

from src.stats_audit import (
    stats5, signature2, is_legal, BOUNDS_0_100, REF_SIGNATURE, MU_0, COV_0
)
from moment_preserving_moves import _K

LAYER_NAMES = ["nan", "kai", "octagram", "mid_ring", "outer_ring"]

class NankaiEvolutionOptimizer:
    def __init__(
        self,
        seed_csv: Path,
        slots_csv: Path,
        random_seed: int = 42,
        output_dir: Path = Path("output/seed_42"),
        reassign_interval: int = 500,
        stagnation_window: int = 4000,
    ):
        self.random_seed = random_seed
        self.rng = np.random.default_rng(random_seed)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "snapshots").mkdir(parents=True, exist_ok=True)

        # Load seed points
        df_seed = pd.read_csv(seed_csv)
        self.points = df_seed[["x", "y"]].to_numpy(float)
        self.point_ids = df_seed["point_id"].to_numpy(int) if "point_id" in df_seed else np.arange(len(self.points))
        self.n = len(self.points)

        # Verify initial seed strictly passes hard gate
        if not is_legal(self.points, self.n, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100):
            raise ValueError("Initial seed does not pass is_legal gate")

        # Load target slots
        df_slots = pd.read_csv(slots_csv)
        self.slots = df_slots[["x", "y"]].to_numpy(float)
        self.slot_layer_ids = df_slots["layer_id"].to_numpy(int)
        assert len(self.slots) == self.n, f"Slots count {len(self.slots)} != points count {self.n}"

        self.reassign_interval = reassign_interval
        self.stagnation_window = stagnation_window

        # Initial assignment via Linear Sum Assignment
        cost = np.sum((self.points[:, None, :] - self.slots[None, :, :])**2, axis=2)
        _, col_ind = linear_sum_assignment(cost)
        self.assignment = col_ind.copy()

        self.current_energy = self.compute_energy(self.points, self.assignment)
        self.best_energy = self.current_energy
        self.best_points = self.points.copy()
        self.best_assignment = self.assignment.copy()

        # Audit logs and tracking
        self.metrics_log = []
        self.stagnation_events = []
        self.accepted_count = 0
        self.proposal_count = 0

    def compute_energy(self, pts: np.ndarray, assign: np.ndarray) -> float:
        """Normalized squared matching loss (mean squared distance)."""
        diff = pts - self.slots[assign]
        return float(np.mean(np.sum(diff**2, axis=1)))

    def compute_layer_metrics(self, pts: np.ndarray, assign: np.ndarray) -> dict[str, dict[str, float]]:
        diffs = np.sqrt(np.sum((pts - self.slots[assign])**2, axis=1))
        metrics = {}
        for l_id, l_name in enumerate(LAYER_NAMES):
            m = (self.slot_layer_ids[assign] == l_id)
            if np.any(m):
                d_layer = diffs[m]
                metrics[l_name] = {
                    "count": int(np.sum(m)),
                    "mean_dist": float(np.mean(d_layer)),
                    "median_dist": float(np.median(d_layer)),
                    "max_dist": float(np.max(d_layer)),
                    "p90_dist": float(np.percentile(d_layer, 90))
                }
            else:
                metrics[l_name] = {"count": 0, "mean_dist": 0.0, "max_dist": 0.0}
        return metrics

    def update_assignment(self):
        cost = np.sum((self.points[:, None, :] - self.slots[None, :, :])**2, axis=2)
        _, col_ind = linear_sum_assignment(cost)
        self.assignment = col_ind.copy()
        self.current_energy = self.compute_energy(self.points, self.assignment)
        if self.current_energy < self.best_energy:
            self.best_energy = self.current_energy
            self.best_points = self.points.copy()
            self.best_assignment = self.assignment.copy()

    def save_snapshot(self, step: int, is_final: bool = False):
        snap_csv = self.output_dir / "snapshots" / f"frame_{step:06d}.csv"
        assigned_lids = self.slot_layer_ids[self.assignment]
        df_out = pd.DataFrame({
            "point_id": self.point_ids,
            "x": self.points[:, 0],
            "y": self.points[:, 1],
            "assigned_slot_id": self.assignment,
            "assigned_layer_id": assigned_lids,
            "assigned_layer_name": [LAYER_NAMES[i] for i in assigned_lids]
        })
        df_out.to_csv(snap_csv, index=False)

        # 1. Pure scatter plot of actual data points
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.scatter(self.points[:, 0], self.points[:, 1], s=14, color="#1f77b4", edgecolors="none", alpha=0.9)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        sig = signature2(self.points, ddof=1)
        ax.set_title(f"Step {step:06d} (N={self.n})\nSig: {sig} | MSE: {self.current_energy:.2f}", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        pure_path = self.output_dir / "snapshots" / f"frame_{step:06d}_pure.png"
        fig.savefig(pure_path, dpi=180)
        plt.close(fig)

        # 2. Diagnostic plot with layer coloring and faint target slots
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.scatter(self.slots[:, 0], self.slots[:, 1], s=10, color="#d3d3d3", alpha=0.5, label="Target Slots")
        colors = ["#d62728", "#9467bd", "#ff7f0e", "#2ca02c", "#1f77b4"]
        for l_id, l_name in enumerate(LAYER_NAMES):
            m = (assigned_lids == l_id)
            if np.any(m):
                ax.scatter(self.points[m, 0], self.points[m, 1], s=14, color=colors[l_id], label=f"{l_name} ({np.sum(m)})", alpha=0.85)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_aspect("equal")
        ax.set_title(f"Diagnostic Step {step:06d}\nMSE: {self.current_energy:.2f}", fontsize=10)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
        ax.grid(True, linestyle="--", alpha=0.3)
        diag_path = self.output_dir / "snapshots" / f"frame_{step:06d}_diagnostic.png"
        fig.savefig(diag_path, dpi=180)
        plt.close(fig)

    def optimize(self, total_steps: int = 100000, snapshot_interval: int = 20000):
        t0 = time.time()
        print(f"[{time.strftime('%X')}] Seed {self.random_seed}: Starting optimization for {total_steps} steps...")
        self.save_snapshot(0)

        # Stagnation tracking
        recent_energies = [self.current_energy]
        reheat_temp = 0.0

        for step in range(1, total_steps + 1):
            self.proposal_count += 1

            # Global matching update
            if step % self.reassign_interval == 0:
                self.update_assignment()

            # Stagnation check
            if step % self.stagnation_window == 0:
                past_e = recent_energies[0]
                curr_e = self.current_energy
                rel_imprv = (past_e - curr_e) / max(past_e, 1e-4)
                recent_energies = [curr_e]
                if rel_imprv < 0.005:
                    # Trigger stagnation recovery
                    event = {
                        "step": step,
                        "cause": f"Relative improvement {rel_imprv:.4f} < 0.005 over {self.stagnation_window} steps",
                        "action": "reassign + boost angle exploration + soft reheat"
                    }
                    self.stagnation_events.append(event)
                    self.update_assignment()
                    reheat_temp = 0.02
                else:
                    reheat_temp = max(0.0, reheat_temp * 0.8)

            # Adaptive proposal selection
            errs = np.sum((self.points - self.slots[self.assignment])**2, axis=1)
            err_probs = errs / errs.sum()

            strat = self.rng.random()
            if strat < 0.45:
                # Weighted: pick 1 high-error point and 2 random
                i1 = self.rng.choice(self.n, p=err_probs)
                i2, i3 = self.rng.choice(self.n, 2, replace=False)
                while i2 == i1 or i3 == i1:
                    i2, i3 = self.rng.choice(self.n, 2, replace=False)
                ix = np.array([i1, i2, i3])
            elif strat < 0.75:
                # Spatial neighborhood triad
                i1 = self.rng.choice(self.n)
                dists = np.sum((self.points - self.points[i1])**2, axis=1)
                near = np.argsort(dists)[1:15]
                i2, i3 = self.rng.choice(near, 2, replace=False)
                ix = np.array([i1, i2, i3])
            else:
                # Uniform triad
                ix = self.rng.choice(self.n, 3, replace=False)

            b = self.points[ix]
            center = b.mean(axis=0)
            z = b - center
            kz = _K @ z
            y = self.slots[self.assignment[ix]]

            a = np.sum(z * y)
            b_val = np.sum(kz * y)
            th_star = np.arctan2(b_val, a)

            # Proposal angle
            mode = self.rng.random()
            if mode < 0.55:
                th = th_star
            elif mode < 0.80:
                th = th_star * self.rng.uniform(0.15, 0.75)
            else:
                th = float(self.rng.normal(0, 0.12))

            cand_b = center + np.cos(th) * z + np.sin(th) * kz

            # Bounds check [0.5, 99.5]
            if np.any(cand_b < 0.5) or np.any(cand_b > 99.5):
                continue

            old_3_err = np.sum((b - y)**2)
            new_3_err = np.sum((cand_b - y)**2)
            delta_e = (new_3_err - old_3_err) / self.n

            # Temperature schedule
            base_temp = max(0.0002, 0.25 * (1.0 - step / total_steps)**2)
            temp = base_temp + reheat_temp

            if delta_e < 0 or (temp > 1e-5 and self.rng.random() < np.exp(-delta_e / temp)):
                cand_points = self.points.copy()
                cand_points[ix] = cand_b
                # Hard gate check
                if signature2(cand_points, ddof=1) == REF_SIGNATURE:
                    self.points = cand_points
                    self.current_energy += delta_e
                    self.accepted_count += 1
                    if self.current_energy < self.best_energy:
                        self.best_energy = self.current_energy
                        self.best_points = self.points.copy()
                        self.best_assignment = self.assignment.copy()

            # Snapshot logging
            if step % snapshot_interval == 0:
                self.update_assignment()
                self.save_snapshot(step)
                elapsed = time.time() - t0
                acc_rate = self.accepted_count / self.proposal_count
                l_mets = self.compute_layer_metrics(self.points, self.assignment)
                entry = {
                    "step": step,
                    "elapsed_sec": round(elapsed, 2),
                    "energy_mse": round(self.current_energy, 4),
                    "accepted_count": self.accepted_count,
                    "acceptance_rate": round(acc_rate, 4),
                    "stats5": stats5(self.points, ddof=1).tolist(),
                    "signature2": list(signature2(self.points, ddof=1)),
                    "layer_metrics": l_mets
                }
                self.metrics_log.append(entry)
                print(
                    f"[{time.strftime('%X')}] Step {step:6d}/{total_steps} | "
                    f"MSE: {self.current_energy:6.2f} | Acc: {acc_rate*100:4.1f}% | "
                    f"Time: {elapsed:5.1f}s | Sig: {entry['signature2']}"
                )

        # Final global update and snapshot
        self.update_assignment()
        self.save_snapshot(total_steps, is_final=True)
        total_time = time.time() - t0

        summary = {
            "random_seed": self.random_seed,
            "n_points": self.n,
            "total_steps": total_steps,
            "total_time_seconds": round(total_time, 2),
            "final_energy_mse": round(self.current_energy, 4),
            "best_energy_mse": round(self.best_energy, 4),
            "final_stats5": stats5(self.points, ddof=1).tolist(),
            "final_signature2": list(signature2(self.points, ddof=1)),
            "matches_ref_signature": (signature2(self.points, ddof=1) == REF_SIGNATURE),
            "accepted_proposals": self.accepted_count,
            "overall_acceptance_rate": round(self.accepted_count / self.proposal_count, 4),
            "stagnation_events": self.stagnation_events,
            "final_layer_metrics": self.compute_layer_metrics(self.points, self.assignment),
            "history": self.metrics_log
        }

        with open(self.output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Seed {self.random_seed} finished in {total_time:.2f}s. Metrics saved to {self.output_dir / 'metrics.json'}")
        return summary

def main():
    parser = argparse.ArgumentParser(description="Run Nankai emblem evolution.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--seed-csv", type=Path, default=Path("seed_568.csv"))
    parser.add_argument("--slots-csv", type=Path, default=Path("targets/target_slots_568.csv"))
    parser.add_argument("--steps", type=int, default=80000, help="Total optimization steps")
    parser.add_argument("--snapshot-interval", type=int, default=20000, help="Snapshot interval")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.output_dir or Path(f"output/evolution_seed_{args.seed}")
    opt = NankaiEvolutionOptimizer(
        seed_csv=args.seed_csv,
        slots_csv=args.slots_csv,
        random_seed=args.seed,
        output_dir=out_dir
    )
    opt.optimize(total_steps=args.steps, snapshot_interval=args.snapshot_interval)

if __name__ == "__main__":
    main()
