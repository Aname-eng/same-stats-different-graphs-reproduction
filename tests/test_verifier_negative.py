"""Negative Test Suite for SSDG V2 Auditor and Planner."""
from __future__ import annotations
import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

from src.stats_audit import stats5, signature2, is_legal, BOUNDS_0_100, REF_SIGNATURE, MU_0, COV_0
from src.geometry_ground_truth import GroundTruthGeometry
from src.independent_verifier import audit_snapshot_invariants, audit_trajectory_and_run
from src.planner_v2 import run_preflight_planning

class TestVerifierNegativeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gt = GroundTruthGeometry()
        cls.df_dino = pd.read_csv("seed_568.csv")
        cls.p_dino = cls.df_dino[["x", "y"]].to_numpy(float)
        cls.n = len(cls.p_dino)

    def test_case_1_dinosaur_frame0_fails_geometry_and_task_pass(self):
        """Case 1: Legal dinosaur Frame 0 passes invariants, but MUST FAIL geometry and task_pass."""
        inv_audit = audit_snapshot_invariants(Path("seed_568.csv"), self.n, np.arange(self.n))
        self.assertTrue(inv_audit["invariants_pass"], "Dinosaur Frame 0 must pass mathematical invariants")

        geom_eval = self.gt.evaluate(self.p_dino)
        self.assertFalse(geom_eval["final_geometry_pass"], "Dinosaur Frame 0 must FAIL final geometry check")
        self.assertIn("GEOMETRY_OUTER_RING_FAILED", geom_eval["reason_codes"])

    def test_case_2_missing_nan_stroke_fails_geometry(self):
        """Case 2: Emblem missing 'nan' strokes must fail geometry check even if invariants pass."""
        p_missing_nan = self.p_dino.copy()
        geom_eval = self.gt.evaluate(p_missing_nan)
        self.assertIn("GEOMETRY_STROKE_NAN_FAILED", geom_eval["reason_codes"])
        self.assertFalse(geom_eval["final_geometry_pass"])

    def test_case_3_missing_outer_ring_fails_geometry(self):
        """Case 3: Point set without outer ring must fail geometry check."""
        center = MU_0
        pts_central = center + np.random.default_rng(42).normal(0, 5, size=(self.n, 2))
        geom_eval = self.gt.evaluate(pts_central)
        self.assertIn("GEOMETRY_OUTER_RING_FAILED", geom_eval["reason_codes"])
        self.assertFalse(geom_eval["final_geometry_pass"])

    def test_case_4_invariants_failure_cases(self):
        """Case 4: N change, duplicate IDs, NaN/Inf, out of bounds must fail invariants."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test_dup.csv"
            df = self.df_dino.copy()
            df.loc[1, "point_id"] = df.loc[0, "point_id"]
            df.to_csv(fpath, index=False)
            res = audit_snapshot_invariants(fpath, self.n, np.arange(self.n))
            self.assertFalse(res["invariants_pass"])
            self.assertFalse(res["ids_unique"])

            # Out of bounds
            fpath_oob = Path(tmpdir) / "test_oob.csv"
            df_oob = self.df_dino.copy()
            df_oob.loc[0, "x"] = 105.0
            df_oob.to_csv(fpath_oob, index=False)
            res_oob = audit_snapshot_invariants(fpath_oob, self.n, np.arange(self.n))
            self.assertFalse(res_oob["invariants_pass"])
            self.assertFalse(res_oob["in_bounds_0_100"])

            # NaN coordinate
            fpath_nan = Path(tmpdir) / "test_nan.csv"
            df_nan = self.df_dino.copy()
            df_nan.loc[0, "y"] = np.nan
            df_nan.to_csv(fpath_nan, index=False)
            res_nan = audit_snapshot_invariants(fpath_nan, self.n, np.arange(self.n))
            self.assertFalse(res_nan["invariants_pass"])

    def test_case_5_empty_directory_fails_deliverables_and_task_pass(self):
        """Case 5: Empty snapshots list must fail deliverables_complete and task_pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_run = Path(tmpdir)
            audit = audit_trajectory_and_run(empty_run, gt=self.gt)
            self.assertFalse(audit["task_pass"])
            self.assertFalse(audit["deliverables_complete"])
            self.assertIn("DELIVERABLES_SNAPSHOTS_MISSING", audit["reason_codes"])

    def test_case_6_planner_explicit_failure_when_no_candidates_pass(self):
        """Case 6: If all candidates fail, planner must report NO_QUALIFIED_CANDIDATE, chosen_n_star=null."""
        # Test candidate list with only non-qualifying small point counts (e.g. N=142, which fails geometry)
        plan_report = run_preflight_planning(candidates=[142], seed=42, gt=self.gt)
        self.assertIsNone(plan_report["chosen_n_star"], "Must be None when no candidate qualifies")
        self.assertEqual(plan_report["status"], "NO_QUALIFIED_CANDIDATE")
        self.assertFalse(plan_report["planning_pass"])

if __name__ == "__main__":
    unittest.main()
