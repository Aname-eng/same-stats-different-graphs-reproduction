import unittest
import numpy as np
import pandas as pd
from pathlib import Path
from moment_preserving_moves import stats5, signature2, is_legal, _points

class TestStatsAudit(unittest.TestCase):
    def setUp(self):
        dino_path = Path("course_source/seed_datasets/Datasaurus_data.csv")
        self.dino_df = pd.read_csv(dino_path, header=None, names=["x", "y"])
        self.dino_pts = self.dino_df[["x", "y"]].to_numpy(float)
        self.ref_sig = ("54.26", "47.83", "16.77", "26.94", "-0.06")

    def test_original_dino_signature(self):
        sig = signature2(self.dino_pts, ddof=1)
        self.assertEqual(sig, self.ref_sig)
        s5 = stats5(self.dino_pts, ddof=1)
        self.assertAlmostEqual(s5[0], 54.26327324, places=6)
        self.assertAlmostEqual(s5[1], 47.83225282, places=6)
        self.assertAlmostEqual(s5[2], 16.76514204, places=6)
        self.assertAlmostEqual(s5[3], 26.93540349, places=6)
        self.assertAlmostEqual(s5[4], -0.06447185, places=6)

    def test_ddof_distinction(self):
        s_sample = stats5(self.dino_pts, ddof=1)
        s_pop = stats5(self.dino_pts, ddof=0)
        # Sample std must be strictly larger than population std by sqrt(N/(N-1))
        n = len(self.dino_pts)
        factor = np.sqrt(n / (n - 1))
        self.assertAlmostEqual(s_sample[2], s_pop[2] * factor, places=7)
        self.assertAlmostEqual(s_sample[3], s_pop[3] * factor, places=7)

    def test_positive_and_negative_correlation(self):
        x = np.array([10., 20., 30., 40., 50.])
        y_pos = np.array([12., 21., 33., 42., 51.])
        pts_pos = np.column_stack((x, y_pos))
        s_pos = stats5(pts_pos, ddof=1)
        self.assertGreater(s_pos[4], 0.9)
        self.assertFalse(signature2(pts_pos, ddof=1)[4].startswith("-"))

        y_neg = np.array([51., 42., 33., 21., 12.])
        pts_neg = np.column_stack((x, y_neg))
        s_neg = stats5(pts_neg, ddof=1)
        self.assertLess(s_neg[4], -0.9)
        self.assertTrue(signature2(pts_neg, ddof=1)[4].startswith("-"))

    def test_nan_inf_rejection(self):
        pts_nan = self.dino_pts.copy()
        pts_nan[0, 0] = np.nan
        with self.assertRaises(ValueError):
            _points(pts_nan)

        pts_inf = self.dino_pts.copy()
        pts_inf[0, 0] = np.inf
        with self.assertRaises(ValueError):
            _points(pts_inf)

    def test_is_legal_bounds_check(self):
        bounds = [[0., 100.], [0., 100.]]
        self.assertTrue(is_legal(self.dino_pts, len(self.dino_pts), self.ref_sig, ddof=1, bounds=bounds))
        out_pts = self.dino_pts.copy()
        out_pts[0, 0] = 105.0
        self.assertFalse(is_legal(out_pts, len(out_pts), self.ref_sig, ddof=1, bounds=bounds))

if __name__ == "__main__":
    unittest.main()
