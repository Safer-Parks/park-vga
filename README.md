# park-vga

Python code and workflow for Visibility Graph Analysis (VGA) of public parks

## Approach

This Python package recreates work done manually in QGIS to integrate visibility analysis across park areas with tree covereage/vegetation etc.

The two case study parks were Peel Park, Bradford, and Woodhouse Moor (Hyde Park), Leeds.

The aim is not to perfectly recreate the results of detailed single-park analysis, but rather to return good-quality, rapid analysis that can be done at scale across a region/nationally.

### QGIS Process

A range of different visibility analysis approaches were used in QGIS, recorded here.

#### QGIS Visibility Analysis plugin

- Using DEFRA LiDAR Composite First Return DSM
- Merged raster from two dsms covering the region
- Testing both 10 and 20 m grids
- Binary viewshed, 1 m observer and 0 m target height
- The resulting viewshed is then multiplied by ((DSM - DTM) <= 0), removing treetops as "highly visible locations" - see [output tiff](park-vga/qgis_work/final_diff_20m.tif)

## Important resources

- [How to run visibility analysis in QGIS](https://www.helenmakesmaps.com/post/how-to-run-visibility-analysis-in-qgis)

## Relevant papers

- [A critical evaluation of visibility analysis approaches for visual impact assessment (VIA) in the context of environmental impact assessment (EIA)](https://www.sciencedirect.com/science/article/pii/S0195925522002281)
    - Type of DEM important: DSM most accurate, over DTM
    - DEM resolution not overly important
    - Line of sight most accurate, over viewshed or cumalitive viewshed

## Python project

### Setup

1. Install pixi: https://pixi.shsß
2. Initialize the environment:
   ```bashß
   pixi install
   ```
3. Activate the environment:
   ```bash
   pixi shell
   ```

