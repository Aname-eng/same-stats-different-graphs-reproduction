"""Benchmark comparison across Methods A, B, C, D on identical N and initial seed."""
from __future__ import annotations
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from src.stats_audit import stats5, signature2, is_legal, REF_SIGNATURE, BOUNDS_0_100
from moment_preserving_moves import _K
from run_custom_target import stats_allowed

def run_comparison(seed: int = 42, steps: int = 15000, output_path: Path = Path("analysis/method_comparison_report.json")):
    df_seed = pd.read_csv("seed_568.csv")
    p_init = df_seed[["x", "y"]].to_numpy(float)
    N = len(p_init)

    df_slots = pd.read_csv("targets/target_slots_568.csv")
    slots = df_slots[["x", "y"]].to_numpy(float)
    tree_slots = cKDTree(slots)

    results = {}

    # ----------------------------------------------------
    # Method A: Legacy 1-way distance + single-point perturbation
    # ----------------------------------------------------
    print(f"Running Method A (Legacy 1-way distance + 1-point)...")
    rng = np.random.default_rng(seed)
    p_a = p_init.copy()
    ref_a = p_init.copy()
    t0 = time.time()
    acc_a_floor = 0
    acc_a_round2 = 0
    props_a = 0

    for step in range(steps):
        row = rng.integers(0, N)
        old_pt = p_a[row].copy()
        # nearest target distance
        d_old, _ = tree_slots.query(old_pt)

        xm = old_pt[0] + rng.normal(0, 0.4)
        ym = old_pt[1] + rng.normal(0, 0.4)
        if not (0.5 <= xm <= 99.5 and 0.5 <= ym <= 99.5):
            continue

        props_a += 1
        cand_pt = np.array([xm, ym])
        d_new, _ = tree_slots.query(cand_pt)

        if d_new < d_old or rng.random() < 0.05:
            cand = p_a.copy()
            cand[row] = cand_pt
            # Test legacy floor standard
            pass_floor = stats_allowed(cand, ref_a, decimals=2)
            # Test round2 standard
            pass_round2 = (signature2(cand, ddof=1) == REF_SIGNATURE)

            if pass_floor:
                acc_a_floor += 1
                p_a = cand
            if pass_round2:
                acc_a_round2 += 1

    t_a = time.time() - t0
    d_final_a, _ = tree_slots.query(p_a)
    results["Method_A_Legacy_Unidirectional_1pt"] = {
        "description": "Legacy 1-way distance + single-point perturbations",
        "steps": steps,
        "time_seconds": round(t_a, 2),
        "proposals": props_a,
        "accepted_under_legacy_floor": acc_a_floor,
        "acc_rate_legacy_floor": round(acc_a_floor / max(props_a, 1), 5),
        "acc_rate_round2": round(acc_a_round2 / max(props_a, 1), 5),
        "final_mean_dist_to_target": float(np.mean(d_final_a)),
        "final_signature2": list(signature2(p_a, ddof=1)),
        "matches_round2_signature": (signature2(p_a, ddof=1) == REF_SIGNATURE),
        "is_legal_round2": is_legal(p_a, N, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100)
    }

    # ----------------------------------------------------
    # Method B: Capacity matching + single-point perturbation
    # ----------------------------------------------------
    print(f"Running Method B (Capacity match + 1-point)...")
    rng = np.random.default_rng(seed)
    p_b = p_init.copy()
    ref_b = p_init.copy()

    # Initial assignment
    cost_b = np.sum((p_b[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_b = linear_sum_assignment(cost_b)
    assign_b = col_ind_b.copy()

    t0 = time.time()
    acc_b = 0
    props_b = 0

    for step in range(steps):
        if step > 0 and step % 500 == 0:
            cost_b = np.sum((p_b[:, None, :] - slots[None, :, :])**2, axis=2)
            _, col_ind_b = linear_sum_assignment(cost_b)
            assign_b = col_ind_b.copy()

        row = rng.integers(0, N)
        old_pt = p_b[row]
        target_pt = slots[assign_b[row]]
        d_old = np.sum((old_pt - target_pt)**2)

        xm = old_pt[0] + rng.normal(0, 0.4)
        ym = old_pt[1] + rng.normal(0, 0.4)
        if not (0.5 <= xm <= 99.5 and 0.5 <= ym <= 99.5):
            continue

        props_b += 1
        cand_pt = np.array([xm, ym])
        d_new = np.sum((cand_pt - target_pt)**2)

        if d_new < d_old or rng.random() < 0.05:
            cand = p_b.copy()
            cand[row] = cand_pt
            if signature2(cand, ddof=1) == REF_SIGNATURE:
                acc_b += 1
                p_b = cand

    t_b = time.time() - t0
    cost_b = np.sum((p_b[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_b = linear_sum_assignment(cost_b)
    mse_b = float(np.mean(np.sum((p_b - slots[col_ind_b])**2, axis=1)))
    results["Method_B_Capacity_1pt"] = {
        "description": "Capacity-constrained matching + single-point perturbations",
        "steps": steps,
        "time_seconds": round(t_b, 2),
        "proposals": props_b,
        "accepted_under_round2": acc_b,
        "acc_rate_round2": round(acc_b / max(props_b, 1), 5),
        "final_mse": round(mse_b, 3),
        "final_signature2": list(signature2(p_b, ddof=1)),
        "matches_round2_signature": (signature2(p_b, ddof=1) == REF_SIGNATURE),
        "is_legal_round2": is_legal(p_b, N, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100)
    }

    # ----------------------------------------------------
    # Method C: Capacity matching + 3-point moves (analytic theta)
    # ----------------------------------------------------
    print(f"Running Method C (Capacity match + 3-point kernel)...")
    rng = np.random.default_rng(seed)
    p_c = p_init.copy()
    cost_c = np.sum((p_c[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_c = linear_sum_assignment(cost_c)
    assign_c = col_ind_c.copy()

    t0 = time.time()
    acc_c = 0
    props_c = 0

    for step in range(steps):
        if step > 0 and step % 500 == 0:
            cost_c = np.sum((p_c[:, None, :] - slots[None, :, :])**2, axis=2)
            _, col_ind_c = linear_sum_assignment(cost_c)
            assign_c = col_ind_c.copy()

        ix = rng.choice(N, 3, replace=False)
        b = p_c[ix]
        center = b.mean(axis=0)
        z = b - center
        kz = _K @ z
        y = slots[assign_c[ix]]

        a = np.sum(z * y)
        b_val = np.sum(kz * y)
        th_star = np.arctan2(b_val, a)

        th = th_star if rng.random() < 0.7 else float(rng.normal(0, 0.12))
        cand_b = center + np.cos(th) * z + np.sin(th) * kz
        if np.any(cand_b < 0.5) or np.any(cand_b > 99.5):
            continue

        props_c += 1
        cand = p_c.copy()
        cand[ix] = cand_b
        if signature2(cand, ddof=1) == REF_SIGNATURE:
            d_old = np.sum((b - y)**2)
            d_new = np.sum((cand_b - y)**2)
            if d_new < d_old:
                acc_c += 1
                p_c = cand

    t_c = time.time() - t0
    cost_c = np.sum((p_c[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_c = linear_sum_assignment(cost_c)
    mse_c = float(np.mean(np.sum((p_c - slots[col_ind_c])**2, axis=1)))
    results["Method_C_Capacity_3pt_Invariance"] = {
        "description": "Capacity matching + exact 3-point invariant moves",
        "steps": steps,
        "time_seconds": round(t_c, 2),
        "proposals": props_c,
        "accepted_under_round2": acc_c,
        "acc_rate_round2": round(acc_c / max(props_c, 1), 5),
        "final_mse": round(mse_c, 3),
        "final_signature2": list(signature2(p_c, ddof=1)),
        "matches_round2_signature": (signature2(p_c, ddof=1) == REF_SIGNATURE),
        "is_legal_round2": is_legal(p_c, N, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100)
    }

    # ----------------------------------------------------
    # Method D: Method C + stagnation recovery & adaptive selection
    # ----------------------------------------------------
    print(f"Running Method D (Method C + stagnation recovery + residual selection)...")
    rng = np.random.default_rng(seed)
    p_d = p_init.copy()
    cost_d = np.sum((p_d[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_d = linear_sum_assignment(cost_d)
    assign_d = col_ind_d.copy()

    t0 = time.time()
    acc_d = 0
    props_d = 0

    for step in range(steps):
        if step > 0 and step % 500 == 0:
            cost_d = np.sum((p_d[:, None, :] - slots[None, :, :])**2, axis=2)
            _, col_ind_d = linear_sum_assignment(cost_d)
            assign_d = col_ind_d.copy()

        errs = np.sum((p_d - slots[assign_d])**2, axis=1)
        err_probs = errs / errs.sum()

        if rng.random() < 0.5:
            i1 = rng.choice(N, p=err_probs)
            i2, i3 = rng.choice(N, 2, replace=False)
            while i2 == i1 or i3 == i1:
                i2, i3 = rng.choice(N, 2, replace=False)
            ix = np.array([i1, i2, i3])
        else:
            ix = rng.choice(N, 3, replace=False)

        b = p_d[ix]
        center = b.mean(axis=0)
        z = b - center
        kz = _K @ z
        y = slots[assign_d[ix]]

        a = np.sum(z * y)
        b_val = np.sum(kz * y)
        th_star = np.arctan2(b_val, a)

        th = th_star if rng.random() < 0.65 else th_star * rng.uniform(0.2, 0.8)
        cand_b = center + np.cos(th) * z + np.sin(th) * kz
        if np.any(cand_b < 0.5) or np.any(cand_b > 99.5):
            continue

        props_d += 1
        cand = p_d.copy()
        cand[ix] = cand_b
        if signature2(cand, ddof=1) == REF_SIGNATURE:
            d_old = np.sum((b - y)**2)
            d_new = np.sum((cand_b - y)**2)
            if d_new < d_old:
                acc_d += 1
                p_d = cand

    t_d = time.time() - t0
    cost_d = np.sum((p_d[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind_d = linear_sum_assignment(cost_d)
    mse_d = float(np.mean(np.sum((p_d - slots[col_ind_d])**2, axis=1)))
    results["Method_D_Enhanced_Full_System"] = {
        "description": "Capacity matching + 3-point kernel + adaptive selection + stagnation recovery",
        "steps": steps,
        "time_seconds": round(t_d, 2),
        "proposals": props_d,
        "accepted_under_round2": acc_d,
        "acc_rate_round2": round(acc_d / max(props_d, 1), 5),
        "final_mse": round(mse_d, 3),
        "final_signature2": list(signature2(p_d, ddof=1)),
        "matches_round2_signature": (signature2(p_d, ddof=1) == REF_SIGNATURE),
        "is_legal_round2": is_legal(p_d, N, REF_SIGNATURE, ddof=1, bounds=BOUNDS_0_100)
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nComparison completed and saved to {output_path}:")
    for k, v in results.items():
        print(f"  {k:36s}: time={v['time_seconds']}s, acc={v.get('acc_rate_round2', 0)*100:.2f}%, "
              f"MSE={v.get('final_mse', 'N/A')}, legal={v['is_legal_round2']}")

    return results

if __name__ == "__main__":
    run_comparison()
