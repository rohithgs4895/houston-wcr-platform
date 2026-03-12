"""
Spatial methodology summary card for the Houston WCR Intelligence Platform.
Generates the GIS operations panel shown in the sidebar.
"""


METHODOLOGY_TEXT = """
### Spatial Methodology

**Coordinate Reference Systems**
- Analysis CRS: `EPSG:2278` — Texas State Plane South Central (US feet). All distance and area calculations performed in this projected CRS for accuracy.
- Display CRS: `EPSG:4326` — WGS84. All map rendering and data storage use geographic coordinates.

**Operations in Use**
- **Voronoi Service Zone Derivation** — Each treatment plant's service area is the set of all locations closer to that plant than any other. Built using Shapely's `voronoi_diagram()` clipped to the Houston city boundary.
- **Spatial Join: Applications → Zones** — `gpd.sjoin()` with `predicate="within"` assigns each WCR application to its treatment plant zone in O(n log n) time.
- **Buffer Analysis** — Stressed zone boundaries are buffered by 2,640 ft (0.5 miles) in EPSG:2278, then applications falling within the buffer are flagged as "capacity-adjacent risk."
- **Kernel Density Estimation** — `numpy.histogram2d()` bins applications onto a 0.02-degree grid over Houston's bounding box, producing density values for heatmap rendering.
- **Nearest Plant Distance** — Point-to-point distances from application locations to all treatment plants calculated in EPSG:2278 (feet), returning the nearest plant and distance.
- **Council District Aggregation** — Spatial join of applications to council district polygons; aggregate SLA compliance, application counts, and total fees by district.

**Data Sources**
- Houston Public Works WCR Applications (simulated, seed=42)
- Houston Water treatment plant locations (real coordinates, public record)
- City of Houston council district boundaries (approximate)
- Texas state holidays: `holidays.Texas()` library
"""


def render_methodology_expander():
    """Return the methodology content as a string for st.expander."""
    return METHODOLOGY_TEXT


SPATIAL_OPERATIONS_LIST = [
    ("Voronoi service zone derivation", "Service area polygons from plant locations"),
    ("Spatial join: applications → zones", "Assigns WCR apps to treatment plant zones"),
    ("Buffer analysis: 0.5 mi capacity alerts", "Flags apps near stressed zone boundaries"),
    ("Kernel density estimation (heatmap)", "Application clustering and hotspot detection"),
    ("Coordinate system: EPSG:2278 (TX State Plane)", "Accurate distance/area calculations"),
    ("Nearest plant distance", "Feet-accurate plant proximity via projected CRS"),
    ("Council district aggregation", "Spatial join to district polygons for stats"),
]
