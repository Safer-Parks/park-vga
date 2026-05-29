# Moving scripts from notebooks into modules to allow to scaling-up of the work

In this series of (numbered) notebooks, I'm importing and testing each step of the process, moving from in-noptebook analysis, to a workflow based on imported functions, and eventually a hands-off scriupt that can be run in bulk.

Each notebook builds iteratively on the last, so there is repetition: I didn't want to save out intermediary files that wouldn't end up being used in the real scaled-up workflow, so earlier steps are "re-done" in later notebooks, but I wanted to keep the work-in-progress visible.

You can see the overall workflow [in this notebook](example_workflow.ipynb).

Workflow process (scaled-up):

1. Load park boundary, using unique id
2. Parse Lidar file paths from coordinates
3. Check that files exist
4. Generate hex grid for visibility and foliage analysis
5. Load in Lidar data
6. Calculate visibility analysis
7. Trim the visibility analysis to hexagons that intersect the park boundary
8. Calculate foliage stats
9. Trim the foliage stats to hexagons that intersect the park boundary - 5m buffer (cutting off buildings etc. near boundary)
10. Export datasets as geojson in EPSG:4326 ready for presentation online.


Timing

310 s for Woodhouse Moor/2369 points -> 7.64 points per second; geometry more regular so more points within 100m distance

191 s for smaller park - 2207 point -> 11.55 points per second; geometry is very irregular so fewer points wtihin 100m distance
