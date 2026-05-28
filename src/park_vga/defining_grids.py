import geopandas as gpd
from shapely.geometry import box

def load_data(boundaries_file, primary_name, buffer_distance):
    # Load park boundaries
    park_gdf = gpd.read_file(boundaries_file)
    
    # Filter for the specific park
    park_gdf = park_gdf[park_gdf['Primary Name'] == primary_name]
    
    # Create buffer around the park boundary
    park_gdf['geometry'] = park_gdf.geometry.buffer(buffer_distance)
    
    return park_gdf


def example():
    print("hello world!")
    print("version 2")


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
    # print(corners) # for dev, but remove for scaling up.

    # convert each corner to a grid reference
    grid_refs = [OSGB36_to_os_grid(corner[1], corner[0], include_quadrant=True) for corner in corners]
    
    # return unique grid references
    return set(grid_refs)

def find_tiles(park_gdf, crs="EPSG:27700"):
    """From bounding park geometry, calculate bounding box and associated grid refs"""
    bbox_list = list(park_gdf.bounds.iloc[0])
    bbox = gpd.GeoSeries(box(*bbox_list), crs=crs)
    grid_refs = get_tile_refs_from_bbox(bbox)
    return set(grid_refs)