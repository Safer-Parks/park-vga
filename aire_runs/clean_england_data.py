import pandas as pd
import os
import glob
import geopandas as gpd

import warnings
warnings.filterwarnings('ignore', message='Geometry is in a geographic CRS')

output_path = "/mnt/scratch/earmmu/england_aire_run_output"
new_output_path = "/mnt/scratch/earmmu/england_aire_run_output_centroids"

folders = glob.glob(f"{output_path}/*")

for folder in folders:
    print(f"Folder: {folder}")
    park_files_batch = glob.glob(f"{folder}/*")
    print(f"Number of files in folder: {len(park_files_batch)}")
    for park in park_files_batch:
        df = gpd.read_file(park)
        # we want to skip the smaller parks
        if len(df) < 20:
            continue
        
        print(f"{park} has {len(df)} hexes, which is above the cutoff of 20.")
        # the variable park contains the file path,
        # we want to create a new file path, where ../workflow_outputs is replaced with ../workflow_outputs_centroids
        new_park = park.replace(str(output_path), str(new_output_path))
        print(f"New park file path: {new_park}")
        if os.path.exists(new_park):
            print(f"File {new_park} already exists, skipping.")
            continue
        
        # now, we want to set the hex centroids instead of polygons
        df['geometry'] = df.geometry.centroid

        # save the file to the path new_park, ensuring that the directory exists
        # note the filepath provided is a full path to the file, not just the folder - we don't
        #want to create a new folder, we want to create the full path to the file
        os.makedirs(os.path.dirname(new_park), exist_ok=True)
        df.to_file(new_park)