from data_downloader import OpenDataDownloader, GeometryFormatter
from data_helpers import RoadFeaturesCalculator, FeatureJoiner
from dotenv import load_dotenv
from geopandas import GeoDataFrame
import argparse
import geo
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
    ]
    loader = get_open_data_loader()
    print("[ 1/15] Loading centerline dataset...")
    streets = get_geodataframe(
        loader, "centerline", "the_geom", force_download=args.force_download
    )
    print("[ 2/15] Loading speed humps dataset...")
    speed_humps = get_geodataframe(
        loader, "speedhumps", "the_geom", force_download=args.force_download
    )
    print("[ 3/15] Loading trees dataset...")
    trees = get_geodataframe(
        loader, "trees", "the_geom", force_download=args.force_download
    )
    print("[ 4/15] Loading speed limits dataset...")
    speed_limits = get_geodataframe(
        loader, "speedlimits", "the_geom", force_download=args.force_download
    )
    print("[ 5/15] Loading traffic volumes dataset...")
    traffic_volumes = get_geodataframe(
        loader,
        "traffic_volumes",
        "wktgeom",
        crs=geo.NYC_EPSG,
        force_download=args.force_download,
    )
    print("[ 6/15] Loading crashes dataset...")
    crashes = get_geodataframe(loader, "crashes", force_download=args.force_download)
    joiner = FeatureJoiner(streets, column_selection=columns_from_centerline)
    print("[ 7/15] Joining speed humps to street information...")
    joiner.add_linear_feature(
        speed_humps, output_column="has_humps", install_date_column="date_insta"
    )
    print("[ 8/15] Joining speed limits to street information...")
    speed_limits["postvz_sl"] = speed_limits["postvz_sl"].astype(float)
    print("[ 9/15] Joining traffic volumes to street information...")
    traffic_volumes["vol"] = traffic_volumes["vol"].astype(float)
    print("[10/15] Joining crashes to street information...")
    crashes = RoadFeaturesCalculator(
        crashes, joiner.streets
    ).calculate_point_road_features(
        output_column="collision_rate",
        method="weighted",
        split_by_date=True,
        date_column="crash_date",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )
    print("[11/15] Joining trees to street information...")
    trees = RoadFeaturesCalculator(trees, joiner.streets).calculate_point_road_features(
        "n_trees", method="uniform", cols_to_aggregate_by=columns_to_aggregate_by
    )
    print("[12/15] Joining speed limits to street information...")
    speed_limits = RoadFeaturesCalculator(
        speed_limits, joiner.streets
    ).calculate_point_road_features(
        output_column="speed_limit",
        method="value",
        feature_value_column="postvz_sl",
        agg_function="max",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )
    print("[13/15] Joining traffic volumes to street information...")
    traffic_volumes = RoadFeaturesCalculator(
        traffic_volumes, joiner.streets
    ).calculate_point_road_features(
        "traffic_volumes",
        feature_value_column="vol",
        method="value",
        agg_function="mean",
        cols_to_aggregate_by=columns_to_aggregate_by,
    )
    print("[14/15] Consolidating...")
    joiner.add_multiple_features(
        [crashes, trees, speed_limits, traffic_volumes],
        index_cols=columns_to_aggregate_by,
    )
    joiner.streets["physicalid"] = joiner.streets["physicalid"].astype(int)
    joiner.streets["st_width"] = joiner.streets["st_width"].astype(float)
    joiner.streets["shape_leng"] = joiner.streets["shape_leng"].astype(float)
    joiner.streets["bike_lane"] = joiner.streets["bike_lane"].astype(str)
    print("[15/15] Saving to disk...")
    os.makedirs("../data", exist_ok=True)
    joiner.streets.drop(columns=["after", "until"]).to_pickle(
        "../data/final_dataset.pkl"
    )
