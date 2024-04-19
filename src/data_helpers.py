from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from numpy import datetime64, timedelta64
from shapely import is_empty

import geo


class RoadFeaturesCalculator:

    def __init__(self, features: gpd.GeoDataFrame, streets: gpd.GeoDataFrame):
        self.features = features
        self.streets = streets

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

    def calculate_linear_road_features(
        self,
        output_column: str,
        install_date_column: str | None = None,
        predicate: str = "contains",
        buffer: float = 30,
    ):
        self.features[install_date_column] = self.features[install_date_column].apply(
            datetime64
        )
        if predicate == "contains":
            buffered_features = self.features.copy()
            buffered_features["geometry"] = buffered_features["geometry"].buffer(buffer)
            features_aggregate = (
                buffered_features.sjoin(self.streets, how="right", predicate=predicate)
                .groupby(by="physicalid", as_index=False)[install_date_column]
                .max()
                .rename(columns={install_date_column: "after"})
            )
        else:
            raise NotImplementedError(
                f"Predicate {predicate} is not implemented for calculate_linear_road_features."
            )
        features_aggregate[output_column] = ~features_aggregate["after"].isna()
        features_aggregate["until"] = np.nan
        features_old = features_aggregate[features_aggregate[output_column]].copy()
        features_old[output_column] = False
        features_old.rename(columns={"after": "until", "until": "after"}, inplace=True)
        return pd.concat([features_aggregate, features_old])

    def calculate_point_road_features(
        self,
        aggregate_column: str,
        date_column: str | None = None,
        installation_date_column: str | None = None,
        method: str | None = None,
        buffer: int = 30,
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> pd.DataFrame:
        if method == "weighted":
            intersection_weights = self.__get_intersection_weights(
                buffer=buffer, intersection_data_path=intersection_data_path
            )
            weighted_features = self.features.sjoin(
                intersection_weights, how="left", predicate="within"
            )[["geometry", "weight"]].fillna(value=1.0)
        elif method == "uniform":
            weighted_features = self.features[["geometry"]].copy()
            weighted_features["weight"] = 1.0
        else:
            raise NotImplementedError(f"Method {method} has not been implemented.")

        buffered_streets = self.streets.copy()
        buffered_streets["geometry"] = buffered_streets["geometry"].buffer(buffer)

        feature_aggregation = (
            weighted_features.sjoin(buffered_streets, how="right", predicate="within")
            # TODO: decide what columns we want to keep.
            # Perhaps we want to pass them as arguments?
            .groupby(by="physicalid", as_index=False)["weight"]
            .sum()
            .rename(columns={"weight": aggregate_column})
        )
        if date_column is not None:
            week_span = self.__get_week_span(date_column)
            feature_aggregation[aggregate_column] = (
                feature_aggregation[aggregate_column] / week_span
            )
        return feature_aggregation


class FeatureJoiner:

    def __init__(self, features: gpd.GeoDataFrame, streets: gpd.GeoDataFrame):
        self.features = features
        self.streets = streets

    def add_data_with_installation_date(
        self,
        date_column: str,
    ):
        self.features[date_column] = self.features[date_column].apply(datetime64)
        # self.streets.pass()

    def add_data_with_time_data(
        self,
    ):
        pass

    def add_data(self):
        self.streets = self.streets.join(self.features, on="physicalid", how="left")


# centerline <- speedhumps <- crashes, trees, ...
