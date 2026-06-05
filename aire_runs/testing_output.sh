#!/bin/bash

# Configuration
CSV_FILE="england_filenames.csv"
DATA_BASE_FOLDER="../workflow_outputs/"
OUTPUT_FOLDER="../outputs/"  # Where to save test plots
TOTAL_PARKS=30
STARTING_PARK=0
NUM_SAMPLES=3

echo "Reading parks from $CSV_FILE (indices $STARTING_PARK to $((STARTING_PARK + TOTAL_PARKS - 1)))"

# Read CSV and skip header
mapfile -t all_filenames < <(tail -n +2 "$CSV_FILE")

# Extract park names for our range (remove _pp_or_g_cmb.geojson suffix)
park_names=()
for i in $(seq $STARTING_PARK $((STARTING_PARK + TOTAL_PARKS - 1))); do
    if [ $i -lt ${#all_filenames[@]} ]; then
        # Remove quotes if present, then strip the _pp_or_g_cmb.geojson suffix
        filename="${all_filenames[$i]//\"/}"
        park_name="${filename%_pp_or_g_cmb.geojson}"
        park_names+=("$park_name")
    fi
done

echo "Found ${#park_names[@]} parks in range"

# Pick 3 random parks from the selection
if [ ${#park_names[@]} -lt $NUM_SAMPLES ]; then
    echo "Warning: Only ${#park_names[@]} parks available, sampling all"
    NUM_SAMPLES=${#park_names[@]}
fi

# Shuffle and pick first 3
selected_parks=($(printf '%s\n' "${park_names[@]}" | shuf | head -n $NUM_SAMPLES))

echo "Selected parks for testing: ${selected_parks[@]}"

# Run testing for each selected park
for park_name in "${selected_parks[@]}"; do
    data_folder="${DATA_BASE_FOLDER}${park_name}/"
    
    if [ -d "$data_folder" ]; then
        echo "Testing park: $park_name"
        python testing_output.py "$data_folder" "$OUTPUT_FOLDER"
    else
        echo "Warning: Data folder not found for $park_name: $data_folder"
    fi
done

echo "Testing complete!"