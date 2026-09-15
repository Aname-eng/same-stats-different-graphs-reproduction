import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
import matplotlib.pyplot as plt
from run_custom_target import stats_allowed

# 1. Load dino
source_df = pd.read_csv('course_source/seed_datasets/Datasaurus_data.csv', header=None, names=['x', 'y'])
source = source_df[['x', 'y']].to_numpy(float)
reference = source.copy()
N = len(source)

# 2. Extract components
img = Image.open('南开校徽.jpg').convert('L')
arr = np.asarray(img)
mask = (arr < 150)
h, w = mask.shape
cy, cx = 397.0, 399.5

y_grid, x_grid = np.indices((h, w))
dist_center = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)

# Segment components
mask_text = mask & (dist_center < 145)
mask_star = mask & (dist_center >= 145) & (dist_center < 235)
mask_ring = mask & (dist_center >= 340) & (dist_center < 375)

# Thinning to boundaries
b_text = mask_text ^ ndimage.binary_erosion(mask_text, structure=np.ones((3,3)))
b_star = mask_star ^ ndimage.binary_erosion(star_mask if 'star_mask' in locals() else mask_star, structure=np.ones((3,3)))
b_ring = mask_ring ^ ndimage.binary_erosion(mask_ring, structure=np.ones((3,3)))

# Coordinate transformation
scale = 0.115
def to_plot_coords(binary_mask):
    r, c = np.where(binary_mask)
    x = (c - cx) * scale + 54.26
    y = (cy - r) * scale + 47.83
    return np.column_stack((x, y))

target_text = to_plot_coords(b_text)
target_star = to_plot_coords(b_star)
target_ring = to_plot_coords(b_ring)

print(f'Target text points: {len(target_text)}, star points: {len(target_star)}, ring points: {len(target_ring)}')

# 3. Partition the 142 source points into quotas
d_text = np.min(np.sum((source[:, None, :] - target_text[None, :, :])**2, axis=2), axis=1)
d_star = np.min(np.sum((source[:, None, :] - target_star[None, :, :])**2, axis=2), axis=1)
d_ring = np.min(np.sum((source[:, None, :] - target_ring[None, :, :])**2, axis=2), axis=1)

n_text = 46
n_star = 50
n_ring = 46

order_text = np.argsort(d_text)
chosen_text = set(order_text[:n_text])

rem1 = [i for i in range(N) if i not in chosen_text]
order_star = sorted(rem1, key=lambda i: d_star[i])
chosen_star = set(order_star[:n_star])

chosen_ring = set([i for i in range(N) if i not in chosen_text and i not in chosen_star])

group = np.zeros(N, dtype=int)
for i in chosen_text:
    group[i] = 0
for i in chosen_star:
    group[i] = 1
for i in chosen_ring:
    group[i] = 2

target_dict = {0: target_text, 1: target_star, 2: target_ring}

# Precompute distance grids / KDTree or vectorized distance for speed!
from scipy.spatial import cKDTree
tree_text = cKDTree(target_text)
tree_star = cKDTree(target_star)
tree_ring = cKDTree(target_ring)
trees = {0: tree_text, 1: tree_star, 2: tree_ring}

# 4. Run simulated annealing
current = source.copy()
rng = np.random.default_rng(20260915)
iters = 120000
shake = 0.25

for it in range(iters):
    temp = 0.3 * (1 - it / iters)**2
    row = int(rng.integers(0, N))
    grp = group[row]
    tr = trees[grp]
    
    old_p = current[row]
    old_dist, _ = tr.query(old_p)
    
    for _ in range(8):
        xm = old_p[0] + rng.normal(0, shake)
        ym = old_p[1] + rng.normal(0, shake)
        if not (0 < xm < 100 and 0 < ym < 100):
            continue
        new_dist, _ = tr.query([xm, ym])
        do_bad = rng.random() < temp
        
        if new_dist < old_dist or new_dist < 0.6 or do_bad:
            trial = current.copy()
            trial[row] = [xm, ym]
            if stats_allowed(trial, reference, 2):
                current = trial
            break

dist_moved = np.sqrt(np.sum((source - current)**2, axis=1))
print(f'Finished {iters} iters. Mean moved: {dist_moved.mean():.2f}, max: {dist_moved.max():.2f}')

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
axes[0].scatter(target_ring[:, 0], target_ring[:, 1], s=1, c='lightgray', alpha=0.5)
axes[0].scatter(target_star[:, 0], target_star[:, 1], s=1, c='orange', alpha=0.5)
axes[0].scatter(target_text[:, 0], target_text[:, 1], s=1, c='blue', alpha=0.5)
axes[0].set_title('Target Components (Text, Star, Ring)')
axes[0].set_xlim(0, 100); axes[0].set_ylim(0, 100); axes[0].set_aspect('equal')

axes[1].scatter(current[group == 2, 0], current[group == 2, 1], s=25, c='darkgreen', label='Outer Ring (46 pts)')
axes[1].scatter(current[group == 1, 0], current[group == 1, 1], s=25, c='darkorange', label='8-pointed Star (50 pts)')
axes[1].scatter(current[group == 0, 0], current[group == 0, 1], s=25, c='darkblue', label='Text 南開 (46 pts)')
axes[1].set_title(f'Evolved Emblem (142 pts, Mean moved: {dist_moved.mean():.2f})')
axes[1].legend(loc='upper right')
axes[1].set_xlim(0, 100); axes[1].set_ylim(0, 100); axes[1].set_aspect('equal')

plt.savefig('analysis/test_grouped_emblem.png', dpi=150)
print('Saved analysis/test_grouped_emblem.png')
