"""Reviewer contract tests for SSDG_FLASH_01. No optimizer, image assets or network.

Run from the repository root:
  python -m unittest discover -s review_tests -p test_flash01_audit_contract.py -v

GeometryProbe intentionally isolates input/media validation. Passing this suite
DOES NOT certify emblem geometry or full-trajectory replay. Do not weaken tests.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src.independent_verifier import audit_snapshot_invariants, audit_trajectory_and_run


class GeometryProbe:
    """Test-only geometry collaborator, never a production geometry validator."""
    def __init__(self, passed: bool = True):
        self.passed = passed

    def evaluate(self, points):
        p = np.asarray(points)
        if p.ndim != 2 or p.shape[1] != 2 or not len(p) or not np.isfinite(p).all():
            raise AssertionError("Malformed coordinates reached geometry evaluation")
        return {
            "final_geometry_pass": self.passed,
            "reason_codes": [] if self.passed else ["GEOMETRY_PROBE_FAILED"],
            "layer_evaluations": {},
        }


def legal_frame(n: int = 32) -> pd.DataFrame:
    """Synthetic positive fixture with the required SAMPLE moments; not a dino."""
    mu = np.array([54.26, 47.83])
    sx, sy, corr = 16.77, 26.94, -0.06
    cov = np.array([[sx * sx, corr * sx * sy], [corr * sx * sy, sy * sy]])
    theta = 2 * np.pi * np.arange(n) / n
    z = np.column_stack((np.cos(theta), np.sin(theta))) * np.sqrt(2 * (n - 1) / n)
    p = mu + z @ np.linalg.cholesky(cov).T
    return pd.DataFrame({"point_id": np.arange(1000, 1000 + n), "x": p[:, 0], "y": p[:, 1]})


def write_gif(path: Path) -> None:
    """Two decodable frames, not proof that this GIF depicts the data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [Image.new("L", (8, 8), value) for value in (0, 255)]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=40, loop=0)


class TestFlash01AuditContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.df = legal_frame()
        self.n = len(self.df)
        self.ids = self.df["point_id"].to_numpy()

    def snapshot(self, df=None, expected_n=None):
        path = self.root / "single.csv"
        (self.df if df is None else df).to_csv(path, index=False)
        return audit_snapshot_invariants(path, self.n if expected_n is None else expected_n, self.ids)

    def make_run(self):
        run = self.root / "seed_101"
        (run / "snapshots").mkdir(parents=True)
        for step in (0, 2):
            self.df.to_csv(run / "snapshots" / f"frame_{step:06d}.csv", index=False)
        (run / "metrics.json").write_text(json.dumps({
            "n_points": self.n, "total_steps": 2, "random_seed": 101
        }), encoding="utf-8")
        write_gif(run / "evolution_pure_scatter.gif")
        return run

    def audit_run(self, run, expected_n=None, geometry_pass=True):
        return audit_trajectory_and_run(run, expected_n=expected_n, gt=GeometryProbe(geometry_pass))

    def assert_reason(self, result, reason):
        self.assertIn(reason, result["reason_codes"])
        json.dumps(result, allow_nan=False)

    def test_01_valid_snapshot_is_positive_control(self):
        r = self.snapshot()
        self.assertTrue(r["invariants_pass"])
        self.assertEqual(r["signature2"], ["54.26", "47.83", "16.77", "26.94", "-0.06"])
        json.dumps(r, allow_nan=False)

    def test_02_missing_id_column_is_not_synthesized(self):
        r = self.snapshot(self.df.drop(columns="point_id"))
        self.assertFalse(r["invariants_pass"])
        self.assert_reason(r, "SNAPSHOT_COLUMNS_MISSING")

    def test_03_fractional_ids_are_not_truncated(self):
        bad = self.df.copy()
        bad["point_id"] = bad["point_id"].astype(float) + 0.25
        r = self.snapshot(bad)
        self.assertFalse(r["invariants_pass"])
        self.assert_reason(r, "POINT_ID_INVALID")

    def test_04_duplicate_and_reordered_ids_fail(self):
        duplicate = self.df.copy()
        duplicate.loc[1, "point_id"] = duplicate.loc[0, "point_id"]
        reordered = self.df.iloc[[1, 0] + list(range(2, self.n))].copy()
        for df, code in ((duplicate, "POINT_ID_DUPLICATE"), (reordered, "POINT_ID_ORDER_MISMATCH")):
            with self.subTest(reason=code):
                r = self.snapshot(df)
                self.assertFalse(r["invariants_pass"])
                self.assert_reason(r, code)

    def test_05_wrong_expected_n_fails_snapshot(self):
        r = self.snapshot(expected_n=self.n + 1)
        self.assertFalse(r["invariants_pass"])
        self.assert_reason(r, "POINT_COUNT_MISMATCH_EXPECTED")

    def test_06_empty_and_malformed_csv_fail_without_crash(self):
        for text, code in (("", "SNAPSHOT_EMPTY"), ("point_id,x,y\n", "SNAPSHOT_EMPTY"),
                           ("point_id,x\n1000,54.26\n", "SNAPSHOT_COLUMNS_MISSING")):
            with self.subTest(text=text):
                path = self.root / "bad.csv"
                path.write_text(text, encoding="utf-8")
                r = audit_snapshot_invariants(path, self.n, self.ids)
                self.assertFalse(r["invariants_pass"])
                self.assert_reason(r, code)

    def test_07_nan_and_inf_are_rejected(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value):
                bad = self.df.copy()
                bad.loc[0, "x"] = value
                r = self.snapshot(bad)
                self.assertFalse(r["invariants_pass"])
                self.assert_reason(r, "COORDINATES_NONFINITE")

    def test_08_bounds_and_stat_signature_are_independent_checks(self):
        oob = self.df.copy()
        oob.loc[0, "x"] = 100.0
        shifted = self.df.copy()
        shifted["x"] += 0.02
        for df, code in ((oob, "COORDINATES_OUT_OF_BOUNDS"), (shifted, "STAT_SIGNATURE_MISMATCH")):
            with self.subTest(reason=code):
                r = self.snapshot(df)
                self.assertFalse(r["invariants_pass"])
                self.assert_reason(r, code)

    def test_09_valid_files_are_not_full_trajectory_proof(self):
        r = self.audit_run(self.make_run(), expected_n=self.n)
        self.assertTrue(r["input_contract_pass"])
        self.assertTrue(r["snapshot_invariants_pass"])
        self.assertTrue(r["media_valid"])
        self.assertTrue(r["final_geometry_pass"])
        self.assertFalse(r["trajectory_invariants_pass"])
        self.assertFalse(r["task_pass"])
        self.assert_reason(r, "TRAJECTORY_NOT_AUDITED")

    def test_10_expected_n_mismatch_is_a_hard_failure(self):
        r = self.audit_run(self.make_run(), expected_n=self.n + 1)
        self.assertFalse(r["input_contract_pass"])
        self.assertFalse(r["snapshot_invariants_pass"])
        self.assertFalse(r["task_pass"])
        self.assert_reason(r, "POINT_COUNT_MISMATCH_EXPECTED")

    def test_11_frame0_is_required(self):
        run = self.make_run()
        (run / "snapshots/frame_000000.csv").rename(run / "snapshots/frame_000001.csv")
        r = self.audit_run(run)
        self.assertFalse(r["input_contract_pass"])
        self.assert_reason(r, "FRAME0_MISSING")

    def test_12_true_terminal_frame_is_required(self):
        run = self.make_run()
        (run / "snapshots/frame_000002.csv").rename(run / "snapshots/frame_000001.csv")
        r = self.audit_run(run)
        self.assertFalse(r["input_contract_pass"])
        self.assert_reason(r, "FINAL_FRAME_MISSING")

    def test_13_metrics_are_parsed_not_just_found(self):
        run = self.make_run()
        for text in ("{", "{}", json.dumps({"n_points": 0, "total_steps": 2})):
            with self.subTest(text=text):
                (run / "metrics.json").write_text(text, encoding="utf-8")
                r = self.audit_run(run)
                self.assertFalse(r["input_contract_pass"])
                self.assert_reason(r, "METRICS_INVALID")

    def test_14_metrics_n_controls_audit_when_argument_is_omitted(self):
        run = self.make_run()
        (run / "metrics.json").write_text(json.dumps({"n_points": self.n + 1, "total_steps": 2}), encoding="utf-8")
        r = self.audit_run(run)
        self.assertFalse(r["input_contract_pass"])
        self.assert_reason(r, "POINT_COUNT_MISMATCH_EXPECTED")

    def test_15_empty_corrupt_and_still_gif_are_rejected(self):
        run = self.make_run()
        path = run / "evolution_pure_scatter.gif"
        for content in (b"", b"not a gif"):
            with self.subTest(content=content):
                path.write_bytes(content)
                r = self.audit_run(run)
                self.assertFalse(r["media_valid"])
                self.assert_reason(r, "ANIMATION_INVALID")
        Image.new("L", (8, 8), 0).save(path)
        r = self.audit_run(run)
        self.assertFalse(r["media_valid"])
        self.assert_reason(r, "ANIMATION_INVALID")

    def test_16_sibling_animation_does_not_satisfy_local_media(self):
        run = self.make_run()
        (run / "evolution_pure_scatter.gif").unlink()
        write_gif(self.root / "seed_42/evolution_pure_scatter.gif")
        r = self.audit_run(run)
        self.assertFalse(r["media_valid"])
        self.assert_reason(r, "ANIMATION_MISSING")

    def test_17_empty_run_fails(self):
        r = self.audit_run(self.root / "missing")
        self.assertFalse(r["input_contract_pass"])
        self.assertFalse(r["task_pass"])
        self.assertTrue(r["reason_codes"])
        json.dumps(r, allow_nan=False)

    def test_18_geometry_failure_is_not_overwritten(self):
        r = self.audit_run(self.make_run(), geometry_pass=False)
        self.assertTrue(r["snapshot_invariants_pass"])
        self.assertFalse(r["final_geometry_pass"])
        self.assertFalse(r["task_pass"])
        self.assert_reason(r, "GEOMETRY_PROBE_FAILED")


if __name__ == "__main__":
    unittest.main()
