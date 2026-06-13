import geopandas as gpd
from shapely.geometry import box
import glob
import os
from shapely.geometry import Point, Polygon
import numpy as np

def load_data(boundaries_file, name, buffer_distance, type="primary name"):
    # Load park boundaries
    park_gdf = gpd.read_file(boundaries_file)
    
    # Filter for the specific park
    if type == "primary name":
        park_gdf = park_gdf[park_gdf['Primary Name'] == name]
    else:
        park_gdf = park_gdf[park_gdf['id'] == name]
    
    # Create buffer around the park boundary
    park_gdf['geometry'] = park_gdf.geometry.buffer(buffer_distance)
    
    return park_gdf


def example():
    print("hello world!")
    print("version 4")


def OSGB36_to_os_grid(easting, northing, include_quadrant=False):
    """
    Convert easting/northing (British National grid - OSGB36/EPSG:27700) directly to OS grid reference.
    See page 42 here: https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf
    for a map showing coordinate overlays on the UK.

    Parameters:
    -----------
    easting : float
        Easting in meters (EPSG:27700)
    northing : float
        Northing in meters (EPSG:27700)
    include_quadrant : bool
        If True, returns quadrant (ne, nw, se, sw). If False, returns basic 10km reference.
        
    Returns:
    --------
    str : OS grid reference (e.g., 'SD50' or 'SD50ne')
    """
    
    first_letters = ['S', 'T', 'N', 'O', 'H']
    second_letters = ['V', 'W', 'X', 'Y', 'Z',
                      'Q', 'R', 'S', 'T', 'U',
                      'L', 'M', 'N', 'O', 'P',
                      'F', 'G', 'H', 'J', 'K',
                      'A', 'B', 'C', 'D', 'E']
    
    e_500 = int(easting / 500000)
    n_500 = int(northing / 500000)
    e_100 = int((easting % 500000) / 100000)
    n_100 = int((northing % 500000) / 100000)
    
    try:
        first_letter = first_letters[n_500 * 2 + e_500]
        second_letter = second_letters[n_100 * 5 + e_100]
    except IndexError:
        return None
    
    e_within_100km = (easting % 100000) / 1000
    n_within_100km = (northing % 100000) / 1000
    e_10km = int(e_within_100km / 10)
    n_10km = int(n_within_100km / 10)
    
    grid_ref = f"{first_letter}{second_letter}{e_10km}{n_10km}"
    
    if include_quadrant:
        e_is_east = (e_within_100km % 10) >= 5
        n_is_north = (n_within_100km % 10) >= 5
        quadrant = ('ne' if e_is_east and n_is_north else
                   'se' if e_is_east else
                   'nw' if n_is_north else 'sw')
        grid_ref += quadrant
    
    return grid_ref


def get_tile_refs_from_bbox(bbox):
    # get the corner points of the bounding box
    corners = [bbox[0].exterior.coords[i] for i in range(4)]
    print(corners)

    # convert each corner to a grid reference
    # grid_refs = [OSGB36_to_os_grid(corner[1], corner[0], include_quadrant=True) for corner in corners]
    grid_refs = [OSGB36_to_os_grid(corner[0], corner[1], include_quadrant=True) for corner in corners]
    print("Grid refs for corners:", grid_refs)
    # return unique grid references
    return set(grid_refs)

def find_tiles(park_gdf, crs="EPSG:27700"):
    """From bounding park geometry, calculate bounding box and associated grid refs"""
    bbox_list = list(park_gdf.bounds.iloc[0])
    bbox = gpd.GeoSeries(box(*bbox_list), crs=crs)
    print("Calculating grid refs")
    grid_refs = get_tile_refs_from_bbox(bbox)
    return set(grid_refs)

def find_file_paths_old(tile_names, lidar_dtm, lidar_dsm):
    """Given a set of tile names, find the corresponding file paths for DTM and DSM"""
    dtm_paths = []
    dsm_paths = []
    
    for tile in tile_names:
        dtm_pattern = os.path.join(lidar_dtm, f"*{tile}*.tif")
        dsm_pattern = os.path.join(lidar_dsm, f"*{tile}*.tif")
        
        dtm_files = glob.glob(dtm_pattern)
        dsm_files = glob.glob(dsm_pattern)
        
        if dtm_files:
            dtm_paths.append(dtm_files[0])  # Assuming one file per tile
        else:
            print(f"Warning: No DTM file found for tile {tile}")
        
        if dsm_files:
            dsm_paths.append(dsm_files[0])  # Assuming one file per tile
        else:
            print(f"Warning: No DSM file found for tile {tile}")
    
    return dtm_paths, dsm_paths

def find_file_paths(tile_names, lidar_dtm, lidar_dsm):
    """Given a set of tile names, find the corresponding file paths for DTM and DSM"""
    dtm_paths = []
    dsm_paths = []
    
    # Get all files in the directories once (no recursive search)
    try:
        dtm_files = os.listdir(lidar_dtm)
    except OSError as e:
        print(f"Error reading DTM directory: {e}")
        dtm_files = []
    
    try:
        dsm_files = os.listdir(lidar_dsm)
    except OSError as e:
        print(f"Error reading DSM directory: {e}")
        dsm_files = []
    
    for tile in tile_names:
        # Find matching DTM file
        dtm_match = [f for f in dtm_files if tile in f and 'DTM' in f.upper() and f.endswith('.tif')]
        if dtm_match:
            dtm_paths.append(os.path.join(lidar_dtm, dtm_match[0]))
        else:
            print(f"Warning: No DTM file found for tile {tile}")
        
        # Find matching DSM file
        dsm_match = [f for f in dsm_files if tile in f and 'DSM' in f.upper() and f.endswith('.tif')]
        if dsm_match:
            dsm_paths.append(os.path.join(lidar_dsm, dsm_match[0]))
        else:
            print(f"Warning: No DSM file found for tile {tile}")
    
    return dtm_paths, dsm_paths

def park_geometry_to_file_path(park_gdf, lidar_dtm, lidar_dsm):
    print("Finding tile names from park geometry")
    tile_names = find_tiles(park_gdf)
    print("Tile name(s):", tile_names, "\nFinding file paths for these tiles")
    dtm_paths, dsm_paths = find_file_paths(tile_names, lidar_dtm, lidar_dsm)
    print("Paths found:", "\nDTM paths:", dtm_paths, "\nDSM paths:", dsm_paths)
    return dtm_paths, dsm_paths

def check_plot(park_gdf):
    park_gdf.plot()

def create_hexagon_grid(park_gdf, spacing=10, return_mode='centroids'):
    """
    Create a regular pointy-top hexagonal grid within a park boundary.
    
    Spacing refers to vertical distance between hexagon centroid rows.
    
    Reference: https://www.redblobgames.com/grids/hexagons/
    
    Parameters:
    -----------
    park_gdf : GeoDataFrame
        GeoDataFrame containing the park boundary (EPSG:27700)
    spacing : float
        Vertical distance in meters between adjacent hexagon centroid rows
    return_mode : str
        'centroids' - return GeoDataFrame of centroid points
        'polygons' - return GeoDataFrame of hexagon polygons  
        'both' - return dict with both 'centroids' and 'polygons'
    
    Returns:
    --------
    GeoDataFrame or dict
    """
    
    park_geometry = park_gdf.geometry.iloc[0]
    bounds = park_geometry.bounds
    
    # For pointy-top: vert_spacing = 1.5 × size, so size = spacing / 1.5
    size = spacing / 1.5
    
    # Horizontal spacing (width) = sqrt(3) × size
    h_spacing = np.sqrt(3) * size
    v_spacing = spacing  # = 1.5 × size
    
    # Pointy-top vertices at these angles
    vertex_angles = np.array([30, 90, 150, 210, 270, 330]) * np.pi / 180
    
    # Offset for odd rows: sqrt(3)/2 × size = h_spacing/2
    offset_odd_row = h_spacing / 2
    
    centroids = []
    polygons = []
    
    x_min, y_min, x_max, y_max = bounds
    y = y_min
    row = 0
    
    while y <= y_max:
        x = x_min
        # Offset alternating rows
        if row % 2 == 1:
            x += offset_odd_row
        
        while x <= x_max:
            centroid = Point(x, y)
            
            # Create hexagon polygon
            hex_x = x + size * np.cos(vertex_angles)
            hex_y = y + size * np.sin(vertex_angles)
            hexagon = Polygon(list(zip(hex_x, hex_y)))
            
            # Include if centroid in park or hexagon intersects boundary
            if park_geometry.contains(centroid) or park_geometry.intersects(hexagon):
                centroids.append(centroid)
                polygons.append(hexagon)
            
            x += h_spacing
        
        y += v_spacing
        row += 1
    
    centroids_gdf = gpd.GeoDataFrame(geometry=centroids, crs='EPSG:27700')
    
    if return_mode == 'centroids':
        print(f"Created {len(centroids_gdf)} pointy-top hexagon centroids ({spacing}m vertical spacing)")
        return centroids_gdf
    
    elif return_mode == 'polygons':
        polygons_gdf = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:27700')
        print(f"Created {len(polygons_gdf)} pointy-top hexagon polygons ({spacing}m vertical spacing)")
        return polygons_gdf
    
    elif return_mode == 'both':
        polygons_gdf = gpd.GeoDataFrame(geometry=polygons, crs='EPSG:27700')
        print(f"Created {len(centroids_gdf)} pointy-top hexagons ({spacing}m vertical spacing)")
        return {
            'centroids': centroids_gdf,
            'polygons': polygons_gdf
        }
    
    else:
        raise ValueError(f"return_mode must be 'centroids', 'polygons', or 'both'")

