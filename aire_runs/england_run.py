#!/usr/bin/env python
"""
Process a single boundaries file from wales_filenames.csv and run the
park visibility workflow on each park.

Usage:
    python wales_run.py <csv_row_index> <csv_file> <data_folder> \
        <output_folder> <wales_dtm> <wales_dsm> <park_ids_file> <lut_file>
"""

import pandas as pd
import geopandas as gpd
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import park_vga

# Arguments
csv_row_index = int(sys.argv[1])
csv_file = sys.argv[2]
data_folder = sys.argv[3]
output_folder = sys.argv[4]
wales_dtm = sys.argv[5]
wales_dsm = sys.argv[6]
park_ids_file = sys.argv[7]
lut_file = sys.argv[8]

# Open the filenames csv
files_list = pd.read_csv(csv_file)
filename = files_list.loc[csv_row_index, "filename"]

file_path = os.path.join(data_folder, filename)
gdf = gpd.read_file(file_path)
output_sub_dir = os.path.join(output_folder, filename.split(".")[0])
os.makedirs(output_sub_dir, exist_ok=True)

check_regions_gdf = gpd.read_file(lut_file)
check_regions_gdf["filename"] = check_regions_gdf["filename"].apply(lambda x: Path(x).name)
country = check_regions_gdf.loc[check_regions_gdf["filename"] == filename, "country"].values[0]
authority = check_regions_gdf.loc[check_regions_gdf["filename"] == filename, "auth_name_e"].values[0]
print(country, authority)

# Filter the park ids dataframe to just the authority
park_ids_file_df = pd.read_csv(park_ids_file)
park_ids_file_df = park_ids_file_df.loc[park_ids_file_df["auth_name_e"] == authority]
print(len(park_ids_file_df))

for n in range(len(gdf)):
    print(f"{n}/{len(gdf)}")
    park_id = gdf.loc[n, "id"]
    print(park_id)
    park_id_safe = park_ids_file_df.loc[park_ids_file_df["old_park_id"] == park_id, "new_park_id"].values[0]
    print(park_id_safe)
    
    output_file = os.path.join(output_sub_dir, f"{park_id_safe}_visibility.geojson")
    if Path(output_file).exists():
        print(f"Output file {output_file} already exists, skipping park {park_id_safe}")
        continue
    
    if country == "England":
        dtm_path = wales_dtm
        dsm_path = wales_dsm
        print(file_path)
        print(output_sub_dir)
        results = park_vga.workflow.workflow_eng(file_path, n,
                                            dtm_path, dsm_path,
                                            output_sub_dir,
                                            spacing=12,
                                            return_results=False, save_results=True,
                                            park_id_for_file_name=park_id_safe,
                                            max_distance=80)