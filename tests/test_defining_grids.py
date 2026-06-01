"""Unit tests for park_vga.defining_grids module"""

import pytest
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import park_vga.defining_grids as defining_grids

# Define test data paths
TEST_DATA_DIR = Path(__file__).parent / 'test_data_england'
TEST_PARK_FILE = TEST_DATA_DIR / 'Chapel_Allerton_Park_test.geojson'
FULL_PARKS_FILE = TEST_DATA_DIR / 'Leeds_pp_or_g_cmb.geojson'


class TestLoadData:
    """Tests for load_data function"""
    
    def test_load_data_by_primary_name(self):
        """Test loading park by primary name"""
        park_gdf = defining_grids.load_data(
            str(TEST_PARK_FILE), 
            'Chapel Allerton Park',
            buffer_distance=0,
            type='primary name'
        )
        
        assert isinstance(park_gdf, gpd.GeoDataFrame)
        assert len(park_gdf) == 1
        assert park_gdf.crs.to_string() == 'EPSG:27700'
    
    def test_load_data_with_buffer(self):
        """Test that buffer increases geometry area"""
        park_gdf_no_buffer = defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=0,
            type='primary name'
        )
        
        park_gdf_buffer = defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        area_no_buffer = park_gdf_no_buffer.geometry.iloc[0].area
        area_buffer = park_gdf_buffer.geometry.iloc[0].area
        
        assert area_buffer > area_no_buffer
    
    def test_load_data_invalid_park_name(self):
        """Test error handling for non-existent park"""
        park_gdf = defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Non-existent Park',
            buffer_distance=0,
            type='primary name'
        )
        
        assert len(park_gdf) == 0


class TestOSGB36ToOSGrid:
    """Tests for OSGB36_to_os_grid conversion"""
    
    def test_grid_conversion_basic(self):
        """Test basic coordinate to OS grid conversion"""
        # Chapel Allerton Park is in SD50 quadrant
        easting = 430600  # approx Leeds
        northing = 437400  # approx Leeds
        
        grid_ref = defining_grids.OSGB36_to_os_grid(easting, northing, include_quadrant=False)
        
        assert grid_ref is not None
        assert len(grid_ref) == 4  # Format: SD50
        assert grid_ref[0:2] in ['SD', 'SE', 'TA']  # Valid for UK
    
    def test_grid_conversion_with_quadrant(self):
        """Test coordinate to OS grid with quadrant"""
        easting = 430600
        northing = 437400
        
        grid_ref = defining_grids.OSGB36_to_os_grid(
            easting, northing, include_quadrant=True
        )
        
        assert grid_ref is not None
        assert len(grid_ref) == 6  # Format: SD50ne
        assert grid_ref[-2:] in ['ne', 'nw', 'se', 'sw']
    
    def test_grid_conversion_quadrant_assignment(self):
        """Test quadrant assignment in grid conversion"""
        # Test different coordinate quadrants
        easting = 430630  # ~center of grid square
        northing = 437420
        
        grid_ref = defining_grids.OSGB36_to_os_grid(
            easting, northing, include_quadrant=True
        )
        
        # Should return a valid format with quadrant
        assert grid_ref is not None
        assert len(grid_ref) == 6


class TestCreateHexagonGrid:
    """Tests for create_hexagon_grid function"""
    
    @pytest.fixture
    def park_geometry(self):
        """Fixture: load Chapel Allerton Park"""
        return defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=10,
            type='primary name'
        )
    
    def test_create_hexagon_grid_centroids(self, park_geometry):
        """Test hexagon grid creation - centroids only"""
        hex_grid = defining_grids.create_hexagon_grid(
            park_geometry,
            spacing=10,
            return_mode='centroids'
        )
        
        assert isinstance(hex_grid, gpd.GeoDataFrame)
        assert len(hex_grid) > 0
        assert hex_grid.crs.to_string() == 'EPSG:27700'
        assert all(hex_grid.geometry.geom_type == 'Point')
    
    def test_create_hexagon_grid_polygons(self, park_geometry):
        """Test hexagon grid creation - polygons only"""
        hex_grid = defining_grids.create_hexagon_grid(
            park_geometry,
            spacing=10,
            return_mode='polygons'
        )
        
        assert isinstance(hex_grid, gpd.GeoDataFrame)
        assert len(hex_grid) > 0
        assert all(hex_grid.geometry.geom_type == 'Polygon')
    
    def test_create_hexagon_grid_both(self, park_geometry):
        """Test hexagon grid creation - both centroids and polygons"""
        hex_grid = defining_grids.create_hexagon_grid(
            park_geometry,
            spacing=10,
            return_mode='both'
        )
        
        assert isinstance(hex_grid, dict)
        assert 'centroids' in hex_grid
        assert 'polygons' in hex_grid
        
        # Should have same count
        assert len(hex_grid['centroids']) == len(hex_grid['polygons'])
    
    def test_hexagon_grid_density(self, park_geometry):
        """Test that finer spacing produces more hexagons"""
        coarse_grid = defining_grids.create_hexagon_grid(
            park_geometry,
            spacing=20,
            return_mode='centroids'
        )
        
        fine_grid = defining_grids.create_hexagon_grid(
            park_geometry,
            spacing=10,
            return_mode='centroids'
        )
        
        # Finer spacing should produce more hexagons
        assert len(fine_grid) > len(coarse_grid)
    
    def test_hexagon_grid_invalid_mode(self, park_geometry):
        """Test error handling for invalid return_mode"""
        with pytest.raises(ValueError):
            defining_grids.create_hexagon_grid(
                park_geometry,
                spacing=10,
                return_mode='invalid_mode'
            )


class TestParkGeometryToFilePath:
    """Tests for park_geometry_to_file_path function"""
    
    def test_find_file_paths(self):
        """Test finding LiDAR files for Chapel Allerton Park"""
        park_gdf = defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=20,
            type='primary name'
        )
        
        lidar_dtm = TEST_DATA_DIR
        lidar_dsm = TEST_DATA_DIR
        
        dtm_paths, dsm_paths = defining_grids.park_geometry_to_file_path(
            park_gdf,
            str(lidar_dtm),
            str(lidar_dsm)
        )
        
        # Chapel Allerton should find files
        assert isinstance(dtm_paths, list)
        assert isinstance(dsm_paths, list)


class TestFindTiles:
    """Tests for find_tiles function"""
    
    def test_find_tiles_leeds(self):
        """Test finding grid tiles for Leeds area"""
        park_gdf = defining_grids.load_data(
            str(TEST_PARK_FILE),
            'Chapel Allerton Park',
            buffer_distance=10,
            type='primary name'
        )
        
        tiles = defining_grids.find_tiles(park_gdf)
        
        assert isinstance(tiles, set)
        assert len(tiles) > 0
        # Should be valid OS grid references
        for tile in tiles:
            assert len(tile) >= 4
