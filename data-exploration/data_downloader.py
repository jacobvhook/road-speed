import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
from shapely import wkt
from sodapy import Socrata


class OpenDataDownloader:
    """Contains methods to load data from NYC Open Data into memory."""

    def __init__(self, app_token: str):
        self.app_token = app_token

    def load_data(
        self,
        dataset: str | None = None,
        limit: int | None = None,
        save_to_file: str | None = None,
        load_from_file: str | None = None,
    ) -> pd.DataFrame:
        if load_from_file is not None:
            return pd.read_csv(load_from_file, low_memory=False)
        client = Socrata("data.cityofnewyork.us", app_token=self.app_token)
        results = client.get(dataset, limit=limit)
        df = pd.DataFrame.from_records(results)
        if save_to_file is not None:
            df.to_csv(save_to_file, index=False)
        return df

    def load_geo_dataframe(
        self,
        dataset: str | None = None,
        geometry_column: str | None = None,
        crs: str = "EPSG:4326",
        to_crs: str | None = None,
        limit: int | None = None,
        load_from_file: str | None = None,
        save_to_file: str | None = None,
    ) -> gpd.GeoDataFrame:
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
