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
        return pd.concat([features_aggregate, features_old]).fillna(
            {"until": datetime64("2024-04"), "after": datetime64("2012-07")}
        )

    def calculate_point_road_features(
        self,
        output_column: str,
        feature_value_column: str | None = None,
        date_column: str | None = None,
        method: str | None = None,
        buffer: int = 30,
        split_by_date: bool = False,
        agg_function: str = "sum",
        cols_to_aggregate_by: list[str] = ["physicalid"],
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> pd.DataFrame:
        feature_columns = ["geometry"]
        if date_column is not None:
            feature_columns.append(date_column)
            self.features[date_column] = self.features[date_column].apply(datetime64)
        if method == "weighted":
            feature_columns.append("weight")
            intersection_weights = self.__get_intersection_weights(
                buffer=buffer, intersection_data_path=intersection_data_path
            )
            weighted_features = self.features.sjoin(
                intersection_weights, how="left", predicate="within"
            )[feature_columns].fillna(value=1.0)
        elif method == "binary":
            feature_columns.append("weight")
            intersection_weights = self.__get_intersection_weights(
                buffer=buffer, intersection_data_path=intersection_data_path
            )
            intersection_weights["weight"] = 0
            weighted_features = self.features.sjoin(
                intersection_weights, how="left", predicate="within"
            )[feature_columns].fillna(value=1.0)
        elif method == "uniform":
            weighted_features = self.features[feature_columns].copy()
            weighted_features["weight"] = 1.0
        elif method == "value":
            if not isinstance(feature_value_column, str):
                raise TypeError(
                    "'feature_value_column' must be a string if 'method' is set to 'value'"
                )
            feature_columns.append(feature_value_column)
            weighted_features = self.features[feature_columns].copy()
            weighted_features["weight"] = weighted_features[feature_value_column]
        else:
            raise NotImplementedError(f"Method {method} has not been implemented.")
        buffered_streets = self.streets.copy()
        buffered_streets["geometry"] = buffered_streets["geometry"].buffer(buffer)
        street_assignment = weighted_features.sjoin(
            buffered_streets, how="right", predicate="within"
        )
        if split_by_date:
            if date_column is None:
                raise TypeError("date_column cannot be None if split_by_date is True")
            street_assignment["weight"] = street_assignment[
                ["weight", date_column, "until", "after"]
            ].apply(
                lambda o: (
                    0
                    if pd.isna(o[date_column])
                    or o[date_column] > o["until"]
                    or o[date_column] <= o["after"]
                    else o["weight"]
                ),
                axis=1,
            )
        feature_aggregation = (
            street_assignment.groupby(by=cols_to_aggregate_by, dropna=False)[["weight"]]
            .agg(agg_function)
            .rename(columns={"weight": output_column})
        )
        return feature_aggregation


class FeatureJoiner:

    def __init__(self, streets: gpd.GeoDataFrame, column_selection: list[str]):
        self.streets = (
            streets[
                (streets["rw_type"] == "1") & (streets["shape_leng"].astype(float) > 80)
            ][column_selection]
            .drop_duplicates(subset=["physicalid"])
            .copy()
        )

    def add_linear_feature(
        self,
        features: gpd.GeoDataFrame,
        output_column: str,
        *,
        predicate: str = "contains",
        buffer: int = 30,
        install_date_column: str | None = None,
    ) -> None:
        streets_with_features = RoadFeaturesCalculator(
            features=features, streets=self.streets
        ).calculate_linear_road_features(
            output_column=output_column,
            install_date_column=install_date_column,
            predicate=predicate,
            buffer=buffer,
        )
        self.streets = self.streets.merge(
            streets_with_features, how="left", on="physicalid"
        )

    def add_point_feature(
        self,
        features: gpd.GeoDataFrame,
        output_column: str,
        *,
        method: str = "uniform",
        buffer: int = 30,
        date_column: str | None = None,
        split_by_date: bool = False,
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> None:
        streets_with_features = RoadFeaturesCalculator(
            features=features, streets=self.streets
        ).calculate_point_road_features(
            output_column=output_column,
            date_column=date_column,
            split_by_date=split_by_date,
            method=method,
            buffer=buffer,
            intersection_data_path=intersection_data_path,
        )
        self.streets = self.streets.merge(
            streets_with_features, how="left", on="physicalid"
        )

    def add_multiple_features(
        self, dataframes: list[pd.DataFrame], index_cols: list[str]
    ) -> None:
        multi_index = pd.MultiIndex.from_frame(self.streets[index_cols])
        self.streets.drop(columns=index_cols, inplace=True)
        self.streets.set_index(multi_index, inplace=True)
        self.streets = self.streets.join(dataframes).reset_index()
