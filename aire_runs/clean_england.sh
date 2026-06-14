#!/bin/bash
#SBATCH --job-name=england_clean
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --output=logs/england_clean.log
#SBATCH --error=logs/england_clean.err
#SBATCH --mail-type=END,FAIL
#SBATCH --account=proj_a

mkdir -p logs
eval "$(pixi shell-hook --shell=bash)"
python clean_england_data.py