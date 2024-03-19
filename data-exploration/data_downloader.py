from sodapy import Socrata
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape


class OpenDataDownloader:
    """Contains methods to load data from NYC Open Data into memory."""

    def __init__(self, app_token: str):
        self.app_token = app_token

    def load_data(self, dataset: str, limit: int = None) -> pd.DataFrame:
        client = Socrata("data.cityofnewyork.us", app_token=self.app_token)
        results = client.get(dataset, limit=limit)
        return pd.DataFrame.from_records(results)

    def load_geo_dataframe(
        self,
        dataset: str,
        geometry_column: str,
        crs: str = "EPSG:4326",
        to_crs: str = None,
        limit: int = None,
    ):
        df = self.load_data(dataset, limit)
        df["geometry"] = df[geometry_column].apply(shape)
        df.drop(columns=[geometry_column], inplace=True)
        if to_crs == None:
            return gpd.GeoDataFrame(df, geometry=df.geometry, crs=crs)
        return gpd.GeoDataFrame(df, geometry=df.geometry, crs=crs).to_crs(to_crs)
