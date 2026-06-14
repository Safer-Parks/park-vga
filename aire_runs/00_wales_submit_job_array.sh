#!/bin/bash
#SBATCH --job-name=wales_parks
#SBATCH --array=0-22%5
#SBATCH --time=14:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=logs/wales_parks_%a.log
#SBATCH --error=logs/wales_parks_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --account=proj_a

mkdir -p logs
eval "$(pixi shell-hook --shell=bash)"
python wales_run_new.py \
    "$SLURM_ARRAY_TASK_ID" \
    "parameter_files/wales_filenames_00.csv" \
    "parks_final/" \
    "/mnt/scratch/earmmu/wales_aire_run_output/" \
    "/mnt/scratch/earmmu/wales_lidar/wales_dtm_32bit_cog.tif" \
    "/mnt/scratch/earmmu/wales_lidar/wales_dsm_32bit_cog.tif" \
    "../example_datasets/all_parks_ids.csv" \
    "../example_datasets/LUT_regions_authorities_filenames.geojson"