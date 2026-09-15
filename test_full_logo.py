import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
from run_custom_target import stats_allowed

# 1. Load dino
source_df = pd.read_csv('course_source/seed_datasets/Datasaurus_data.csv', header=None, names=['x', 'y'])
source = source_df[['x', 'y']].to_numpy(float)
reference = source.copy()
N = len(source)

# 2. Load Nankai emblem WITH internal patterns (components: text + star + circle)
target_df = pd.read_csv('targets/南开校徽_components.csv')[['x', 'y']]
tc = target_df.mean()
target = target_df.to_numpy(float)
# Center to (54.26, 47.83) keeping 1:1 true aspect ratio!
target[:, 0] = target[:, 0] - tc['x'] + 54.26
target[:, 1] = target[:, 1] - tc['y'] + 47.83
scale = 0.72
target = (target - np.array([54.26, 47.83])) * scale + np.array([54.26, 47.83])

print('Target components count:', len(target))

# Test dynamic 1-to-1 assignment annealing
current = source.copy()
rng = np.random.default_rng(20260915)

# Initial optimal matching
cost = np.sum((current[:, None, :] - target[None, :, :])**2, axis=2)
row_ind, col_ind = linear_sum_assignment(cost)
assignment = col_ind # current[i] is matched to target[assignment[i]]

initial_error = np.mean(np.sum((current - target[assignment])**2, axis=1))
print('Initial 1-to-1 assignment error:', initial_error)

iters = 100000
shake = 0.25

for i in range(iters):
    temp = 0.4 * (1 - i / iters)**2
    # Periodically re-optimize assignment every 1000 steps
    if i > 0 and i % 1000 == 0:
        cost = np.sum((current[:, None, :] - target[None, :, :])**2, axis=2)
        _, col_ind = linear_sum_assignment(cost)
        assignment = col_ind
        
    row = int(rng.integers(0, N))
    old_p = current[row].copy()
    assigned_g = target[assignment[row]]
    old_dist = np.sum((old_p - assigned_g)**2)
    
    # Try multiple moves
    for _ in range(8):
        xm = old_p[0] + rng.normal(0, shake)
        ym = old_p[1] + rng.normal(0, shake)
        if not (0 < xm < 100 and 0 < ym < 100):
            continue
        new_dist = np.sum((np.array([xm, ym]) - assigned_g)**2)
        do_bad = rng.random() < temp
        if new_dist < old_dist or new_dist < 1.0 or do_bad:
            trial = current.copy()
            trial[row] = [xm, ym]
            if stats_allowed(trial, reference, 2):
                current = trial
            break

final_error = np.mean(np.sum((current - target[assignment])**2, axis=1))
print('Final 1-to-1 assignment error:', final_error)
dist_moved = np.sqrt(np.sum((source - current)**2, axis=1))
print(f'Mean dist moved: {dist_moved.mean():.2f}, max: {dist_moved.max():.2f}')

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].scatter(target[:, 0], target[:, 1], s=25, c='red', alpha=0.7)
axes[0].set_title('Target Nankai Emblem (With Internal Text Pattern)')
axes[0].set_aspect('equal')
axes[0].set_xlim(0, 100); axes[0].set_ylim(0, 100)

axes[1].scatter(target[:, 0], target[:, 1], s=15, c='red', alpha=0.2)
axes[1].scatter(current[:, 0], current[:, 1], s=25, c='purple')
axes[1].set_title(f'Evolved Points (1-to-1 Matching, Mean moved: {dist_moved.mean():.2f})')
axes[1].set_aspect('equal')
axes[1].set_xlim(0, 100); axes[1].set_ylim(0, 100)

plt.savefig('analysis/test_full_logo_assignment.png', dpi=150)
print('Saved analysis/test_full_logo_assignment.png')
