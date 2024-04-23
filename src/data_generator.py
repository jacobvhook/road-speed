from data_downloader import OpenDataDownloader, GeometryFormatter
from data_helpers import RoadFeaturesCalculator, FeatureJoiner
from dotenv import load_dotenv
from geopandas import GeoDataFrame
from pandas import cut
import argparse
import data_sources
import geo
import numpy as np
import os


def get_open_data_loader() -> OpenDataDownloader:
    load_dotenv()
    nyc_token = os.getenv("NYC_OPENDATA_APPTOKEN")
    return OpenDataDownloader(nyc_token)


def get_geodataframe(
    loader: OpenDataDownloader,
    dataset: str,
    geometry_column: str | None = None,
    crs: str = geo.STD_EPSG,
    force_download=False,
) -> GeoDataFrame:
    df = loader.load_data(dataset=dataset, force_download=force_download)
    if geometry_column is None:
        return GeometryFormatter(df, crs=crs).from_lat_long()
    return GeometryFormatter(df, crs=crs).from_geometry_column(
        geometry_column=geometry_column
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--force-download",
        action="store_true",
        help="Forces the datasets to be downloaded",
    )
    args = parser.parse_args()
    if args.force_download:
        print("The datasets will be downloaded from NYC Open Data\n")

    columns_to_aggregate_by = ["physicalid", "after", "until"]
    columns_from_centerline = [
        "physicalid",
        "geometry",
        "bike_lane",
        "st_width",
        "shape_leng",
        "post_type",
        "pre_type",
        "st_name",
    ]

    dataframes = dict()
    loader = get_open_data_loader()

    for dataset, metadata in data_sources.DATASET_METADATA.items():
        print(f"Loading {dataset} dataset...")
        dataframes[dataset] = get_geodataframe(
            loader,
            dataset=dataset,
            geometry_column=metadata.get("geometry_column", None),
            crs=metadata.get("crs", geo.STD_EPSG),
            force_download=args.force_download,
        )

    joiner = FeatureJoiner(
        dataframes["centerline"], column_selection=columns_from_centerline
    )

    print("Joining speed humps data to streets dataset...")
    joiner.add_linear_feature(
        dataframes["speedhumps"],
        output_column="has_humps",
        install_date_column="date_insta",
    )
    dataframes["speedlimits"]["postvz_sl"] = dataframes["speedlimits"][
        "postvz_sl"
    ].astype(float)
    dataframes["traffic_volumes"]["vol"] = dataframes["traffic_volumes"]["vol"].astype(
        float
    )

    print("Processing crashes data using street information...")
    crashes = RoadFeaturesCalculator(
        dataframes["crashes"], joiner.streets
    ).calculate_point_road_features(
        output_column="collision_rate",
        method="weighted",
        split_by_date=True,
        date_column="crash_date",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )

    print("")
    trees = RoadFeaturesCalculator(
        dataframes["trees"], joiner.streets
    ).calculate_point_road_features(
        "n_trees", method="uniform", cols_to_aggregate_by=columns_to_aggregate_by
    )

    print("Processing speed limits data using street information...")
    speed_limits = RoadFeaturesCalculator(
        dataframes["speedlimits"], joiner.streets
    ).calculate_point_road_features(
        output_column="speed_limit",
        method="value",
        feature_value_column="postvz_sl",
        agg_function="max",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )

    print("Processing traffic volumes data using street information...")
    traffic_volumes = RoadFeaturesCalculator(
        dataframes["traffic_volumes"], joiner.streets
    ).calculate_point_road_features(
        "traffic_volume",
        feature_value_column="vol",
        method="value",
        agg_function="mean",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )

    print("Processing parking meters data using street information...")
    parking_meters = RoadFeaturesCalculator(
        dataframes["parking_meters"], joiner.streets
    ).calculate_point_road_features(
        "n_parking_meters",
        method="uniform",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )

    print("Joining all features...")
    joiner.add_multiple_features(
        [crashes, trees, speed_limits, traffic_volumes, parking_meters],
        index_cols=columns_to_aggregate_by,
    )

    joiner.streets["physicalid"] = joiner.streets["physicalid"].astype(int)
    joiner.streets["st_width"] = joiner.streets["st_width"].astype(float)
    joiner.streets["shape_leng"] = joiner.streets["shape_leng"].astype(float)
    joiner.streets["bike_lane"] = joiner.streets["bike_lane"].astype(str)
    joiner.streets["collision_rate_per_length"] = (
        joiner.streets["collision_rate"] / joiner.streets["shape_leng"]
    )

    percentiles = [50, 75, 90, 95, 99]
    labels = ["bottom_50", "top_50", "top_25", "top_10", "top_5", "top_1"]
    percentile_bins = (
        [-np.inf]
        + [
            np.percentile(joiner.streets["collision_rate_per_length"].values, q=p)
            for p in percentiles
        ]
        + [np.inf]
    )
    joiner.streets["percentile"] = cut(
        joiner.streets["collision_rate_per_length"], percentile_bins, labels=labels
    )

    print("Saving to disk...")
    os.makedirs("../data", exist_ok=True)
    joiner.streets.drop(columns=["after", "until"]).to_pickle(
        "../data/final_dataset.pkl"
    )
