#!/bin/bash
#SBATCH --job-name=wales_clean
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=logs/wales_clean.log
#SBATCH --error=logs/wales_clean.err
#SBATCH --mail-type=END,FAIL
#SBATCH --account=proj_a

mkdir -p logs
eval "$(pixi shell-hook --shell=bash)"
python clean_wales_data.py