import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile
from shapely.geometry import Point, LineString, Polygon, MultiPolygon


def load_lidar_rasters_for_park(park_geometry, dtm_paths, dsm_paths):
    """
    Load and mosaic DSM and DTM rasters from UK National LiDAR Programme.
    
    Parameters:
    -----------
    park_geometry : GeoDataFrame or Shapely geometry
        Park boundary geometry
    dtm_paths : list
        List of DTM file paths
    dsm_paths : list
        List of DSM file paths
    
    Returns:
    --------
    dict with 'dsm', 'dtm', 'height_above_ground', 'dsm_meta', 'dtm_meta', 'transform', 'crs'
    or None if error
    """
    
    # Validate inputs
    if not dtm_paths or not dsm_paths:
        print("ERROR: Empty DTM or DSM file list provided")
        return None
    
    print(f"Loading {len(dsm_paths)} DSM and {len(dtm_paths)} DTM files")
    
    # Handle both GeoDataFrame and geometry inputs
    if isinstance(park_geometry, gpd.GeoDataFrame):
        park_gdf = park_geometry.copy()
        park_geom_single = park_geometry.geometry.iloc[0]
    else:
        park_geom_single = park_geometry
        if hasattr(park_geometry, 'crs'):
            park_gdf = gpd.GeoDataFrame([1], geometry=[park_geometry], crs=park_geometry.crs)
        else:
            # Assume WGS84 (lat/lon) if no CRS provided
            park_gdf = gpd.GeoDataFrame([1], geometry=[park_geometry], crs='EPSG:4326')

    
    # Find the raster CRS by checking all files
    raster_crs = None
    for dsm_file in dsm_paths:
        with rasterio.open(dsm_file) as src:
            if src.crs is not None:
                raster_crs = src.crs
                break
    
    # If no DSM has CRS, check DTM files
    if raster_crs is None:
        for dtm_file in dtm_paths:
            with rasterio.open(dtm_file) as src:
                if src.crs is not None:
                    raster_crs = src.crs
                    break
    
    # If still no CRS found, use park's CRS
    if raster_crs is None:
        raster_crs = park_gdf.crs
        print(f"WARNING: No CRS found in any raster. Assigning park CRS {raster_crs}")
    else:
        # Reproject park if needed
        if park_gdf.crs is not None and park_gdf.crs.to_string() != raster_crs.to_string():
            print(f"Reprojecting park geometry to match raster CRS {raster_crs}")
            park_gdf = park_gdf.to_crs(raster_crs)
            park_geom_single = park_gdf.geometry.iloc[0]
    
    # Function to mosaic multiple rasters with NoData handling
    def mosaic_rasters(file_list, target_crs=None):
        # Use the provided target_crs (from parent function level)
        # If not provided, determine from first raster that has one
        if target_crs is None:
            for f in file_list:
                with rasterio.open(f) as src:
                    if src.crs is not None:
                        target_crs = src.crs
                        break
        
        # If still no CRS found, use the park's CRS
        if target_crs is None:
            target_crs = park_gdf.crs
            print(f"WARNING: No CRS found in rasters. Assigning {target_crs}")
        
        if len(file_list) == 1:
            with rasterio.open(file_list[0]) as src:
                data = src.read(1)
                # Replace NoData values with NaN
                if src.nodata is not None:
                    data = np.where(data == src.nodata, np.nan, data)
                # Also handle extreme values
                data = np.where(data < -1000, np.nan, data)
                # Create output metadata
                out_meta = src.meta.copy()
                if out_meta['crs'] is None:
                    out_meta['crs'] = target_crs
                    print(f"WARNING: {file_list[0]} has no CRS. Assigning {target_crs}")
                return data, src.transform, out_meta
        
        # For multiple files, open and ensure all have CRS
        # Use memory files to normalize CRS before merging
        normalized_files = []
        
        for f in file_list:
            with rasterio.open(f) as src:
                src_crs = src.crs if src.crs is not None else target_crs
                if src.crs is None:
                    print(f"WARNING: {f} has no CRS. Assigning {target_crs}")
                
                # Write to memory file with target CRS
                memfile = MemoryFile()
                out_meta = src.meta.copy()
                out_meta['crs'] = src_crs
                
                with memfile.open(**out_meta) as mem_dst:
                    mem_dst.write(src.read())
                
                # Re-open the memory file
                mem_dst = memfile.open()
                normalized_files.append((mem_dst, memfile))
        
        try:
            # Extract the dataset objects for merging
            src_datasets = [mem_dst for mem_dst, _ in normalized_files]
            
            mosaic, out_transform = merge(src_datasets, nodata=np.nan)
            
            # Clean up NoData values
            mosaic = mosaic[0]
            mosaic = np.where(mosaic < -1000, np.nan, mosaic)
            
            out_meta = src_datasets[0].meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": mosaic.shape[0],
                "width": mosaic.shape[1],
                "transform": out_transform,
                "nodata": np.nan,
                "crs": target_crs
            })
            return mosaic, out_transform, out_meta
        finally:
            for mem_dst, memfile in normalized_files:
                mem_dst.close()
                memfile.close()
    
    # Mosaic and clip DSM
    dsm_mosaic, dsm_transform, dsm_meta = mosaic_rasters(dsm_paths, target_crs=raster_crs)
    
    # Check for valid data
    valid_dsm = np.sum(~np.isnan(dsm_mosaic))
    print(f"DSM valid pixels: {valid_dsm} of {dsm_mosaic.size} ({valid_dsm/dsm_mosaic.size*100:.1f}%)")
    
    with MemoryFile() as memfile:
        with memfile.open(**dsm_meta) as dataset:
            dataset.write(dsm_mosaic, 1)
            park_geom_list = [park_geom_single.__geo_interface__]
            
            try:
                dsm_clipped, dsm_clip_transform = mask(dataset, park_geom_list, crop=True, nodata=np.nan)
                dsm_clipped = dsm_clipped[0]
            except ValueError as e:
                print(f"ERROR clipping DSM: {e}")
                print(f"Park bounds: {park_gdf.total_bounds}")
                print(f"Park CRS: {park_gdf.crs}, Raster CRS: {raster_crs}")
                return None
    
    # Mosaic and clip DTM
    dtm_mosaic, dtm_transform, dtm_meta = mosaic_rasters(dtm_paths, target_crs=raster_crs)
    
    # Check for valid data
    valid_dtm = np.sum(~np.isnan(dtm_mosaic))
    print(f"DTM valid pixels: {valid_dtm} of {dtm_mosaic.size} ({valid_dtm/dtm_mosaic.size*100:.1f}%)")
    
    with MemoryFile() as memfile:
        with memfile.open(**dtm_meta) as dataset:
            dataset.write(dtm_mosaic, 1)
            park_geom_list = [park_geom_single.__geo_interface__]
            dtm_clipped, dtm_clip_transform = mask(dataset, park_geom_list, crop=True, nodata=np.nan)
            dtm_clipped = dtm_clipped[0]
    
    # Calculate height above ground
    height_above_ground = dsm_clipped - dtm_clipped
    
    # Report statistics
    valid_height = ~np.isnan(height_above_ground)
    if np.sum(valid_height) > 0:
        height_range = f"{np.nanmin(height_above_ground):.1f}m to {np.nanmax(height_above_ground):.1f}m"
    else:
        height_range = "No valid data"
    
    print(f"Output shape: {dsm_clipped.shape}, Height range: {height_range}")
    
    # Update metadata for clipped rasters
    dsm_meta.update({
        "height": dsm_clipped.shape[0],
        "width": dsm_clipped.shape[1],
        "transform": dsm_clip_transform,
        "nodata": np.nan
    })
    
    dtm_meta.update({
        "height": dtm_clipped.shape[0],
        "width": dtm_clipped.shape[1],
        "transform": dtm_clip_transform,
        "nodata": np.nan
    })
    
    return {
        'dsm': dsm_clipped,
        'dtm': dtm_clipped,
        'height_above_ground': height_above_ground,
        'dsm_meta': dsm_meta,
        'dtm_meta': dtm_meta,
        'transform': dsm_clip_transform,
        'crs': raster_crs
    }

def extract_park_raster_wales(park_gdf, dtm_path, dsm_path):
    """
    Extract DTM and DSM data for a park from Wales COG rasters using bounding box.
    
    Simpler alternative to load_lidar_rasters_for_park() optimized for single-file 
    COG datasets (Wales) rather than tiled datasets (England).
    
    Parameters:
    -----------
    park_gdf : GeoDataFrame
        Park boundary geometry
    dtm_path : str
        Path to DTM raster file
    dsm_path : str
        Path to DSM raster file
    
    Returns:
    --------
    dict with keys:
        - 'dsm': DSM clipped array
        - 'dtm': DTM clipped array  
        - 'height_above_ground': DSM - DTM (vegetation/building height)
        - 'dsm_meta': DSM metadata
        - 'dtm_meta': DTM metadata
        - 'transform': rasterio Affine transform for clipped data
        - 'crs': Coordinate reference system
    
    or None if error
    """
    from rasterio.windows import from_bounds
    
    try:
        # Open DTM to get CRS
        with rasterio.open(dtm_path) as src:
            raster_crs = src.crs
        
        # Ensure park is in raster CRS
        if park_gdf.crs != raster_crs:
            print(f"Reprojecting park from {park_gdf.crs} to {raster_crs}")
            park_gdf = park_gdf.to_crs(raster_crs)
        
        minx, miny, maxx, maxy = park_gdf.bounds.iloc[0]
        
        # Extract DTM
        with rasterio.open(dtm_path) as src:
            window = from_bounds(minx, miny, maxx, maxy, src.transform)
            dtm_clipped = src.read(1, window=window)
            dtm_transform = src.window_transform(window)
            dtm_meta = src.meta.copy()
            dtm_meta.update({
                'height': dtm_clipped.shape[0],
                'width': dtm_clipped.shape[1],
                'transform': dtm_transform
            })
        
        # Extract DSM
        with rasterio.open(dsm_path) as src:
            window = from_bounds(minx, miny, maxx, maxy, src.transform)
            dsm_clipped = src.read(1, window=window)
            dsm_transform = src.window_transform(window)
            dsm_meta = src.meta.copy()
            dsm_meta.update({
                'height': dsm_clipped.shape[0],
                'width': dsm_clipped.shape[1],
                'transform': dsm_transform
            })
        
        # Calculate height above ground
        height_above_ground = dsm_clipped - dtm_clipped
        
        # Report statistics
        valid_pixels = np.sum(~np.isnan(height_above_ground))
        if valid_pixels > 0:
            height_range = f"{np.nanmin(height_above_ground):.1f}m to {np.nanmax(height_above_ground):.1f}m"
        else:
            height_range = "No valid data"
        
        print(f"Extracted {dsm_clipped.shape} pixels, Height range: {height_range}")
        
        return {
            'dsm': dsm_clipped,
            'dtm': dtm_clipped,
            'height_above_ground': height_above_ground,
            'dsm_meta': dsm_meta,
            'dtm_meta': dtm_meta,
            'transform': dtm_transform,
            'crs': raster_crs
        }
    
    except Exception as e:
        print(f"ERROR extracting park raster: {e}")
        return None


def point_to_raster_index(point, transform):
    """Convert a point to raster row/col indices"""
    from rasterio.transform import rowcol
    row, col = rowcol(transform, point.x, point.y)
    return int(row), int(col)

def points_to_raster_indices(points, transform):
    """Convert multiple points to raster indices at once (vectorized)"""
    from rasterio.transform import rowcol
    xs = np.array([p.x for p in points])
    ys = np.array([p.y for p in points])
    rows, cols = rowcol(transform, xs, ys)
    return np.column_stack([rows.astype(int), cols.astype(int)])

def get_elevation_at_point(point, raster, transform):
    """Get elevation value at a point from raster"""
    # row, col = points_to_raster_indices(point, transform)
    row, col = point_to_raster_index(point, transform)
    
    # Check bounds
    if 0 <= row < raster.shape[0] and 0 <= col < raster.shape[1]:
        return raster[row, col]
    return np.nan

def check_line_of_sight(observer_point, target_point, dsm, dtm, transform, 
                        observer_height=1.0, target_height=0):
    """
    Check if there is line of sight between two points
    
    Parameters:
    observer_point: Point geometry of observer
    target_point: Point geometry of target
    dsm: Digital Surface Model array
    dtm: Digital Terrain Model array  
    transform: rasterio transform
    observer_height: height of observer above ground (meters)
    target_height: height of target above ground (meters)
    
    Returns:
    bool: True if visible, False if blocked
    """
    # Get observer and target elevations
    obs_ground = get_elevation_at_point(observer_point, dtm, transform)
    target_ground = get_elevation_at_point(target_point, dtm, transform)
    
    if np.isnan(obs_ground) or np.isnan(target_ground):
        return False
    
    obs_elevation = obs_ground + observer_height
    target_elevation = target_ground + target_height
    
    # Calculate distance and number of sample points
    distance = observer_point.distance(target_point)
    
    if distance < 1:
        return True
    
    # Sample points along the line (every meter)
    num_samples = int(distance) + 1
    
    # Create line samples
    x_samples = np.linspace(observer_point.x, target_point.x, num_samples)
    y_samples = np.linspace(observer_point.y, target_point.y, num_samples)
    
    # Required height at each sample point (linear interpolation)
    required_heights = np.linspace(obs_elevation, target_elevation, num_samples)
    
    # Check each sample point
    for i in range(1, num_samples - 1):  # Skip start and end points
        sample_point = Point(x_samples[i], y_samples[i])
        
        # Get surface elevation at this point
        surface_elevation = get_elevation_at_point(sample_point, dsm, transform)
        
        if np.isnan(surface_elevation):
            continue
        
        # Check if surface blocks the line of sight
        if surface_elevation > required_heights[i]:
            return False
    
    return True

def calculate_visibility_metrics(analysis_points, dsm, dtm, transform, 
                                 observer_height=1.0, target_height=0, max_distance=100):
    """
    Calculate visibility metrics for all analysis points
    
    Parameters:
    analysis_points: GeoDataFrame of analysis points
    dsm: Digital Surface Model
    dtm: Digital Terrain Model
    transform: rasterio transform
    observer_height: observer eye height in meters; default 1 m
    max_distance: maximum visibility distance in meters
    
    Returns:
    GeoDataFrame with visibility metrics
    """
    print(f"Calculating visibility for {len(analysis_points)} points")
    
    results = []
    
    for idx, observer_row in analysis_points.iterrows():
        if idx % 50 == 0:
            print(f"Processing point {idx+1}/{len(analysis_points)}")
        
        observer_point = observer_row.geometry
        visible_count = 0
        total_checked = 0
        
        # Check visibility to all other points within max_distance
        for target_idx, target_row in analysis_points.iterrows():
            if idx == target_idx:
                continue
            
            target_point = target_row.geometry
            distance = observer_point.distance(target_point)
            
            if distance > max_distance:
                continue
            
            total_checked += 1
            
            if check_line_of_sight(observer_point, target_point, dsm, dtm, 
                                  transform, observer_height, target_height):
                visible_count += 1
        
        # Calculate visibility percentage
        if total_checked > 0:
            visibility_pct = (visible_count / total_checked) * 100
        else:
            visibility_pct = 0
        
        results.append({
            'geometry': observer_point,
            'visible_points': visible_count,
            'total_points': total_checked,
            'visibility_pct': visibility_pct
        })
    
    results_gdf = gpd.GeoDataFrame(results, crs=analysis_points.crs)

    
    return results_gdf

def extract_foliage_by_hexgrid(height_raster, transform, hex_polygons, 
                               min_height=0.1, crs='EPSG:27700'):
    """
    Extract foliage statistics from height raster, aggregated to hexagon grid.
    Outputs point-based GeoJSON with foliage metrics per hex.
    
    Parameters:
    -----------
    height_raster : ndarray
        Height above ground raster (DSM - DTM, NaN for no data)
    transform : rasterio.Affine
        Georeferencing transform for the raster
    hex_polygons : list of tuples
        Output from create_hexagon_polygons_from_bounds()
        [(Point(centroid), Polygon(hex_boundary)), ...]
    min_height : float
        Minimum vegetation height threshold (m)
    crs : str
        Coordinate reference system
    
    Returns:
    --------
    GeoDataFrame
        Points with columns: geometry, max_height, mean_height, 
        std_height, count_pixels, percent_cover, percent_cover_height_bands
    """
    from rasterio.transform import rowcol
    from rasterio.mask import mask
    from rasterio.io import MemoryFile
    
    foliage_data = []
    
    print(f"Extracting foliage data from {len(hex_polygons)} hexagons...")
    
    for hex_idx, (centroid, hex_poly) in enumerate(hex_polygons):
        
        # Create temporary raster memory file to clip to hex boundary
        temp_meta = {
            'driver': 'GTiff',
            'height': height_raster.shape[0],
            'width': height_raster.shape[1],
            'count': 1,
            'dtype': height_raster.dtype,
            'crs': crs,
            'transform': transform,
            'nodata': np.nan
        }
        
        try:
            with MemoryFile() as memfile:
                with memfile.open(**temp_meta) as dataset:
                    dataset.write(height_raster, 1)
                    
                    # Mask raster to hexagon boundary
                    clipped, clipped_transform = mask(
                        dataset, 
                        [hex_poly.__geo_interface__], 
                        crop=False,
                        nodata=np.nan
                    )
                    clipped = clipped[0]
            
            # Extract valid (non-NaN) values
            valid_mask = ~np.isnan(clipped)
            valid_heights = clipped[valid_mask]
            
            # Count pixels above minimum height threshold
            above_threshold = valid_heights[valid_heights >= min_height]
            
            # Calculate statistics
            if len(valid_heights) > 0:
                max_height = float(np.nanmax(valid_heights))
                mean_height = float(np.nanmean(valid_heights))
                std_height = float(np.nanstd(valid_heights))
                count_pixels = int(np.sum(valid_mask))
                percent_cover = float(np.sum(valid_mask) / valid_mask.size * 100)
                percent_above_threshold = float(len(above_threshold) / count_pixels * 100) if count_pixels > 0 else 0.0
            else:
                max_height = np.nan
                mean_height = np.nan
                std_height = np.nan
                count_pixels = 0
                percent_cover = 0.0
                percent_above_threshold = 0.0
            
            # Height band percentages (might use?)
            height_bands = {
                'low_level_<0.5': float(np.sum((valid_heights >= 0.15) & (valid_heights < 0.5)) / count_pixels * 100) if count_pixels > 0 else 0.0,
                'mid_level_0.5-2': float(np.sum((valid_heights >= 0.5) & (valid_heights < 2.0)) / count_pixels * 100) if count_pixels > 0 else 0.0,
                'tall_2+': float(np.sum(valid_heights >= 2.0) / count_pixels * 100) if count_pixels > 0 else 0.0,
            }
            
            foliage_data.append({
                'geometry': centroid,
                'max_height': max_height,
                'mean_height': mean_height,
                'std_height': std_height,
                'count_pixels': count_pixels,
                'percent_cover': percent_cover,
                f'percent_above_{min_height}m': percent_above_threshold,
                **height_bands
            })
        
        except Exception as e:
            # If clipping fails (hex outside raster bounds), record NaNs
            foliage_data.append({
                'geometry': centroid,
                'max_height': np.nan,
                'mean_height': np.nan,
                'std_height': np.nan,
                'count_pixels': 0,
                'percent_cover': 0.0,
                'percent_above_1m': 0.0,
                'low_level_<0.5': 0.0,
                'mid_level_0.5-2': 0.0,
                'tall_2+': 0.0,
            })
        
        if (hex_idx + 1) % max(1, len(hex_polygons) // 10) == 0:
            print(f"  Processed {hex_idx + 1} / {len(hex_polygons)} hexagons")
    
    # Convert to GeoDataFrame
    foliage_gdf = gpd.GeoDataFrame(foliage_data, crs=crs)
    
    return foliage_gdf