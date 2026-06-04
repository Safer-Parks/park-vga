"""Integration test running workflow on Chapel Allerton Park"""

import pytest
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys
import tempfile
import shutil

from geopandas.testing import assert_geodataframe_equal
from pandas.testing import assert_frame_equal
import numpy as np


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import park_vga


# lidar_dtm = "test_data_england/DTM"
# lidar_dsm = "test_data_england/DSM"

# output_comparisons = ("test_outputs/compare_TESTINGWORKFLOW_foliage_results_park_leeds_945491c73c1c.geojson",
#                       "tests/test_outputs/compare_TESTINGWORKFLOW_visibility_results_park_leeds_945491c73c1c.geojson")

# boundaries_file = "test_data_england/Leeds_pp_or_g_cmb.geojson"

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / 'test_data_england'

lidar_dtm = str(DATA_DIR / 'DTM')
lidar_dsm = str(DATA_DIR / 'DSM')
boundaries_file = str(DATA_DIR / 'Leeds_pp_or_g_cmb.geojson')
output_comparisons = (
    str(TEST_DIR / 'test_outputs' / 'compare_TESTINGWORKFLOW_visibility_results_park_leeds_945491c73c1c.geojson'),  # [0]
    str(TEST_DIR / 'test_outputs' / 'compare_TESTINGWORKFLOW_foliage_results_park_leeds_945491c73c1c.geojson')      # [1]
)

TEST_PARK_NAME = "Chapel Allerton Park"


@pytest.fixture
def temp_output_dir():
    """Fixture: create temporary output directory that's cleaned up after test"""
    with tempfile.TemporaryDirectory(prefix='park_vga_test_') as temp_dir:
        yield Path(temp_dir)
    # Auto-cleaned up after yield


def test_full_workflow(temp_output_dir):
    """Test that the functions return data of the correct shape and that output files are created"""
    park_n = park_vga.workflow.find_park_n(TEST_PARK_NAME, boundaries_file)
    results = park_vga.workflow.workflow_eng(boundaries_file, park_n,
                                         lidar_dtm, lidar_dsm,
                                         temp_output_dir,
                                         return_results=True, save_results=True,
                                         park_id_for_file_name="1dda12df6406")
    print("Check that the type and len of output is correct")
    assert type(results) == tuple and len(results) == 2
    visibility_results = results[0]
    foliage_results = results[1]
    print("Check that the shape of the visibility and foliage output is correct")
    print(f"Results type: {type(results)}, length: {len(results)}")
    print(f"results[0] shape: {results[0].shape}")
    print(f"results[0] columns: {list(results[0].columns)}")
    print(f"results[1] shape: {results[1].shape}")
    print(f"results[1] columns: {list(results[1].columns)}")
    assert visibility_results.shape == (350, 4)
    assert foliage_results.shape == (350, 10)
    # Check that there are output files in output_path

    # Check that there are output files in temp_output_dir
    visibility_file = temp_output_dir / '1dda12df6406_visibility.geojson'
    foliage_file = temp_output_dir / '1dda12df6406_foliage.geojson'

    visibility_results_loaded = gpd.read_file(str(visibility_file))
    foliage_results_loaded = gpd.read_file(str(foliage_file))

    # # Compare loaded results with expected comparison files
    # expected_visibility = gpd.read_file(output_comparisons[0])
    # expected_foliage = gpd.read_file(output_comparisons[1])

    # assert_geodataframe_equal(visibility_results_loaded, expected_visibility, check_dtype=False)
    # assert_geodataframe_equal(foliage_results_loaded, expected_foliage, check_dtype=False)

    # Load expected results to compare
    print("Load example results to compare")
    expected_visibility = gpd.read_file(output_comparisons[0])
    expected_foliage = gpd.read_file(output_comparisons[1])

    # geopandas arrays - want values to be close within precision limits, and geometry to be equal
    print("Check that visibility matches")
    # assert_geodataframe_equal(visibility_results, expected_visibility, check_dtype=False)
    numeric_cols = visibility_results_loaded.select_dtypes(include=[np.number]).columns
    assert_frame_equal(
        visibility_results_loaded[numeric_cols],
        expected_visibility[numeric_cols],
        rtol=1e-5,    # 0.001% relative tolerance
        atol=1e-8     # absolute tolerance for small numbers
    )
    assert visibility_results_loaded.geometry.geom_equals_exact(
        expected_visibility.geometry, 
        tolerance=1.0  # 1 meter tolerance
    ).all(), "Visibility geometries don't match"

    print("Check that foliage matches")
    # assert_geodataframe_equal(foliage_results, expected_foliage, check_dtype=False)
    foliage_numeric_cols = foliage_results_loaded.select_dtypes(include=[np.number]).columns
    assert_frame_equal(
        foliage_results_loaded[foliage_numeric_cols],
        expected_foliage[foliage_numeric_cols],
        rtol=1e-5,
        atol=1e-8
    )

    assert foliage_results_loaded.geometry.geom_equals_exact(
        expected_foliage.geometry, 
        tolerance=1.0
    ).all(), "Foliage geometries don't match"



