#!/bin/bash
#SBATCH --job-name=test_height_parks
#SBATCH --array=0-22%5
#SBATCH --time=20:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=logs/wales_parks_%a.log
#SBATCH --error=logs/wales_parks_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --account=proj_a

mkdir -p logs
eval "$(pixi shell-hook --shell=bash)"
python england_run.py \
    "$SLURM_ARRAY_TASK_ID" \
    "testing_leeds_bradford.csv" \
    "parks_gardens_id/" \
    "/mnt/scratch/earmmu/testing_height_aire_run_output/" \
    "/mnt/scratch/earmmu/england_lidar" \
    "/mnt/scratch/earmmu/england_lidar/DSM" \
    "../example_datasets/all_parks_ids.csv" \
    "../example_datasets/LUT_regions_authorities_filenames.geojson"
