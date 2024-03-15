# Road safety

Erdos Institute Data Science Project on Road Safety

## Project outline

Analyse features of a road's design, and build a model to predict the safety of
the road, either using KSI metrics or average/ maximum vehicle speed as proxies
for safety & comfort.

## Proposed Data Features

TODO: Add data sources to the following features

- Lane width
- Number of lanes
  - Open Street Maps (OSM)
- Corridor width (related to building setback)
- Presence of trees
  - OSM
  - [Toronto's Open Data][TOD]
- Existence and style of a median (painted, vegetation, concrete)
- Presence and type of cycling infrastructure
  - OSM
- Presence and quality of sidewalks (number, width)
  - OSM (sidewalk width is usually not included)
- Parallel/ angle parking availability?
  - OSM (sometimes)
- Parking & bike lane ordering
- Traffic light / stop sign density (km^-1)
- Road surface type (asphalt, paving stones, gravel)
  - OSM
- Road quality (potholes, construction presence)
- Presence of streetlights
  - OSM
- Surrounding land use (business, commercial, industrial, residential, mixed)
  - OSM
- Population density of the surrounding area
- Traffic volume sorted by mode
- Presence of trucks/ weight restrictions
- Presence of dedicated bus lanes
  - OSM
- Presence of a bus route
  - OSM
- Speed restrictions
  - OSM

## Other points

Since many pedestrian deaths are occurring at nighttime, it may be worth the
effort to predict road speed / safety as a function of time of day (or
daytime/nighttime, on-peak/ off-peak)

## Notes on data sources

### OSM data

Data from open street maps is publicly maintained, so different areas will have
different degrees of completeness. The [Python module OSMnx][OSMPy] can be used to fetch
and visualize OSM data.

[TOD]: https://open.toronto.ca/dataset/street-tree-data/
[OSMPy]: https://pygis.io/docs/d_access_osm.htm
