"""Integration tests for park_vga workflow

These tests verify the complete workflow end-to-end with realistic data.
"""

import pytest
import geopandas as gpd
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import park_vga

# Define test data paths
TEST_DATA_DIR = Path(__file__).parent / 'test_data_england'
TEST_PARK_FILE = TEST_DATA_DIR / 'Chapel_Allerton_Park_test.geojson'

# Find DTM and DSM files (check subdirectories)
DTM_DIR = TEST_DATA_DIR / 'DTM'
DSM_DIR = TEST_DATA_DIR / 'DSM'

DTM_FILES = sorted(DTM_DIR.glob('*.tif')) if DTM_DIR.exists() else []
DSM_FILES = sorted(DSM_DIR.glob('*.tif')) if DSM_DIR.exists() else []
OUTPUT_DIR = TEST_DATA_DIR / 'integration_test_output'


class TestWorkflowHelperFunctions:
    """Tests for workflow helper functions"""
    
    def test_find_park_n(self):
        """Test finding park index by name"""
        # First, we need to create a simple test GeoJSON with known properties
        test_gdf = gpd.read_file(str(TEST_PARK_FILE))
        
        # Create a temporary GeoJSON for testing
        test_file = TEST_DATA_DIR / 'temp_test_parks.geojson'
        test_gdf.to_file(test_file)
        
        try:
            park_n = park_vga.workflow.find_park_n(
                'Chapel Allerton Park',
                str(test_file)
            )
            
            assert isinstance(park_n, int)
            assert park_n >= 0
        finally:
            if test_file.exists():
                test_file.unlink()
    
    def test_find_park_id(self):
        """Test finding park ID by index"""
        # Use the full Leeds dataset which has id property
        from pathlib import Path
        full_parks_file = TEST_DATA_DIR / 'Leeds_pp_or_g_cmb.geojson'
        
        if not full_parks_file.exists():
            pytest.skip("Full parks dataset not available")
        
        park_id = park_vga.workflow.find_park_id(0, str(full_parks_file))
        
        assert isinstance(park_id, str)
        assert len(park_id) > 0


class TestLoadDataIntegration:
    """Integration tests for data loading"""
    
    def test_load_park_data(self):
        """Test loading park data"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        assert isinstance(park_gdf, gpd.GeoDataFrame)
        assert len(park_gdf) == 1
        assert park_gdf.crs.to_string() == 'EPSG:27700'


class TestHexagonGridIntegration:
    """Integration tests for hexagon grid creation"""
    
    def test_create_grid_for_park(self):
        """Test creating hexagon grid for Chapel Allerton Park"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        hex_grid = park_vga.create_hexagon_grid(
            park_gdf,
            spacing=10,
            return_mode='both'
        )
        
        assert 'centroids' in hex_grid
        assert 'polygons' in hex_grid
        
        # Expected ~400 hexagons based on area (~400-500 hex count)
        assert len(hex_grid['centroids']) > 100
        assert len(hex_grid['centroids']) < 1000


@pytest.mark.skipif(
    not all(f.exists() for f in DTM_FILES + DSM_FILES),
    reason="LiDAR test data files not found"
)
class TestLidarLoadingIntegration:
    """Integration tests for LiDAR data loading"""
    
    def test_load_lidar_for_chapel_allerton(self):
        """Test loading LiDAR data for Chapel Allerton Park"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=10,
            type='primary name'
        )
        
        dtm_paths = [str(f) for f in DTM_FILES if f.exists()]
        dsm_paths = [str(f) for f in DSM_FILES if f.exists()]
        
        if not dtm_paths or not dsm_paths:
            pytest.skip("LiDAR files not available")
        
        lidar_data = park_vga.load_lidar_rasters_for_park(
            park_gdf,
            dtm_paths,
            dsm_paths
        )
        
        # Skip if park doesn't overlap rasters
        if lidar_data is None:
            pytest.skip("Park geometry does not overlap LiDAR raster coverage")
        
        assert lidar_data is not None
        assert 'dsm' in lidar_data
        assert 'dtm' in lidar_data
        assert 'height_above_ground' in lidar_data


@pytest.mark.skipif(
    not all(f.exists() for f in DTM_FILES + DSM_FILES),
    reason="LiDAR test data files not found"
)
class TestVisibilityCalculation:
    """Integration tests for visibility calculations"""
    
    def test_calculate_visibility_for_chapel_allerton(self):
        """Test visibility calculation for Chapel Allerton Park"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=50,
            type='primary name'
        )
        
        hex_grid = park_vga.create_hexagon_grid(
            park_gdf,
            spacing=20,  # Coarser grid for faster testing
            return_mode='centroids'
        )
        
        dtm_paths = [str(f) for f in DTM_FILES if f.exists()]
        dsm_paths = [str(f) for f in DSM_FILES if f.exists()]
        
        if not dtm_paths or not dsm_paths:
            pytest.skip("LiDAR files not available")
        
        lidar_data = park_vga.load_lidar_rasters_for_park(
            park_gdf,
            dtm_paths,
            dsm_paths
        )
        
        if lidar_data is None:
            pytest.skip("Could not load LiDAR data")
        
        # Use smaller max_distance for faster testing
        visibility_results = park_vga.calculate_visibility_metrics(
            hex_grid,
            lidar_data['dsm'],
            lidar_data['dtm'],
            lidar_data['transform'],
            observer_height=1.0,
            target_height=0,
            max_distance=50  # Smaller for testing
        )
        
        assert isinstance(visibility_results, gpd.GeoDataFrame)
        assert len(visibility_results) == len(hex_grid)
        assert 'visibility_pct' in visibility_results.columns


@pytest.mark.skipif(
    not all(f.exists() for f in DTM_FILES + DSM_FILES),
    reason="LiDAR test data files not found"
)
class TestFoliageExtraction:
    """Integration tests for foliage extraction"""
    
    def test_extract_foliage_for_chapel_allerton(self):
        """Test foliage extraction for Chapel Allerton Park"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=50,
            type='primary name'
        )
        
        hex_grid = park_vga.create_hexagon_grid(
            park_gdf,
            spacing=20,  # Coarser for faster testing
            return_mode='both'
        )
        
        dtm_paths = [str(f) for f in DTM_FILES if f.exists()]
        dsm_paths = [str(f) for f in DSM_FILES if f.exists()]
        
        if not dtm_paths or not dsm_paths:
            pytest.skip("LiDAR files not available")
        
        lidar_data = park_vga.load_lidar_rasters_for_park(
            park_gdf,
            dtm_paths,
            dsm_paths
        )
        
        if lidar_data is None:
            pytest.skip("Could not load LiDAR data")
        
        hex_polygons = list(zip(
            hex_grid['centroids'].geometry,
            hex_grid['polygons'].geometry
        ))
        
        foliage_results = park_vga.extract_foliage_by_hexgrid(
            lidar_data['height_above_ground'],
            lidar_data['transform'],
            hex_polygons,
            min_height=0.1,
            crs='EPSG:27700'
        )
        
        assert isinstance(foliage_results, gpd.GeoDataFrame)
        assert len(foliage_results) == len(hex_polygons)
        
        # Check for expected columns
        expected_cols = ['max_height', 'mean_height', 'low_level_<0.5']
        for col in expected_cols:
            assert col in foliage_results.columns


class TestWorkflowOutputs:
    """Tests for workflow outputs and data validation"""
    
    def test_hexagon_grid_coverage(self):
        """Test that hexagon grid provides reasonable coverage"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        hex_grid = park_vga.create_hexagon_grid(
            park_gdf,
            spacing=10,
            return_mode='both'
        )
        
        # All centroids should be within park bounds (with buffer)
        park_bounds = park_gdf.total_bounds
        centroid_bounds = hex_grid['centroids'].total_bounds
        
        # Centroids should be roughly within park
        assert centroid_bounds[0] >= park_bounds[0] - 100
        assert centroid_bounds[1] >= park_bounds[1] - 100
        assert centroid_bounds[2] <= park_bounds[2] + 100
        assert centroid_bounds[3] <= park_bounds[3] + 100
    
    def test_crs_consistency(self):
        """Test that CRS is consistent throughout workflow"""
        park_gdf = park_vga.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        hex_grid = park_vga.create_hexagon_grid(
            park_gdf,
            spacing=10,
            return_mode='both'
        )
        
        # All should use EPSG:27700
        assert park_gdf.crs.to_string() == 'EPSG:27700'
        assert hex_grid['centroids'].crs.to_string() == 'EPSG:27700'
        assert hex_grid['polygons'].crs.to_string() == 'EPSG:27700'
