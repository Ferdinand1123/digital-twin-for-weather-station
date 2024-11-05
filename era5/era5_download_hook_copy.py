import cdsapi
from dotenv import load_dotenv
import os
import pandas as pd
from glob import glob
from concurrent.futures import ThreadPoolExecutor


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

    def download_period(self, start_year, end_year, target_folder):
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                self.download_month(year, month, target_folder)
        # Concatenate all downloaded files into a single dataframe after downloading

    def download_month_parallel(self, year, month, target_folder):
        print(f"Downloading {year}-{month:02d}")
        self._download({
            "years": [year],
            "months": [month],
            "days": range(1, 32),
            "hours": range(0, 24)
        }, f"{target_folder}/{year}_{month:02d}.grib")

    def download_period_parallel(self, start_year, end_year, target_folder):
        with ThreadPoolExecutor(max_workers=4) as executor:  # Adjust max_workers based on system capacity
            futures = [
                executor.submit(self.download_month_parallel, year, month, target_folder)
                for year in range(start_year, end_year + 1)
                for month in range(1, 13)
            ]

    def download_month(self, year, month, target_folder):
        print(f"Downloading {year}-{month:02d}")
        self._download({
            "years": [year],
            "months": [month],
            "days": range(1, 32),
            "hours": range(0, 24)
        }, f"{target_folder}/{year}_{month:02d}.grib")
        
    def _download(self, date_info, save_to_file_path):
        response = self.cds.retrieve(
            'reanalysis-era5-single-levels',
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": [
                    "10m_v_component_of_wind",
                    "2m_dewpoint_temperature",
                    "2m_temperature",
                    "surface_pressure",
                    "total_precipitation"
                ],
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
            },
            save_to_file_path
        )

    # Placeholder function for loading a .grib file into a dataframe (requires implementation)
    def load_grib_to_dataframe(self, file_path):
        # Implement loading logic (e.g., using xarray or pygrib)
        pass
