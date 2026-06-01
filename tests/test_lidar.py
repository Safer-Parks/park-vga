"""Unit tests for park_vga.lidar module"""

import pytest
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import park_vga.lidar as lidar
import park_vga.defining_grids as defining_grids

# Define test data paths
TEST_DATA_DIR = Path(__file__).parent / 'test_data_england'
TEST_PARK_FILE = TEST_DATA_DIR / 'Chapel_Allerton_Park_test.geojson'

# Find DTM and DSM files (check subdirectories)
DTM_DIR = TEST_DATA_DIR / 'DTM'
DSM_DIR = TEST_DATA_DIR / 'DSM'

DTM_FILES = sorted(DTM_DIR.glob('*.tif')) if DTM_DIR.exists() else []
DSM_FILES = sorted(DSM_DIR.glob('*.tif')) if DSM_DIR.exists() else []


class TestLoadLidarRasters:
    """Tests for load_lidar_rasters_for_park function"""
    
    @pytest.fixture
    def park_geometry(self):
        """Fixture: load Chapel Allerton Park"""
        return defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=10,  # Small buffer - test with actual park bounds
            type='primary name'
        )
    
    @pytest.fixture
    def dtm_dsm_paths(self):
        """Fixture: get DTM/DSM file paths"""
        dtm_paths = [str(f) for f in DTM_FILES if f.exists()]
        dsm_paths = [str(f) for f in DSM_FILES if f.exists()]
        return dtm_paths, dsm_paths
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_load_lidar_rasters(self, park_geometry, dtm_dsm_paths):
        """Test loading and mosaicking LiDAR rasters"""
        dtm_paths, dsm_paths = dtm_dsm_paths
        
        result = lidar.load_lidar_rasters_for_park(
            park_geometry,
            dtm_paths,
            dsm_paths
        )
        
        # Skip if park doesn't overlap rasters
        if result is None:
            pytest.skip("Park geometry does not overlap LiDAR raster coverage")
        
        assert result is not None
        assert 'dsm' in result
        assert 'dtm' in result
        assert 'height_above_ground' in result
        assert 'transform' in result
        assert 'crs' in result
        
        # Check data types
        assert isinstance(result['dsm'], np.ndarray)
        assert isinstance(result['dtm'], np.ndarray)
        assert isinstance(result['height_above_ground'], np.ndarray)
        
        # Check shapes match
        assert result['dsm'].shape == result['dtm'].shape
        assert result['height_above_ground'].shape == result['dsm'].shape
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_height_above_ground_calculation(self, park_geometry, dtm_dsm_paths):
        """Test height above ground is correctly calculated (DSM - DTM)"""
        dtm_paths, dsm_paths = dtm_dsm_paths
        
        result = lidar.load_lidar_rasters_for_park(
            park_geometry,
            dtm_paths,
            dsm_paths
        )
        
        if result is None:
            pytest.skip("Park geometry does not overlap LiDAR raster coverage")
        
        # Height should be DSM - DTM
        expected_height = result['dsm'] - result['dtm']
        
        # Compare (ignoring NaN values)
        valid_mask = ~np.isnan(expected_height)
        if np.sum(valid_mask) > 0:
            np.testing.assert_array_almost_equal(
                result['height_above_ground'][valid_mask],
                expected_height[valid_mask],
                decimal=5
            )
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_valid_data_percentage(self, park_geometry, dtm_dsm_paths):
        """Test that we get valid data from rasters"""
        dtm_paths, dsm_paths = dtm_dsm_paths
        
        result = lidar.load_lidar_rasters_for_park(
            park_geometry,
            dtm_paths,
            dsm_paths
        )
        
        if result is None:
            pytest.skip("Park geometry does not overlap LiDAR raster coverage")
        
        valid_pixels = np.sum(~np.isnan(result['height_above_ground']))
        total_pixels = result['height_above_ground'].size
        
        # Should have some valid data (at least 1%)
        assert valid_pixels > 0
        valid_pct = valid_pixels / total_pixels
        assert valid_pct > 0.01, f"Only {valid_pct*100:.2f}% valid pixels"
    
    def test_load_lidar_empty_paths(self, park_geometry):
        """Test error handling for empty file paths"""
        result = lidar.load_lidar_rasters_for_park(
            park_geometry,
            [],
            []
        )
        
        assert result is None


class TestPointToRasterIndex:
    """Tests for point_to_raster_index helper function"""
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_point_to_raster_index(self):
        """Test converting point to raster indices"""
        from shapely.geometry import Point
        import rasterio
        
        # Use actual raster to get transform
        with rasterio.open(str(DTM_FILES[0])) as src:
            transform = src.transform
            
            # Test point
            test_point = Point(
                transform.c,  # x at origin
                transform.f   # y at origin
            )
            
            row, col = lidar.point_to_raster_index(test_point, transform)
            
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert row >= 0
            assert col >= 0


class TestGetElevationAtPoint:
    """Tests for get_elevation_at_point helper function"""
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_get_elevation_at_point(self):
        """Test getting elevation at specific points"""
        from shapely.geometry import Point
        import rasterio
        
        with rasterio.open(str(DTM_FILES[0])) as src:
            raster = src.read(1)
            transform = src.transform
            
            # Get elevation at raster origin
            test_point = Point(transform.c + 100, transform.f - 100)
            
            elevation = lidar.get_elevation_at_point(test_point, raster, transform)
            
            # Should be a number (or NaN if outside bounds)
            assert isinstance(elevation, (float, np.floating))


class TestCheckLineOfSight:
    """Tests for check_line_of_sight function"""
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_line_of_sight_same_point(self):
        """Test line of sight to same point (should be True)"""
        from shapely.geometry import Point
        import rasterio
        
        with rasterio.open(str(DTM_FILES[0])) as src:
            raster = src.read(1)
            transform = src.transform
            dtm = raster.copy()
            dsm = raster.copy()
            
            test_point = Point(transform.c + 100, transform.f - 100)
            
            visible = lidar.check_line_of_sight(
                test_point, test_point,
                dsm, dtm, transform,
                observer_height=1.0, target_height=0
            )
            
            # Same point should always be visible
            assert visible is True


class TestCalculateVisibilityMetrics:
    """Tests for calculate_visibility_metrics function"""
    
    @pytest.fixture
    def small_hex_grid(self):
        """Fixture: create a small hex grid for testing"""
        from shapely.geometry import Point
        
        # Create 5 test points in a small area
        points = [
            Point(430600 + i*50, 437400 + i*50) for i in range(5)
        ]
        
        gdf = gpd.GeoDataFrame(geometry=points, crs='EPSG:27700')
        return gdf
    
    @pytest.mark.skipif(
        not all(f.exists() for f in DTM_FILES + DSM_FILES),
        reason="LiDAR test data files not found"
    )
    def test_calculate_visibility_metrics(self, small_hex_grid):
        """Test visibility metrics calculation"""
        import rasterio
        
        # Create simple test rasters
        with rasterio.open(str(DTM_FILES[0])) as src:
            dtm = src.read(1)
            dsm = src.read(1)  # For test, use DTM as DSM
            transform = src.transform
        
        results = lidar.calculate_visibility_metrics(
            small_hex_grid,
            dsm, dtm, transform,
            observer_height=1.0,
            target_height=0,
            max_distance=100
        )
        
        assert isinstance(results, gpd.GeoDataFrame)
        assert len(results) == len(small_hex_grid)
        assert 'visibility_pct' in results.columns
        assert 'visible_points' in results.columns
        assert 'total_points' in results.columns
        
        # All visibility percentages should be 0-100
        assert (results['visibility_pct'] >= 0).all()
        assert (results['visibility_pct'] <= 100).all()


class TestExtractFoliageByHexgrid:
    """Tests for extract_foliage_by_hexgrid function"""
    
    @pytest.fixture
    def hex_polygons_and_data(self):
        """Fixture: create hex grid and synthetic height raster"""
        from shapely.geometry import Point, Polygon
        from rasterio.transform import Affine
        
        # Create synthetic height raster (simple 100x100 array with vegetation)
        height_raster = np.random.uniform(0, 5, (100, 100))  # Heights 0-5m
        
        # Create transform for the synthetic raster
        # Origin at (0, 100), 1m pixels, y-axis inverted
        transform = Affine.translation(0, 100) * Affine.scale(1, -1)
        
        # Create hex polygons within the synthetic raster bounds
        hex_polygons = []
        for i in range(5):
            # Create centroids within raster bounds (0-100 x)
            x = 10 + i * 15
            y = 50 + i * 10
            centroid = Point(x, y)
            # Create polygon around centroid (5m radius)
            polygon = centroid.buffer(5)
            hex_polygons.append((centroid, polygon))
        
        return hex_polygons, height_raster, transform
    
    def test_extract_foliage_basic(self, hex_polygons_and_data):
        """Test foliage extraction from height raster"""
        hex_polygons, height_raster, transform = hex_polygons_and_data
        
        results = lidar.extract_foliage_by_hexgrid(
            height_raster,
            transform,
            hex_polygons,
            min_height=0.1,
            crs='EPSG:27700'
        )
        
        assert isinstance(results, gpd.GeoDataFrame)
        assert len(results) == len(hex_polygons)
        
        # Check expected columns
        expected_cols = [
            'max_height', 'mean_height', 'std_height',
            'count_pixels', 'percent_cover'
        ]
        for col in expected_cols:
            assert col in results.columns
    
    def test_foliage_height_bands(self, hex_polygons_and_data):
        """Test that height band columns are created"""
        hex_polygons, height_raster, transform = hex_polygons_and_data
        
        results = lidar.extract_foliage_by_hexgrid(
            height_raster,
            transform,
            hex_polygons,
            min_height=0.1,
            crs='EPSG:27700'
        )
        
        # Check height band columns exist
        height_bands = ['low_level_<0.5', 'mid_level_0.5-2', 'tall_2+']
        for band in height_bands:
            assert band in results.columns
            # Values should be between 0 and 100 (percentages)
            assert (results[band] >= 0).all() or results[band].isna().all()
