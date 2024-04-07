import cdsapi
from dotenv import load_dotenv
import os

from ..crai.station_reconstruct.utils import Station

load_dotenv("copernicus_api.env")

class Era5DownloadHook:
    
    def __init__(self, lat, lon):
        self.cds = cdsapi.Client(
            url="https://cds.climate.copernicus.eu/api/v2",
            key=f"{os.getenv('UID')}:{os.getenv('API_KEY')}"
        )
        self.lon, self.lat = lon, lat
        self.coordinate_limits = {
            "north": self.lat + 0.9,
            "west": self.lon - 0.9,
            "south": self.lat - 0.9,
            "east": self.lon + 0.9,
        }


    def download_hours_on_same_day(self, year, month, day, hours, target_path):
        self._download({
            "years": [year],
            "months": [month],
            "days": [day],
            "hours": hours
        }, target_path + f"/{year}_{month}_{day}.grib")
            
    def _download(self, date_info, save_to_file_path):
        response = self.cds.retrieve(
        'reanalysis-era5-single-levels',
        {
            "product_type": "reanalysis",
            "format": "grib",
            "variable": "2m_temperature",
            "area": [
                self.coordinate_limits["north"],
                self.coordinate_limits["west"] % 360,
                self.coordinate_limits["south"],
                self.coordinate_limits["east"] % 360,
            ],
            "year": date_info.get("years"),
            "month": [f"{month:02d}" for month in date_info.get("months")],
            "day": [f"{day:02d}" for day in date_info.get("days")],
            "time": [f"{hour:02d}:00" for hour in date_info.get("hours")]

        }, save_to_file_path)