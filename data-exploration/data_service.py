from data_downloader import OpenDataDownloader
import data_sources
from datetime import datetime
import geo
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely import empty, GeometryType, union_all


class CrashDataService:
    """Class providing some data processing methods for data obtained from NYC Open Data."""

    def __init__(
        self,
        nyc_app_token: str,
        from_year: int = 2010,
        extra_columns: list[str] | None = None,
    ):
        self.app_token = nyc_app_token
        self.data_loader = OpenDataDownloader(nyc_app_token)
        self.from_year = from_year
        self.columns = extra_columns
        self.__load_crashes_dataset()

    def __load_crashes_dataset(self) -> gpd.GeoDataFrame:
        self.crashes = self.data_loader.load_data(
            data_sources.CRASHES_ENDPOINT, limit=3000000
        )
        columns_to_return = [
            "collision_id",
            "crash_date",
            "crash_time",
            "latitude",
            "longitude",
        ]
        if self.columns is not None:
            for col in self.columns:
                if col not in columns_to_return:
                    columns_to_return.append(col)
        self.crashes = self.crashes[columns_to_return]
        self.crashes.dropna(subset=["longitude", "latitude"], inplace=True)
        self.crashes["datetime"] = self.crashes[["crash_date", "crash_time"]].apply(
            lambda o: self.__get_datetime(o["crash_date"], o["crash_time"]), axis=1
        )
        self.crashes.drop(columns=["crash_date", "crash_time"], inplace=True)
        self.crashes = self.crashes[
            self.crashes.datetime >= datetime(self.from_year, 1, 1)
        ]
        self.crashes = gpd.GeoDataFrame(
            self.crashes,
            geometry=gpd.points_from_xy(
                self.crashes["longitude"], self.crashes["latitude"]
            ),
            crs=geo.STD_EPSG,
        ).to_crs(geo.NYC_EPSG)
        self.crashes.drop(columns=["longitude", "latitude"], inplace=True)
        return self.crashes

    def __load_streets_dataset(
        self,
        columns_to_load: list[str] | None = None,
    ) -> gpd.GeoDataFrame:
        streets = self.data_loader.load_geo_dataframe(
            data_sources.CENTERLINE_ENDPOINT,
            geometry_column="the_geom",
            limit=3000000,
            to_crs=geo.NYC_EPSG,
        )
        # Streets have road type 1
        streets = streets[streets["rw_type"] == "1"]
        if columns_to_load is not None:
            if "geometry" not in columns_to_load:
                columns_to_load.append("geometry")
            if "physicalid" not in columns_to_load:
                columns_to_load.append("physicalid")
            streets = streets[columns_to_load]
        streets.drop_duplicates(subset=["geometry"], inplace=True)
        return streets

    def __load_speed_humps_dataset(self) -> gpd.GeoDataFrame:
        humps = self.data_loader.load_geo_dataframe(
            data_sources.SPEEDHUMPS_ENDPOINT,
            "the_geom",
            to_crs=geo.NYC_EPSG,
            limit=3000000,
        )
        humps = humps[["humps", "geometry"]]
        # Some rows do not have geometry info
        empty_multiline_string = empty(1, GeometryType.MULTILINESTRING)[0]
        humps = humps[humps.geometry != empty_multiline_string]
        humps["humps"] = humps["humps"].astype(float)
        humps = humps.groupby(by="geometry", as_index=False)["humps"].sum()
        humps = gpd.GeoDataFrame(humps, crs=geo.NYC_EPSG)
        humps["geometry"] = humps.geometry.centroid
        return humps

    def __load_speed_limits_dataset(self) -> gpd.GeoDataFrame:
        speed_limits = self.data_loader.load_geo_dataframe(
            data_sources.SPEEDLIMITS_ENDPOINT,
            "the_geom",
            to_crs=geo.NYC_EPSG,
            limit=3000000,
        )
        speed_limits = speed_limits[["postvz_sl", "geometry"]]
        speed_limits["postvz_sl"] = speed_limits["postvz_sl"].astype(int)
        speed_limits = speed_limits.groupby(by="geometry", as_index=False)[
            "postvz_sl"
        ].mean()
        speed_limits = gpd.GeoDataFrame(speed_limits, crs=geo.NYC_EPSG)
        speed_limits["geometry"] = speed_limits.geometry.centroid
        return speed_limits

    def __load_trees_dataset(self) -> gpd.GeoDataFrame:
        trees = self.data_loader.load_geo_dataframe(
            data_sources.TREES_ENDPOINT, "the_geom", to_crs=geo.NYC_EPSG, limit=3000000
        )
        trees = trees[["tree_id", "geometry"]]
        return trees

    def __get_datetime(self, date: str, time: str) -> datetime:
        year, month, day = list(map(int, date.split("T")[0].split("-")))
        hour, minute = list(map(int, time.split(":")))
        return datetime(year, month, day, hour, minute)

    def __spatial_join_to_street_data(
        self,
        street_data: gpd.GeoDataFrame,
        right_df: gpd.GeoDataFrame,
        agg_column: str,
        agg_op: str,
    ) -> gpd.GeoDataFrame:
        street_data_cols = list(street_data.columns)
        street_data = street_data.sjoin(right_df, how="left")
        street_data = street_data.groupby(
            by=street_data_cols, as_index=False, dropna=False
        ).agg(**{agg_column: pd.NamedAgg(column=agg_column, aggfunc=agg_op)})
        street_data = gpd.GeoDataFrame(street_data, crs=geo.NYC_EPSG)
        return street_data

    def __get_intersection_crashes(
        self, street_geometry: gpd.GeoDataFrame, buffer: int
    ) -> gpd.GeoDataFrame:
        street_geometry["intersections"] = street_geometry.geometry.boundary.buffer(
            buffer
        )
        intersections = gpd.GeoDataFrame(
            street_geometry[["physicalid", "intersections"]],
            crs=geo.NYC_EPSG,
            geometry="intersections",
        )
        intersection_crashes_ids = (
            self.crashes[["collision_id", "geometry"]]
            .sjoin(intersections, how="inner", predicate="within")["collision_id"]
            .drop_duplicates()
        )
        intersection_crashes_mask = self.crashes["collision_id"].isin(
            intersection_crashes_ids.values
        )
        return (
            self.crashes[intersection_crashes_mask],
            self.crashes[~intersection_crashes_mask],
        )

    def get_non_intersection_info(
        self,
        buffer: int,
        join_speed_humps: bool = False,
        join_speed_limits: bool = False,
        join_trees: bool = False,
        destination_file_name: str | None = None,
    ) -> gpd.GeoDataFrame:
        final_cols = [
            "collision_id",
            "geometry",
            "datetime",
            "physicalid",
            "shape_leng",
            "st_width",
        ]
        if self.columns is not None:
            final_cols += self.columns
        street_data = self.__load_streets_dataset(
            columns_to_load=["geometry", "physicalid", "shape_leng", "st_width"]
        )
        _, non_intersection_crashes = self.__get_intersection_crashes(
            street_data, buffer
        )
        street_data["geometry"] = street_data.geometry.buffer(buffer)
        if join_speed_humps:
            humps = self.__load_speed_humps_dataset()
            street_data = self.__spatial_join_to_street_data(
                street_data, humps, "humps", "sum"
            )
            final_cols.append("humps")
        if join_speed_limits:
            speed_limits = self.__load_speed_limits_dataset()
            street_data = self.__spatial_join_to_street_data(
                street_data, speed_limits, "postvz_sl", "mean"
            )
            final_cols.append("postvz_sl")
        if join_trees:
            trees = self.__load_trees_dataset()
            street_data = self.__spatial_join_to_street_data(
                street_data, trees, "tree_id", "count"
            )
            street_data = street_data.rename(columns={"tree_id": "trees"})
            final_cols.append("trees")
        crashes_street = non_intersection_crashes.sjoin(street_data, how="inner")[
            final_cols
        ]
        if destination_file_name is not None:
            data_base_path = Path("./data")
            crashes_street.to_csv(data_base_path / destination_file_name, index=False)
        return crashes_street
