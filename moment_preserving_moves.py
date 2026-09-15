"""Fixed-N moves preserving the first and second moments of a 2-D point set.

Only the proposal/validation kernel is supplied. This is NOT a logo optimizer:
it does not preprocess a logo, choose component quotas, or guarantee convergence.
Requires NumPy. Run `python moment_preserving_moves.py` for a synthetic unit test.

All rows remain in their original order. No points are added or deleted.
Mathematical preservation is exact; floating-point arithmetic introduces drift.
Always check the same rounding/standard-deviation convention used by your project.
"""
from __future__ import annotations

import json
from typing import Callable, Sequence
import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
Signature = tuple[str, ...]

# Cross-product matrix for the unit vector (1,1,1)/sqrt(3).
_K = np.array([[0., -1., 1.], [1., 0., -1.], [-1., 1., 0.]]) / np.sqrt(3.)


def _points(points: ArrayLike) -> FloatArray:
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
        raise ValueError('points must have shape (N, 2), with N >= 3')
    if not np.isfinite(p).all():
        raise ValueError('points must contain only finite coordinates')
    return p


def stats5(points: ArrayLike, ddof: int = 1) -> FloatArray:
    """Return mean_x, mean_y, sd_x, sd_y, Pearson_r (unrounded)."""
    p = _points(points)
    if ddof not in (0, 1):
        raise ValueError('ddof must be 0 (population) or 1 (sample)')
    mu = p.mean(axis=0)
    z = p - mu
    cov = z.T @ z / (len(p) - ddof)
    sd = np.sqrt(np.diag(cov))
    if np.any(sd <= 0):
        raise ValueError('both coordinate variances must be positive')
    return np.array([*mu, *sd, cov[0, 1] / (sd[0] * sd[1])])


def signature2(points: ArrayLike, ddof: int = 1) -> Signature:
    """Python .2f formatting; replace this if your project uses other tie rules."""
    return tuple(f'{v:.2f}' for v in stats5(points, ddof=ddof))


def rotate_three(points: ArrayLike, indices: Sequence[int], theta: float) -> FloatArray:
    """Return one atomic 3-point proposal, preserving mean and covariance.

    Rotation is in POINT-INDEX space, not an ordinary rotation in the x-y plane.
    Select overlapping triples across iterations, not permanently fixed triples.
    Do not clip, snap, round, or individually project the resulting coordinates.
    """
    p = _points(points)
    ix_raw = np.asarray(indices)
    if ix_raw.shape != (3,) or not np.issubdtype(ix_raw.dtype, np.integer):
        raise ValueError('indices must be exactly three integer row indices')
    ix = ix_raw.astype(np.intp, copy=False)
    if len(np.unique(ix)) != 3 or np.any(ix < 0) or np.any(ix >= len(p)):
        raise ValueError('indices must be distinct and in range')
    if not np.isfinite(theta):
        raise ValueError('theta must be finite')
    b = p[ix]
    center = b.mean(axis=0)
    z = b - center
    out = p.copy()
    out[ix] = center + np.cos(theta) * z + np.sin(theta) * (_K @ z)
    return out


def is_legal(
    candidate: ArrayLike,
    expected_n: int,
    reference: Signature,
    *,
    ddof: int = 1,
    bounds: ArrayLike | None = None,
) -> bool:
    """Hard gate. Optional bounds is [[xmin,xmax],[ymin,ymax]]."""
    p = np.asarray(candidate, dtype=np.float64)
    if p.shape != (expected_n, 2) or not np.isfinite(p).all():
        return False
    if bounds is not None:
        b = np.asarray(bounds, dtype=np.float64)
        if b.shape != (2, 2) or np.isnan(b).any() or np.any(b[:, 0] > b[:, 1]):
            raise ValueError('bounds must be [[xmin,xmax],[ymin,ymax]]')
        if np.any(p < b[:, 0]) or np.any(p > b[:, 1]):
            return False
    try:
        return signature2(p, ddof=ddof) == reference
    except ValueError:
        return False


def single_point_prefixes(
    points: ArrayLike,
    indices: Sequence[int],
    theta: float,
    reference: Signature,
    *,
    ddof: int = 1,
    bounds: ArrayLike | None = None,
    max_halvings: int = 60,
) -> tuple[list[FloatArray], float] | None:
    """Find a triple move executable as three legal single-row updates.

    Prevalidate EVERY prefix, halving the angle until all prefixes pass.
    Then evaluate the entire move with your shape-energy acceptance rule and,
    if accepted, commit the returned states in order. Rejected trials need not
    be saved. This is a coordinated proposal, not the original independent
    single-point Metropolis chain. The extra prefix restriction can make moves
    much smaller than atomic triple moves.
    """
    p = _points(points)
    if max_halvings < 0:
        raise ValueError('max_halvings must be nonnegative')
    if not is_legal(p, len(p), reference, ddof=ddof, bounds=bounds):
        raise ValueError('initial state fails the hard gate')
    for _ in range(max_halvings + 1):
        endpoint = rotate_three(p, indices, theta)
        if np.array_equal(endpoint, p):
            return None
        current = p.copy()
        states: list[FloatArray] = []
        for i in indices:
            current[int(i)] = endpoint[int(i)]
            if not is_legal(current, len(p), reference, ddof=ddof, bounds=bounds):
                break
            states.append(current.copy())
        if len(states) == 3:
            return states, float(theta)
        theta *= 0.5
    return None


def metropolis_step(
    points: ArrayLike,
    current_energy: float,
    loss: Callable[[FloatArray], float],
    rng: np.random.Generator,
    reference: Signature,
    temperature: float,
    angle_sd: float,
    *,
    ddof: int = 1,
    bounds: ArrayLike | None = None,
) -> tuple[FloatArray, float, bool]:
    """One atomic triple Metropolis step for a FIXED energy function.

    Uniform distinct triples and symmetric zero-mean angles give a symmetric
    proposal. State-dependent triple selection needs a Hastings correction for
    an exact Metropolis-Hastings interpretation. Recompute current_energy when
    changing the target, weights, or assignment surrogate.
    """
    p = _points(points)
    if not np.isfinite(current_energy):
        raise ValueError('current_energy must be finite')
    if not np.isfinite(temperature) or temperature < 0:
        raise ValueError('temperature must be finite and nonnegative')
    if not np.isfinite(angle_sd) or angle_sd <= 0:
        raise ValueError('angle_sd must be finite and positive')
    ix = rng.choice(len(p), 3, replace=False)
    candidate = rotate_three(p, ix, float(rng.normal(0., angle_sd)))
    if not is_legal(candidate, len(p), reference, ddof=ddof, bounds=bounds):
        return p, current_energy, False
    proposed_energy = float(loss(candidate))
    if not np.isfinite(proposed_energy):
        return p, current_energy, False
    delta = proposed_energy - current_energy
    accepted = delta <= 0
    if not accepted and temperature > 0:
        u = max(float(rng.random()), np.finfo(float).tiny)
        accepted = np.log(u) < -delta / temperature
    if accepted:
        return candidate, proposed_energy, True
    return p, current_energy, False


def self_test(n_moves: int = 100_000) -> dict:
    """Synthetic numerical test only; no Datasaurus or logo convergence test."""
    rng = np.random.default_rng(20260915)
    n = 142
    mu = np.array([54.26, 47.83])
    sx, sy, corr = 16.77, 26.94, -0.06
    cov = np.array([[sx*sx, corr*sx*sy], [corr*sx*sy, sy*sy]])
    a = rng.normal(size=(n, 2))
    a -= a.mean(axis=0)
    q, _ = np.linalg.qr(a, mode='reduced')
    p = mu + np.sqrt(n-1) * q @ np.linalg.cholesky(cov).T
    initial = p.copy()
    base = stats5(p)
    ref = signature2(p)
    max_error = np.zeros(5)
    for _ in range(n_moves):
        ix = rng.choice(n, 3, replace=False)
        p = rotate_three(p, ix, float(rng.normal(0., .2)))
        current = stats5(p)
        max_error = np.maximum(max_error, np.abs(current - base))
        assert tuple(f'{v:.2f}' for v in current) == ref
        assert p.shape == (n, 2)
    proposal = single_point_prefixes(initial, (0, 1, 2), .2, ref)
    assert proposal is not None
    states, angle = proposal
    previous = initial
    for state in states:
        assert is_legal(state, n, ref)
        assert np.count_nonzero(np.any(state != previous, axis=1)) <= 1
        previous = state
    # Theta followed by -theta approximately recovers every row in order.
    back = rotate_three(rotate_three(initial, (0, 1, 2), .2), (0, 1, 2), -.2)
    result = {
        'test_type': 'synthetic moment-invariance unit test; NOT logo convergence',
        'n': n,
        'n_moves': n_moves,
        'seed': 20260915,
        'all_rounding_checks_passed': True,
        'signature': list(ref),
        'stat_order': ['mean_x', 'mean_y', 'sd_x', 'sd_y', 'Pearson_r'],
        'max_absolute_drift_across_all_steps': max_error.tolist(),
        'single_point_prefix_test': 'passed',
        'single_point_prefix_angle': angle,
        'round_trip_max_coordinate_error': float(np.max(np.abs(back-initial))),
    }
    return result


if __name__ == '__main__':
    print(json.dumps(self_test(), indent=2, ensure_ascii=False))
