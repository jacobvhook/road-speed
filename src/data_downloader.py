from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
from sodapy import Socrata

import geo
from data_sources import ENDPOINTS


class GeometryFormatter:
    def __init__(self, X: pd.DataFrame, crs: str = geo.STD_EPSG):
        self.X = X
        self.crs = crs

    def from_geometry_column(self, geometry_column: str) -> gpd.GeoDataFrame:
        """Convert a DataFrame to a GeoDataFrame using NYC coordinates."""
        return (
            gpd.GeoDataFrame(
                self.X.rename(columns={geometry_column: "geometry"}),
                geometry=self.X[geometry_column].apply(shape),
                crs=self.crs,
            )
            .to_crs(geo.NYC_EPSG)
            .dropna(subset=["geometry"])
        )

    def from_lat_long(
        self, latitude_column: str = "latitude", longitude_column: str = "longitude"
    ) -> gpd.GeoDataFrame:
        return (
            gpd.GeoDataFrame(
                self.X,
                geometry=gpd.points_from_xy(
                    self.X[longitude_column], self.X[latitude_column]
                ),
                crs=self.crs,
            )
            .to_crs(geo.NYC_EPSG)
            .dropna(subset=[latitude_column, longitude_column])
            .drop(columns=[latitude_column, longitude_column])
        )


class OpenDataDownloader:
    """Contains methods to load data from NYC Open Data into memory."""

    def __init__(self, app_token: str):
        self.app_token = app_token

    def load_data(
        self,
        dataset: str,
        *,
        limit: int = 3_000_000,
        force_download: bool = False,
    ) -> pd.DataFrame:
        data_path: Path = Path(f"../data/{dataset}.pkl")
        if data_path.exists() and not force_download:
            return pd.read_pickle(data_path)
        client = Socrata("data.cityofnewyork.us", app_token=self.app_token)
        results = client.get(ENDPOINTS[dataset], limit=limit)
        df = pd.DataFrame.from_records(results)
        df.to_pickle(data_path)
        return df
