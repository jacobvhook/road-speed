import googlemaps
from dotenv import load_dotenv
import os


class Geocoder:
    def __init__(self, api_key: str | None = None) -> None:
        if not api_key:
            load_dotenv()
            self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        else:
            self.api_key = api_key

        self.gmaps_client = googlemaps.Client(key=self.api_key)

    def geocode(
        self, address: str, administrative_area: str = "NY", country="US"
    ) -> tuple[float, float]:
        geocode_result = self.gmaps_client.geocode(
            address,
            components={"administrative_area": administrative_area, "country": country},
        )
        latitude = geocode_result[0]["geometry"]["location"]["lat"]
        longitude = geocode_result[0]["geometry"]["location"]["lng"]
        return (latitude, longitude)
