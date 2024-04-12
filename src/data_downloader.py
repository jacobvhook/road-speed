from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import shape
from sodapy import Socrata

import geo
from data_sources import ENDPOINTS


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

    def from_geometry_column(
        self, df: pd.DataFrame, geometry_column: str, crs: str = geo.STD_EPSG
    ):
        """Convert a DataFrame to a GeoDataFrame using NYC coordinates."""
        df.rename(columns={geometry_column: "geometry"}, inplace=True)
        return gpd.GeoDataFrame(df, geometry=df.geometry.apply(shape), crs=crs).to_crs(
            geo.NYC_EPSG
        )

    def load_geo_dataframe(
        self,
        dataset: str | None = None,
        geometry_column: str | None = None,
        crs: str = geo.STD_EPSG,  # assume all inputs are in lat/long by default
        to_crs: str = "ESPG:2263",
        limit: int | None = None,
        load_from_file: str | None = None,
        save_to_file: str | None = None,
    ) -> gpd.GeoDataFrame:
        return self.to_geo_dataframe(
            self.load_data(
                dataset,
            )
        )
        # load_data(dataset).to_geo_...()

        if load_from_file is not None:
            df = pd.read_csv(load_from_file, low_memory=False)
            df["geometry"] = df[geometry_column].apply(wkt.loads)
            if geometry_column != "geometry":
                df.drop(columns=geometry_column, inplace=True)
            return gpd.GeoDataFrame(df, geometry=df.geometry, crs=crs)
        df = self.load_data(dataset, limit)
        df["geometry"] = df[geometry_column].apply(shape)
        if geometry_column != "geometry":
            df.drop(columns=[geometry_column], inplace=True)
        if to_crs is None:
            gdf = gpd.GeoDataFrame(df, geometry=df.geometry, crs=crs)
        else:
            gdf = gpd.GeoDataFrame(df, geometry=df.geometry, crs=crs).to_crs(to_crs)
        if save_to_file is not None:
            gdf.to_csv(save_to_file, index=False)
        return gdf
