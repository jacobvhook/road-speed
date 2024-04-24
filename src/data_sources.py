import geo

DATASET_METADATA: dict[str, str] = {
    "crashes": {
        "endpoint": "h9gi-nx95",
    },
    "centerline": {
        "geometry_column": "the_geom",
        "endpoint": "8rma-cm9c",
    },
    "speedlimits": {
        "geometry_column": "the_geom",
        "endpoint": "978y-cak4",
    },
    "speedhumps": {
        "geometry_column": "the_geom",
        "endpoint": "yjra-caqx",
    },
    "trees": {
        "geometry_column": "the_geom",
        "endpoint": "5rq2-4hqu",
    },
    "traffic_volumes": {
        "geometry_column": "wktgeom",
        "endpoint": "7ym2-wayt",
        "crs": geo.NYC_EPSG,
    },
    "parking_meters": {
        "geometry_column": "location",
        "endpoint": "693u-uax6",
    },
    "leading_pedestrian_intervals": {
        "geometry_column": "the_geom",
        "endpoint": "xc4v-ntf4",
    },
}
