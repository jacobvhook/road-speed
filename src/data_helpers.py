import geopandas as gpd
import pandas as pd
from shapely import is_empty
import geo
from pathlib import Path
from numpy import datetime64, timedelta64


class RoadFeaturesCalculator:

    def __init__(self, features_df: gpd.GeoDataFrame, streets_df: gpd.GeoDataFrame):
        self.features = features_df
        self.streets = streets_df

    def __get_week_span(self, date_column: str) -> float:
        crash_dates = self.features[date_column].apply(datetime64)
        return (crash_dates.max() - crash_dates.min()) / timedelta64(1, "W")

    def __get_intersection_weights(
        self,
        buffer: int = 30,
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> gpd.GeoDataFrame:
        if intersection_data_path.exists():
            intersections = pd.read_pickle(intersection_data_path)
            return gpd.GeoDataFrame(
                intersections, geometry=intersections.geometry, crs=geo.NYC_EPSG
            )
        intersections = gpd.GeoDataFrame(
            geometry=self.streets["geometry"].boundary.buffer(buffer), crs=geo.NYC_EPSG
        )

        # Dissolve and explode to get the connected components
        intersections = (
            intersections[~is_empty(intersections)]
            .dissolve()  # Converts the whole GeoSeries into a single object
            .explode(index_parts=False)  # Separates all the subgeometries
            .sjoin(self.streets, how="left")
            .groupby(by="geometry", as_index=False)["physicalid"]
            .count()
        )
        intersections["weight"] = 1.0 / intersections["physicalid"]

        intersections = gpd.GeoDataFrame(
            intersections[["geometry", "weight"]],
            geometry=intersections.geometry,
            crs=geo.NYC_EPSG,
        )

        intersections.to_pickle(intersection_data_path)
        return intersections

    def calculate_road_features(
        self,
        id_column: str,
        feature_name: str,
        date_column: str | None = None,
        method: str = "weighted",
        buffer: int = 30,
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> pd.DataFrame:
        if method == "weighted":
            intersection_weights = self.__get_intersection_weights(
                buffer=buffer, intersection_data_path=intersection_data_path
            )
            weighted_features = self.features.sjoin(
                intersection_weights, how="left", predicate="within"
            )[[id_column, "geometry", "weight"]]
        elif method == "uniform":
            weighted_features = self.features[[id_column, "geometry"]].copy()
            weighted_features["weight"] = 1.0
        else:
            raise NotImplementedError(f"Method {method} has not been implemented.")
        weighted_features["weight"] = weighted_features["weight"].fillna(value=1.0)

        buffered_streets = self.streets.copy()
        buffered_streets["geometry"] = buffered_streets["geometry"].buffer(buffer)

        feature_aggregation = (
            buffered_streets.sjoin(weighted_features, how="left")
            # TODO: decide what columns we want to keep.
            # Perhaps we want to pass them as arguments?
            .groupby(by="physicalid", as_index=False)["weight"]
            .sum()
            .rename(columns={"weight": feature_name})
        )
        if date_column is not None:
            week_span = self.__get_week_span(date_column)
            feature_aggregation[feature_name] = (
                feature_aggregation[feature_name] / week_span
            )
        return feature_aggregation
