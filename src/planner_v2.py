"""Real Candidate-Driven Preflight Planning Pipeline (V2)."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from src.stats_audit import stats5, signature2, is_legal, BOUNDS_0_100, REF_SIGNATURE
from src.geometry_ground_truth import GroundTruthGeometry
from src.dino_densifier import densify_dino
from src.target_emblem_v2 import generate_moment_compatible_target, compute_v2_quotas
from moment_preserving_moves import _K

CANDIDATES = [142, 284, 426, 568, 852]

def run_mini_optimization(
    points: np.ndarray,
    slots: np.ndarray,
    steps: int = 5000,
    seed: int = 42
) -> tuple[np.ndarray, dict]:
    """Execute a mini-optimization run on a candidate N to test real convergence."""
    n = len(points)
    rng = np.random.default_rng(seed)

    # Initial assignment
    cost = np.sum((points[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind = linear_sum_assignment(cost)
    assign = col_ind.copy()

    t0 = time.time()
    acc_count = 0
    curr_e = float(np.mean(np.sum((points - slots[assign])**2, axis=1)))

    for step in range(1, steps + 1):
        if step % 400 == 0:
            cost = np.sum((points[:, None, :] - slots[None, :, :])**2, axis=2)
            _, col_ind = linear_sum_assignment(cost)
            assign = col_ind.copy()
            curr_e = float(np.mean(np.sum((points - slots[assign])**2, axis=1)))

        ix = rng.choice(n, 3, replace=False)
        b = points[ix]
        center = b.mean(axis=0)
        z = b - center
        kz = _K @ z
        y = slots[assign[ix]]

        a = np.sum(z * y)
        b_val = np.sum(kz * y)
        th_star = np.arctan2(b_val, a)

        th = th_star if rng.random() < 0.75 else float(rng.normal(0, 0.15))
        cand_b = center + np.cos(th) * z + np.sin(th) * kz
        if np.any(cand_b < 0.5) or np.any(cand_b > 99.5):
            continue

        cand_pts = points.copy()
        cand_pts[ix] = cand_b
        if signature2(cand_pts, ddof=1) == REF_SIGNATURE:
            d_old = np.sum((b - y)**2)
            d_new = np.sum((cand_b - y)**2)
            delta_e = (d_new - d_old) / n
            temp = max(0.001, 0.2 * (1.0 - step / steps)**2)
            if delta_e < 0 or rng.random() < np.exp(-delta_e / temp):
                points = cand_pts
                curr_e += delta_e
                acc_count += 1

    # Final assignment
    cost = np.sum((points[:, None, :] - slots[None, :, :])**2, axis=2)
    _, col_ind = linear_sum_assignment(cost)
    final_e = float(np.mean(np.sum((points - slots[col_ind])**2, axis=1)))
    elapsed = time.time() - t0

    return points, {
        "steps": steps,
        "elapsed_sec": round(elapsed, 2),
        "accepted_moves": acc_count,
        "acceptance_rate": round(acc_count / steps, 4),
        "final_mse": round(final_e, 4)
    }

def evaluate_candidate_v2(n: int, gt: GroundTruthGeometry, seed: int = 20260915) -> dict:
    t_start = time.time()

    # Step 1: Generate dense dinosaur seed
    dino_ok = False
    dino_error = None
    try:
        p_dino, dino_diag = densify_dino(n, seed=seed)
        dino_ok = dino_diag.get("is_legal", False)
    except Exception as e:
        dino_error = str(e)
        p_dino = None

    if not dino_ok:
        return {
            "n": n,
            "status": "SEED_INVALID",
            "passed_all": False,
            "reason": dino_error or "Dinosaur seed failed legal gate",
            "eval_time_sec": round(time.time() - t_start, 2)
        }

    # Step 2: Prepare moment-compatible target
    target_ok = False
    target_error = None
    try:
        Q, _, target_diag = generate_moment_compatible_target(n, gt=gt, seed=seed, max_opt_iter=1500)
        target_ok = True
    except Exception as e:
        target_error = str(e)
        Q = None

    if not target_ok:
        return {
            "n": n,
            "status": "TARGET_PREPARATION_FAILED",
            "passed_all": False,
            "reason": target_error or "Target preparation failed",
            "eval_time_sec": round(time.time() - t_start, 2)
        }

    # Step 3: Run real mini-optimization with sufficient budget to test convergence
    p_end, opt_summary = run_mini_optimization(p_dino, Q, steps=12000, seed=seed)

    # Step 4: Evaluate geometry on end state
    geom_eval = gt.evaluate(p_end)
    final_geom_pass = geom_eval["final_geometry_pass"]
    sig_end = signature2(p_end, ddof=1)
    inv_pass = (sig_end == REF_SIGNATURE)

    passed_all = bool(final_geom_pass and inv_pass)
    status = "QUALIFIED" if passed_all else "GEOMETRY_FAILED"

    return {
        "n": n,
        "status": status,
        "passed_all": passed_all,
        "quotas": compute_v2_quotas(n),
        "target_lb_total": target_diag.get("LB_total"),
        "mini_opt_summary": opt_summary,
        "geometry_evaluation": geom_eval,
        "reason_codes": geom_eval["reason_codes"] if not passed_all else [],
        "eval_time_sec": round(time.time() - t_start, 2)
    }

def run_preflight_planning(
    candidates: list[int] | None = None,
    seed: int = 20260915,
    gt: GroundTruthGeometry | None = None
) -> dict:
    if candidates is None:
        candidates = CANDIDATES
    if gt is None:
        gt = GroundTruthGeometry()

    evaluations = []
    for n in candidates:
        print(f"Testing planning candidate N={n}...")
        ev = evaluate_candidate_v2(n, gt=gt, seed=seed)
        evaluations.append(ev)
        print(f"  Candidate N={n}: status={ev['status']}, passed_all={ev['passed_all']}")

    qualified = [e for e in evaluations if e["passed_all"]]

    if qualified:
        chosen_n = min(q["n"] for q in qualified)
        status = "QUALIFIED"
        planning_pass = True
        rationale = f"N*={chosen_n} is the minimal candidate passing real mini-evolution and full ground truth geometry verification."
    else:
        chosen_n = None
        status = "NO_QUALIFIED_CANDIDATE"
        planning_pass = False
        rationale = "No candidate in the tested set passed all geometry and moment criteria."

    return {
        "planning_version": "2.1.0-repaired-v2",
        "reference_signature": list(REF_SIGNATURE),
        "status": status,
        "planning_pass": planning_pass,
        "candidates_evaluated": evaluations,
        "chosen_n_star": chosen_n,
        "rationale": rationale,
        "quota_allocation": compute_v2_quotas(chosen_n) if chosen_n else None
    }

def main():
    parser = argparse.ArgumentParser(description="Preflight Planning V2.")
    parser.add_argument("--candidates", type=int, nargs="+", default=CANDIDATES)
    parser.add_argument("--output", type=Path, default=Path("analysis/repair_v2/planning_v2.json"))
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = run_preflight_planning(candidates=args.candidates, seed=args.seed)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nPlanning V2 completed. Written to {args.output}")
    print(f"  Status: {report['status']}")
    print(f"  Chosen N*: {report['chosen_n_star']}")
    print(f"  Planning Pass: {report['planning_pass']}")

    if not report["planning_pass"]:
        exit(1)

if __name__ == "__main__":
    main()
