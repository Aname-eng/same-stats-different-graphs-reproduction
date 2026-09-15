"""Independent Verifier & Multi-Dimensional Auditor for SSDG.

Task: SSDG_FLASH_01_AUDIT_CONTRACT_20260915
Strictly conforms to interface contracts and audit specifications.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from PIL import Image

from src.stats_audit import (
    stats5, signature2, REF_SIGNATURE
)
from src.geometry_ground_truth import GroundTruthGeometry

def get_git_commit_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def audit_snapshot_invariants(csv_path: Path | str, expected_n: int | None, ref_ids: np.ndarray | None = None) -> dict[str, Any]:
    """Audit mathematical invariants of a single snapshot CSV.

    Checks:
      1. File exists, readable, not empty / not header-only.
      2. Required columns: point_id, x, y.
      3. Point count == expected_n (if expected_n provided).
      4. Point IDs are finite integer values.
      5. Point IDs are unique and strictly match ref_ids order.
      6. Coordinates are finite numbers.
      7. Coordinates are strictly in bounds (0 < x, y < 100).
      8. Sample stats match REF_SIGNATURE via signature2(pts, ddof=1).
    """
    p = Path(csv_path)
    reasons: list[str] = []

    if not p.exists() or not p.is_file():
        return {
            "file": str(p),
            "point_count": 0,
            "expected_n": expected_n,
            "count_ok": False,
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_UNREADABLE"]
        }

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return {
            "file": str(p),
            "point_count": 0,
            "expected_n": expected_n,
            "count_ok": False,
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_UNREADABLE"]
        }

    if not content.strip():
        return {
            "file": str(p),
            "point_count": 0,
            "expected_n": expected_n,
            "count_ok": False,
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_EMPTY"]
        }

    try:
        df = pd.read_csv(p)
    except Exception:
        return {
            "file": str(p),
            "point_count": 0,
            "expected_n": expected_n,
            "count_ok": False,
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_UNREADABLE"]
        }

    if len(df) == 0:
        return {
            "file": str(p),
            "point_count": 0,
            "expected_n": expected_n,
            "count_ok": False,
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_EMPTY"]
        }

    req_cols = {"point_id", "x", "y"}
    if not req_cols.issubset(df.columns):
        return {
            "file": str(p),
            "point_count": len(df),
            "expected_n": expected_n,
            "count_ok": bool(len(df) == expected_n if expected_n is not None else True),
            "ids_identical": False,
            "ids_unique": False,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": ["SNAPSHOT_COLUMNS_MISSING"]
        }

    n_pts = len(df)
    count_ok = bool((expected_n is None) or (n_pts == expected_n))
    if not count_ok:
        reasons.append("POINT_COUNT_MISMATCH_EXPECTED")

    # Point IDs validation
    raw_ids = df["point_id"].to_numpy()
    id_valid = True
    parsed_ids: list[int] = []
    for val in raw_ids:
        if isinstance(val, (bool, np.bool_)):
            id_valid = False
            break
        elif isinstance(val, (int, np.integer)):
            parsed_ids.append(int(val))
        elif isinstance(val, (float, np.floating)):
            if np.isfinite(val) and float(val).is_integer():
                parsed_ids.append(int(val))
            else:
                id_valid = False
                break
        elif isinstance(val, str):
            try:
                f_val = float(val)
                if np.isfinite(f_val) and f_val.is_integer():
                    parsed_ids.append(int(f_val))
                else:
                    id_valid = False
                    break
            except ValueError:
                id_valid = False
                break
        else:
            id_valid = False
            break

    if not id_valid:
        reasons.append("POINT_ID_INVALID")
        ids_unique = False
        ids_identical = False
    else:
        ids_arr = np.array(parsed_ids, dtype=np.int64)
        ids_unique = bool(len(np.unique(ids_arr)) == len(ids_arr))
        if not ids_unique:
            reasons.append("POINT_ID_DUPLICATE")

        if ref_ids is not None:
            ref_arr = np.asarray(ref_ids)
            if len(ids_arr) == len(ref_arr) and np.array_equal(ids_arr, ref_arr):
                ids_identical = True
            else:
                ids_identical = False
                reasons.append("POINT_ID_ORDER_MISMATCH")
        else:
            ids_identical = True

    # Coordinates finite check
    try:
        x_raw = df["x"].to_numpy(dtype=float)
        y_raw = df["y"].to_numpy(dtype=float)
        coords_finite = bool(np.isfinite(x_raw).all() and np.isfinite(y_raw).all())
    except Exception:
        coords_finite = False

    if not coords_finite:
        reasons.append("COORDINATES_NONFINITE")
        return {
            "file": str(p),
            "point_count": n_pts,
            "expected_n": expected_n,
            "count_ok": count_ok,
            "ids_identical": ids_identical,
            "ids_unique": ids_unique,
            "in_bounds_0_100": False,
            "bounds": {"x_min": None, "x_max": None, "y_min": None, "y_max": None},
            "stats5_ddof1": None,
            "signature2": None,
            "matches_ref_signature": False,
            "invariants_pass": False,
            "reason_codes": reasons
        }

    x_min, x_max = float(x_raw.min()), float(x_raw.max())
    y_min, y_max = float(y_raw.min()), float(y_raw.max())
    in_bounds = bool(0.0 < x_min and x_max < 100.0 and 0.0 < y_min and y_max < 100.0)
    if not in_bounds:
        reasons.append("COORDINATES_OUT_OF_BOUNDS")

    pts = np.column_stack((x_raw, y_raw))
    s5_ddof1 = stats5(pts, ddof=1)
    sig_ddof1 = list(signature2(pts, ddof=1))
    matches_ref = bool(sig_ddof1 == list(REF_SIGNATURE))
    if not matches_ref:
        reasons.append("STAT_SIGNATURE_MISMATCH")

    invariants_pass = bool(len(reasons) == 0)

    return {
        "file": str(p),
        "point_count": n_pts,
        "expected_n": expected_n,
        "count_ok": count_ok,
        "ids_identical": ids_identical,
        "ids_unique": ids_unique,
        "in_bounds_0_100": in_bounds,
        "bounds": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
        "stats5_ddof1": s5_ddof1.tolist(),
        "signature2": sig_ddof1,
        "matches_ref_signature": matches_ref,
        "invariants_pass": invariants_pass,
        "reason_codes": reasons
    }

def audit_trajectory_and_run(run_dir: Path | str, expected_n: int | None = None, gt: Any = None) -> dict[str, Any]:
    """Audit run directory against SSDG input contract, invariants, media, and geometry."""
    run_dir = Path(run_dir)
    reason_codes: list[str] = []

    if not run_dir.exists() or not run_dir.is_dir():
        return {
            "run_directory": str(run_dir),
            "git_commit_sha": get_git_commit_sha(),
            "n_points": expected_n if expected_n is not None else 0,
            "total_frames": 0,
            "input_contract_pass": False,
            "snapshot_invariants_pass": False,
            "media_valid": False,
            "invariants_pass": False,
            "frame0_invariants_pass": False,
            "frame0_geometry_pass": False,
            "trajectory_invariants_pass": False,
            "trajectory_audit_status": "NOT_AUDITED",
            "final_geometry_pass": False,
            "deliverables_complete": False,
            "task_pass": False,
            "reason_codes": ["RUN_DIRECTORY_MISSING", "TRAJECTORY_NOT_AUDITED"]
        }

    # 1. Metrics validation
    metrics_file = run_dir / "metrics.json"
    metrics_valid = False
    metrics_data: dict[str, Any] = {}
    if metrics_file.exists() and metrics_file.is_file():
        try:
            with open(metrics_file, "r", encoding="utf-8") as mf:
                metrics_data = json.load(mf)
            if isinstance(metrics_data, dict):
                n_pts_val = metrics_data.get("n_points")
                steps_val = metrics_data.get("total_steps")
                if (
                    isinstance(n_pts_val, int) and not isinstance(n_pts_val, bool) and n_pts_val >= 3
                    and isinstance(steps_val, int) and not isinstance(steps_val, bool) and steps_val > 0
                ):
                    metrics_valid = True
        except Exception:
            metrics_valid = False

    if not metrics_valid:
        reason_codes.append("METRICS_INVALID")

    # 2. Expected N determination
    if expected_n is not None:
        effective_n = expected_n
        if metrics_valid and metrics_data.get("n_points") != expected_n:
            if "POINT_COUNT_MISMATCH_EXPECTED" not in reason_codes:
                reason_codes.append("POINT_COUNT_MISMATCH_EXPECTED")
    else:
        if metrics_valid:
            effective_n = metrics_data.get("n_points")
        else:
            effective_n = None

    total_steps = metrics_data.get("total_steps") if metrics_valid else None

    # 3. Snapshot files check
    snaps_dir = run_dir / "snapshots"
    frame0_path = snaps_dir / "frame_000000.csv"
    if not frame0_path.exists():
        reason_codes.append("FRAME0_MISSING")

    final_frame_path = snaps_dir / f"frame_{total_steps:06d}.csv" if total_steps is not None else None
    if final_frame_path is None or not final_frame_path.exists():
        reason_codes.append("FINAL_FRAME_MISSING")

    raw_csvs = sorted(snaps_dir.glob("frame_*.csv")) if snaps_dir.exists() else []
    valid_csvs = []
    for f in raw_csvs:
        stem = f.stem
        if stem.startswith("frame_"):
            try:
                step_num = int(stem[6:])
                if total_steps is not None and step_num > total_steps:
                    continue
                valid_csvs.append((step_num, f))
            except ValueError:
                pass
    valid_csvs.sort(key=lambda x: x[0])
    csv_files = [f for _, f in valid_csvs]

    # Extract ref_ids from frame 0
    ref_ids = None
    if frame0_path.exists():
        try:
            df0 = pd.read_csv(frame0_path)
            if "point_id" in df0.columns:
                raw_ids0 = df0["point_id"].to_numpy()
                parsed0 = []
                for v in raw_ids0:
                    if isinstance(v, (bool, np.bool_)):
                        break
                    elif isinstance(v, (int, np.integer)):
                        parsed0.append(int(v))
                    elif isinstance(v, (float, np.floating)) and float(v).is_integer():
                        parsed0.append(int(v))
                    elif isinstance(v, str):
                        try:
                            fv = float(v)
                            if fv.is_integer():
                                parsed0.append(int(fv))
                            else:
                                break
                        except ValueError:
                            break
                    else:
                        break
                if len(parsed0) == len(raw_ids0):
                    ref_ids = np.array(parsed0, dtype=np.int64)
        except Exception:
            ref_ids = None

    # Audit all snapshots
    frame_invariants = []
    for f in csv_files:
        fa = audit_snapshot_invariants(f, effective_n, ref_ids)
        frame_invariants.append(fa)
        for rc in fa.get("reason_codes", []):
            if rc not in reason_codes:
                reason_codes.append(rc)

    if len(frame_invariants) > 0:
        all_frames_ok = all(fi.get("invariants_pass", False) for fi in frame_invariants)
        snapshot_invariants_pass = bool(all_frames_ok and ("POINT_COUNT_MISMATCH_EXPECTED" not in reason_codes))
    else:
        snapshot_invariants_pass = False

    # 4. Media / GIF validation
    gif_path = run_dir / "evolution_pure_scatter.gif"
    media_valid = False
    if not gif_path.exists():
        reason_codes.append("ANIMATION_MISSING")
    else:
        try:
            if gif_path.stat().st_size == 0:
                reason_codes.append("ANIMATION_INVALID")
            else:
                with Image.open(gif_path) as im:
                    if getattr(im, "format", "") != "GIF":
                        reason_codes.append("ANIMATION_INVALID")
                    else:
                        n_frames = getattr(im, "n_frames", 1)
                        if n_frames < 2:
                            reason_codes.append("ANIMATION_INVALID")
                        else:
                            can_decode = True
                            for frame_idx in range(n_frames):
                                im.seek(frame_idx)
                                im.load()
                            media_valid = True
        except Exception:
            reason_codes.append("ANIMATION_INVALID")

    # 5. Final geometry evaluation
    final_geom_pass = False
    geom_details: dict[str, Any] = {}
    if final_frame_path is not None and final_frame_path.exists():
        try:
            df_final = pd.read_csv(final_frame_path)
            if "x" in df_final.columns and "y" in df_final.columns:
                pts_final = df_final[["x", "y"]].to_numpy(dtype=float)
                if (
                    pts_final.ndim == 2 and pts_final.shape[1] == 2
                    and len(pts_final) > 0 and np.isfinite(pts_final).all()
                ):
                    if gt is None:
                        gt = GroundTruthGeometry()
                    geom_eval = gt.evaluate(pts_final)
                    final_geom_pass = bool(geom_eval.get("final_geometry_pass", False))
                    geom_details = geom_eval.get("layer_evaluations", {})
                    if not final_geom_pass:
                        for rc in geom_eval.get("reason_codes", []):
                            if rc not in reason_codes:
                                reason_codes.append(rc)
        except Exception:
            pass

    # Frame 0 geometry evaluation for diagnostic context
    frame0_geom_pass = False
    if frame0_path.exists():
        try:
            df0_pts = pd.read_csv(frame0_path)
            if "x" in df0_pts.columns and "y" in df0_pts.columns:
                p0 = df0_pts[["x", "y"]].to_numpy(dtype=float)
                if p0.ndim == 2 and p0.shape[1] == 2 and len(p0) > 0 and np.isfinite(p0).all():
                    if gt is None:
                        gt = GroundTruthGeometry()
                    ev0 = gt.evaluate(p0)
                    frame0_geom_pass = bool(ev0.get("final_geometry_pass", False))
        except Exception:
            pass

    # 6. Contract and Status flags
    input_contract_pass = bool(
        metrics_valid
        and ("POINT_COUNT_MISMATCH_EXPECTED" not in reason_codes)
        and ("FRAME0_MISSING" not in reason_codes)
        and ("FINAL_FRAME_MISSING" not in reason_codes)
        and snapshot_invariants_pass
    )

    trajectory_invariants_pass = False
    trajectory_audit_status = "NOT_AUDITED"
    if "TRAJECTORY_NOT_AUDITED" not in reason_codes:
        reason_codes.append("TRAJECTORY_NOT_AUDITED")

    deliverables_complete = False
    task_pass = False

    return {
        "run_directory": str(run_dir),
        "git_commit_sha": get_git_commit_sha(),
        "n_points": effective_n if effective_n is not None else 0,
        "total_frames": len(csv_files),
        "input_contract_pass": input_contract_pass,
        "snapshot_invariants_pass": snapshot_invariants_pass,
        "media_valid": media_valid,
        "invariants_pass": frame_invariants[-1]["invariants_pass"] if frame_invariants else False,
        "frame0_invariants_pass": frame_invariants[0]["invariants_pass"] if frame_invariants else False,
        "frame0_geometry_pass": frame0_geom_pass,
        "trajectory_invariants_pass": trajectory_invariants_pass,
        "trajectory_audit_status": trajectory_audit_status,
        "final_geometry_pass": final_geom_pass,
        "deliverables_complete": deliverables_complete,
        "task_pass": task_pass,
        "reason_codes": reason_codes,
        "final_geometry_details": geom_details,
        "initial_frame": frame_invariants[0] if frame_invariants else None,
        "final_frame": frame_invariants[-1] if frame_invariants else None
    }

def main():
    parser = argparse.ArgumentParser(description="Audit V2 runs independently.")
    parser.add_argument("--run-dirs", nargs="+", default=[
        "output/repair_v2/seed_42",
        "output/repair_v2/seed_101",
        "output/repair_v2/seed_20260915"
    ])
    parser.add_argument("--output", type=Path, default=Path("analysis/repair_v2/independent_audit_report.json"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    gt = GroundTruthGeometry()

    results = {}
    all_task_passed = True
    for rdir in args.run_dirs:
        p = Path(rdir)
        print(f"Auditing run: {p}...")
        res = audit_trajectory_and_run(p, gt=gt)
        results[str(p)] = res
        if not res.get("task_pass", False):
            all_task_passed = False

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Independent audit report saved to {args.output}")
    if not all_task_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
