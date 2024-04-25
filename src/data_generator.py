import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from geopandas import GeoDataFrame
from sklearn.model_selection import train_test_split

import data_sources
import geo
from data_downloader import GeometryFormatter, OpenDataDownloader
from data_helpers import FeatureJoiner, RoadFeaturesCalculator

DATA_FOLDER = Path("../data")


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

    print("Establishing streets dataset...")
    joiner = FeatureJoiner(
        streets=dataframes["centerline"], column_selection=columns_from_centerline
    )
    joiner.streets["physicalid"] = joiner.streets["physicalid"].astype(int)
    joiner.streets["st_width"] = joiner.streets["st_width"].astype(float)
    joiner.streets["shape_leng"] = joiner.streets["shape_leng"].astype(float)
    joiner.streets.rename(columns={"bike_lane": "has_bike_lane"}, inplace=True)
    joiner.streets["has_bike_lane"] = joiner.streets["has_bike_lane"].apply(pd.notna)

    joiner.streets["is_av"] = (
        (joiner.streets["post_type"].isin(["AVE", "BLVD"]))
        | (joiner.streets["pre_type"] == "AVE")
        | (joiner.streets["st_name"].isin(["BROADWAY", "BOWERY"]))
    )
    joiner.streets["is_st"] = joiner.streets["post_type"] == "ST"
    joiner.streets["is_rd"] = joiner.streets["post_type"].isin(["RD", "ROAD"])
    joiner.streets.drop(
        columns=[
            "post_type",
            "pre_type",
            "st_name",
        ],
        inplace=True,
    )

    print("Joining speed humps data to streets dataset...")
    joiner.add_linear_feature(
        dataframes["speedhumps"],
        output_column="has_humps",
        install_date_column="date_insta",
    )
    del dataframes["speedhumps"]

    print("Processing crashes data using street information...")
    crashes = RoadFeaturesCalculator(
        dataframes["crashes"], joiner.streets
    ).calculate_point_road_features(
        output_column="collision_rate",
        method="uniform",
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
    dataframes["speedlimits"]["postvz_sl"] = dataframes["speedlimits"][
        "postvz_sl"
    ].astype(float)
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
    dataframes["traffic_volumes"]["vol"] = dataframes["traffic_volumes"]["vol"].astype(
        float
    )
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

    print("Recasting datatypes...")
    joiner.streets["collision_rate_per_length"] = (
        joiner.streets["collision_rate"] / joiner.streets["shape_leng"]
    )

    joiner.streets.drop(columns=["after", "until"], inplace=True)

    joiner.streets["has_volume_meas"] = ~joiner.streets["traffic_volume"].isna()
    joiner.streets["has_parking_meters"] = joiner.streets["n_parking_meters"] > 0

    print("Imputing data...")
    joiner.streets.dropna(subset="st_width", inplace=True)
    joiner.streets = joiner.streets[joiner.streets["st_width"] > 0].copy()
    joiner.streets["speed_limit"] = joiner.streets["speed_limit"].fillna(value=25)

    print("Generating train/test split...")
    collisions_train, collisions_test = train_test_split(
        joiner.streets,
        test_size=0.2,
        random_state=316_203_477,
    )

    print("Saving to disk...")
    os.makedirs(DATA_FOLDER, exist_ok=True)
    collisions_train.to_pickle(DATA_FOLDER / "final_dataset_train.pkl")
    collisions_test.to_pickle(DATA_FOLDER / "final_dataset_test.pkl")
    joiner.streets.to_pickle(DATA_FOLDER / "final_dataset.pkl")
