"""Statistical audit and reference signatures for Same Stats Different Graphs."""
from __future__ import annotations
import math
from typing import Sequence, Tuple
import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
Signature = Tuple[str, ...]

REF_SIGNATURE: Signature = ("54.26", "47.83", "16.77", "26.94", "-0.06")
BOUNDS_0_100: FloatArray = np.array([[0.0, 100.0], [0.0, 100.0]], dtype=np.float64)

# High-precision baseline calculated from course_source/seed_datasets/Datasaurus_data.csv
MU_0 = np.array([54.26327324, 47.83225282], dtype=np.float64)
SX_0 = 16.76514204
SY_0 = 26.93540349
R_0 = -0.06447185
COV_0 = np.array([
    [SX_0 * SX_0, R_0 * SX_0 * SY_0],
    [R_0 * SX_0 * SY_0, SY_0 * SY_0]
], dtype=np.float64)

def check_points(points: ArrayLike) -> FloatArray:
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
        raise ValueError("points must have shape (N, 2), with N >= 3")
    if not np.isfinite(p).all():
        raise ValueError("points must contain only finite coordinates")
    return p

def stats5(points: ArrayLike, ddof: int = 1) -> FloatArray:
    p = check_points(points)
    if ddof not in (0, 1):
        raise ValueError("ddof must be 0 (population) or 1 (sample)")
    mu = p.mean(axis=0)
    z = p - mu
    cov = z.T @ z / (len(p) - ddof)
    sd = np.sqrt(np.diag(cov))
    if np.any(sd <= 0):
        raise ValueError("both coordinate variances must be positive")
    corr = cov[0, 1] / (sd[0] * sd[1])
    return np.array([mu[0], mu[1], sd[0], sd[1], corr], dtype=np.float64)

def signature2(points: ArrayLike, ddof: int = 1) -> Signature:
    s = stats5(points, ddof=ddof)
    return tuple(f"{v:.2f}" for v in s)

def is_legal(
    candidate: ArrayLike,
    expected_n: int,
    reference: Signature = REF_SIGNATURE,
    *,
    ddof: int = 1,
    bounds: ArrayLike | None = BOUNDS_0_100,
) -> bool:
    p = np.asarray(candidate, dtype=np.float64)
    if p.shape != (expected_n, 2) or not np.isfinite(p).all():
        return False
    if bounds is not None:
        b = np.asarray(bounds, dtype=np.float64)
        if b.shape != (2, 2) or np.isnan(b).any() or np.any(b[:, 0] > b[:, 1]):
            raise ValueError("bounds must be [[xmin,xmax],[ymin,ymax]]")
        if np.any(p <= b[:, 0]) or np.any(p >= b[:, 1]):
            return False
    try:
        return signature2(p, ddof=ddof) == reference
    except ValueError:
        return False
