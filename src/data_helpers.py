import geopandas as gpd
import pandas as pd
from shapely import is_empty
import geo
from pathlib import Path
from numpy import datetime64, timedelta64


class CollisionRatesCalculator:

    def __init__(self, crashes_df: gpd.GeoDataFrame, streets_df: gpd.GeoDataFrame):
        self.crashes = crashes_df
        self.streets = streets_df

    def __get_week_span(self) -> float:
        crash_dates = self.crashes["crash_date"].apply(datetime64)
        return (crash_dates.max() - crash_dates.min()) / timedelta64(1, "W")

    def __get_intersection_weights(
        self, intersection_data_path: Path = Path("../data/intersection_weights.pkl")
    ) -> gpd.GeoDataFrame:
        if intersection_data_path.exists():
            intersections = pd.read_pickle(intersection_data_path)
            return gpd.GeoDataFrame(
                intersections, geometry=intersections.geometry, crs=geo.NYC_EPSG
            )
        intersections = gpd.GeoDataFrame(
            geometry=self.streets["geometry"].boundary.buffer(30), crs=geo.NYC_EPSG
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

    def calculate_collision_rates(
        self,
        method: str = "weighted",
        intersection_data_path: Path = Path("../data/intersection_weights.pkl"),
    ) -> pd.DataFrame:
        if method == "weighted":
            intersection_weights = self.__get_intersection_weights(
                intersection_data_path
            )
            weighted_crashes = self.crashes.sjoin(
                intersection_weights, how="left", predicate="within"
            )[["collision_id", "geometry", "weight"]]
        elif method == "uniform":
            weighted_crashes = self.crashes[["collision_id", "geometry"]].copy()
            weighted_crashes["weight"] = 1.0
        else:
            raise NotImplementedError(f"Method {method} has not been implemented.")
        weighted_crashes["weight"] = weighted_crashes["weight"].fillna(value=1.0)

        buffered_streets = self.streets.copy()
        buffered_streets["geometry"] = buffered_streets["geometry"].buffer(30)

        collision_rates = (
            buffered_streets.sjoin(weighted_crashes, how="left")
            # TODO: decide what columns we want to keep.
            # Perhaps we want to pass them as arguments?
            .groupby(by="physicalid", as_index=False)["weight"]
            .sum()
            .rename(columns={"weight": "collision_rate"})
        )
        week_span = self.__get_week_span()
        collision_rates["collision_rate"] = (
            collision_rates["collision_rate"] / week_span
        )
        return collision_rates
