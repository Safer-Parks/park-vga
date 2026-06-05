#!/bin/bash

# 296 parks in England, so array from 0-295

# Number of parallel jobs
PARALLEL_JOBS=3
# TOTAL_PARKS=296
TOTAL_PARKS=30 # For testing with a smaller number of parks 

echo "Starting to process $TOTAL_PARKS parks with $PARALLEL_JOBS parallel jobs"

declare -a pids

for i in $(seq 0 $((TOTAL_PARKS - 1))); do
    echo "Submitting park $i ($((i+1))/$TOTAL_PARKS)"
    
    python england_run.py \
        "$i" \
        "england_filenames.csv" \
        "parks_gardens_id/" \
        "../workflow_outputs/" \
        "/Volumes/Extreme SSD/DTM" \
        "/Volumes/Extreme SSD/FZ_DSM" \
        "../example_datasets/all_parks_ids.csv" \
        "../example_datasets/LUT_regions_authorities_filenames.geojson" &
    
    pids+=($!)
    
    # If we've started PARALLEL_JOBS jobs, wait for the first one to finish
    if [ ${#pids[@]} -ge $PARALLEL_JOBS ]; then
        wait ${pids[0]}
        pids=("${pids[@]:1}")
    fi
done

# Wait for remaining jobs to finish
for pid in "${pids[@]}"; do
    wait $pid
done

echo "All $TOTAL_PARKS parks processed!"