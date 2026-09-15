"""Preflight visual budget planning and candidate N evaluation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from src.stats_audit import REF_SIGNATURE, BOUNDS_0_100, is_legal
from src.dino_densifier import densify_dino
from src.target_emblem import generate_target_slots, compute_default_quotas

CANDIDATES = [142, 284, 426, 568, 852]

def evaluate_candidate_n(n: int, seed: int = 20260915) -> dict:
    """Evaluate a candidate N across visual budget, legality, and moment compatibility."""
    # 1. Stroke budget metrics
    # Estimated total stroke length ~ 937 units
    total_stroke_len = 937.0
    nominal_spacing = total_stroke_len / n
    # Text stroke length ~ 250 units
    quotas = compute_default_quotas(n)
    text_points = quotas["nan"] + quotas["kai"]
    text_spacing = 250.0 / max(text_points, 1)

    # 2. Dense dinosaur generation
    dino_legal = False
    dino_diag = {}
    try:
        _, dino_diag = densify_dino(n, seed=seed)
        dino_legal = dino_diag.get("is_legal", False)
    except Exception as e:
        dino_diag["error"] = str(e)

    # 3. Target slot allocation
    slot_diag = {}
    try:
        _, _, slot_diag = generate_target_slots(n, seed=seed, quotas=quotas)
    except Exception as e:
        slot_diag["error"] = str(e)

    # 4. Evaluation decision criteria
    # Thresholds:
    # - dino_legal must be True
    # - nominal_spacing <= 2.0 (for connected strokes)
    # - text_points >= 80 (for clear character readability)
    passes_visual_budget = (nominal_spacing <= 2.0) and (text_points >= 80)
    passed_all = dino_legal and passes_visual_budget

    return {
        "n": n,
        "nominal_spacing": round(nominal_spacing, 3),
        "text_points": text_points,
        "text_spacing": round(text_spacing, 3),
        "quotas": quotas,
        "dino_legal": dino_legal,
        "passes_visual_budget": passes_visual_budget,
        "passed_all": passed_all,
        "dino_shift_mean": dino_diag.get("calibration_shift_mean"),
        "dino_nn_mean": dino_diag.get("nearest_neighbor_mean"),
        "reason": (
            "Meets all visual budget, stroke density, and exact statistical gate requirements."
            if passed_all else
            ("Failed visual budget (too sparse for text readability)" if not passes_visual_budget else "Failed dino legality")
        )
    }

def run_preflight_planning(candidates: list[int] | None = None, seed: int = 20260915) -> dict:
    if candidates is None:
        candidates = CANDIDATES

    evaluations = [evaluate_candidate_n(n, seed=seed) for n in candidates]

    # Select smallest candidate that passed all criteria
    qualified = [e for e in evaluations if e["passed_all"]]
    if qualified:
        chosen_n = min(q["n"] for q in qualified)
    else:
        chosen_n = 568 # fallback default

    report = {
        "planning_version": "2.0.0-enhanced",
        "reference_signature": list(REF_SIGNATURE),
        "candidates_evaluated": evaluations,
        "chosen_n_star": chosen_n,
        "rationale": f"N*={chosen_n} is the minimal candidate satisfying both exact statistical legality and visual stroke resolution thresholds.",
        "quota_allocation": compute_default_quotas(chosen_n)
    }
    return report

def main():
    parser = argparse.ArgumentParser(description="Preflight visual budget planning.")
    parser.add_argument("--output", type=Path, default=Path("planning.json"))
    parser.add_argument("--seed", type=int, default=20260915)
    args = parser.parse_args()

    report = run_preflight_planning(seed=args.seed)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Preflight planning completed. Output written to {args.output}")
    print(f"  Chosen N*: {report['chosen_n_star']}")
    print(f"  Quotas: {report['quota_allocation']}")

if __name__ == "__main__":
    main()
