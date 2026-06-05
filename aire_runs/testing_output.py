"""
This script tests output by producing a few quick plots of different regions.
"""

import os
import random
import geopandas as gpd
import os
from pathlib import Path
import sys
import matplotlib.pyplot as plt

data_folder = sys.argv[1]
output_folder = sys.argv[2]

files = os.listdir(data_folder)
visibility_files = [f for f in files if "visibility" in f]
foliage_files = [f for f in files if "foliage" in f]
random_visibility_file = random.choice(visibility_files)
# then using the park_id (so the file prefix, which is the same for both visibility and foliage) 
# find the corresponding foliage file
park_id = random_visibility_file.split("_")[0]
random_foliage_file = [f for f in foliage_files if f.startswith(park_id)][0]

vis = gpd.read_file(os.path.join(data_folder, random_visibility_file))
foliage = gpd.read_file(os.path.join(data_folder, random_foliage_file))

# save a single plot with both foliage and visibility side by side
# and save to a filename that uses the park id in the output folder
plot_file_path = os.path.join(output_folder, f"{park_id}_test_plot.png")

fig, ax = plt.subplots(2, 2, figsize=(20, 10))


vis.plot(column="visibility_pct", cmap="viridis", legend=True, ax=ax[0, 0])
foliage.plot(column="low_level_<0.5", cmap="viridis", legend=True, ax=ax[0, 1])
foliage.plot(column="mid_level_0.5-2", cmap="viridis", legend=True, ax=ax[1, 0])
foliage.plot(column="tall_2+", cmap="viridis", legend=True, ax=ax[1, 1])

plt.tight_layout()
plt.savefig(plot_file_path)
print(f"Saved test plot to {plot_file_path}")