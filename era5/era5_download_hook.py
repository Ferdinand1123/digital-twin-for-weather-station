import cdsapi
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv("copernicus_api.env")

class Era5DownloadHook:
    
    def __init__(self, lat, lon):
        # Extract API URL and key from environment variables
        url = os.getenv('url')  # CDS-Beta API URL
        key = os.getenv('key')  # API key
        
        if not url or not key:
            raise ValueError("API URL and key must be set in the environment file")
        
        print("Using URL:", url)
        
        # Initialize the cdsapi Client using the url and key from the .env file
        self.cds = cdsapi.Client(url=url, key=key)
        
        self.lon, self.lat = lon, lat
        
        # Define the coordinates for the bounding box
        self.coordinate_limits = {
            "north": self.lat + 1,
            "west": self.lon - 1,
            "south": self.lat - 1,
            "east": self.lon + 1,
        }


    def download_hours_in_same_day(self, year, month, day, hours, target_folder):
        print(f"Downloading {year}-{month}-{day} {hours}")
        self._download({
            "years": [year],
            "months": [month],
            "days": [day],
            "hours": hours
        }, target_folder + f"/{year}_{month}_{day}.grib")
        
    def download_month(self, year, month: int, target_folder):
        print(f"Downloading {year}-{month}")
        self._download({
            "years": [year],
            "months": [month],
            "days": range(1, 32),
            "hours": range(0, 24)
        }, target_folder + f"/{year}_{month}.grib")
        
    def download_year(self, year, target_folder):
        print(f"Downloading {year}")
        self._download({
            "years": [year],
            "months": range(1, 13),
            "days": range(1, 32),
            "hours": range(0, 24)
        }, target_folder + f"/{year}.grib")
            
    def _download(self, date_info, save_to_file_path):
        response = self.cds.retrieve(
        'reanalysis-era5-single-levels',
        {
            "product_type": "reanalysis",
            "format": "grib",
            "variable": [
                "2m_temperature", 
                "total_precipitation",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "surface_pressure"],
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