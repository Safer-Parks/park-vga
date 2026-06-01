from . import defining_grids
from . import lidar

def park_id(n, filepath):
    """Given a json file path, find the nth property in the feature collection and return the park id. ('id' property)"""
    import json
    with open(filepath) as f:
        data = json.load(f)
    return data['features'][n]['properties']['id']

def find_park_n(primary_name, filepath):
    """Given a json file path, find the index of the park with the given primary name."""
    import json
    with open(filepath) as f:
        data = json.load(f)
    park_names = [feature['properties']['Primary Name'] for feature in data['features']]
    return park_names.index(primary_name)

def find_smallest_park_id(filepath):
    """Given a json file path, find the smallest park in the feature collection.
    
    Return Park Name, park id, and N (the index of the park in the feature collection)."""
    import json
    with open(filepath) as f:
        data = json.load(f)
    park_ids = [feature['properties']['id'] for feature in data['features']]
    park_names = [feature['properties']['Primary Name'] for feature in data['features']]
    park_areas = [feature['properties']['Total Area (m²)'] for feature in data['features']]
    smallest_park_index = park_areas.index(min(park_areas))
    return park_names[smallest_park_index], park_ids[smallest_park_index], smallest_park_index


def workflow_eng(filepath, n, lidar_dtm, lidar_dsm, output_filepath, buffer_distance=20, spacing=10):
    park_id = park_id(n, filepath)
    print(f"Park ID: {park_id}")
    park_gdf = defining_grids.load_data(filepath, park_id, buffer_distance, type="id")
    park_files = defining_grids.park_geometry_to_file_path(park_gdf, lidar_dtm, lidar_dsm)
    if park_files == ([], []):
        print("No files found for park 1")
        return None
    else:
        print("Files found for park 1")
    hex_grid = defining_grids.create_hexagon_grid(park_gdf, spacing=spacing, return_mode='both')
    lidar_data = lidar.load_lidar_rasters_for_park(
            park_gdf, 
            park_files[0],  # dtm_paths
            park_files[1]   # dsm_paths
        )
    visibility_results = lidar.calculate_visibility_metrics(
            hex_grid["centroids"], 
            lidar_data['dsm'], 
            lidar_data['dtm'], 
            lidar_data['transform'],
            observer_height=1.0,
            target_height=0,
            max_distance=100
        )
    visibility_results = visibility_results.set_geometry(hex_grid["polygons"].geometry)
    park_original =  defining_grids.load_data(filepath, park_id, 0, type="id")
    park_boundary = park_original.geometry.iloc[0]
    visibility_clipped = visibility_results[visibility_results.geometry.intersects(park_boundary)]
    vis_data_to_save = visibility_clipped.to_crs('EPSG:4326')
    # save out visibility results as geojson here
    # output_path = f"{output_filepath}/visibility_results_park_{park_id}.geojson"
    # vis_data_to_save.to_file(output_path, driver='GeoJSON')
    # print(f"Visibility results saved to {output_path}")

