from station.station import StationData
from station.dat_to_nc_converter import DatToNcConverter
from era5.era5_download_hook import Era5DownloadHook
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc

import utils.utils as utils

import tempfile
import os
import xarray as xr
import numpy as np
import datetime

class Era5Downloader():
        
    def __init__(self, station: StationData, grib_dir_path: str, hook, progress=None):
        self.station = station
        self.grib_dir_path = grib_dir_path
        self.lat = self.station.metadata.get("latitude")
        self.lon = self.station.metadata.get("longitude")
        self.hook = hook
        self.progress = progress
        
    def execute(self):
        if self.progress:
            self.progress.update_phase("Downloading ERA5 data")
        self.download()

class DownloadEra5ForStation(Era5Downloader):
        
    def __init__(self, station: StationData, grib_dir_path: str, hook, progress=None):
        super().__init__(station, grib_dir_path, hook, progress)
        self.years_by_month_dict = self.station.get_all_months_in_df()
        self.execute()
        
    def download(self):
        perct = 0
        for year, months in self.years_by_month_dict.items():
            print(f"Downloading... {year}")
            if len(months) < 10:
                for month in months:
                    self.hook.download_month(
                        year,
                        month,
                        self.grib_dir_path
                    )
                    perct += 1 / len(self.years_by_month_dict.items()) * 100 / len(months)
                    self.progress.update_percentage(perct)
            else:
                self.hook.download_year(
                    year,
                    self.grib_dir_path
                )                
                perct += 1 / len(self.years_by_month_dict.items()) * 100
                self.progress.update_percentage(perct)
                
                
            
class DownloadEra5ForStationGaps(Era5Downloader):
        
    def __init__(self, station: StationData, grib_dir_path: str, hook, progress=None):
        super().__init__(station, grib_dir_path, hook, progress)
        self.hours_missing = self.station.find_gaps()
        self.execute()
        
    def download(self):
  
        if not self.hours_missing:
                print("No missing hours")
                return

        grouped_hours_by_day = {}
            
        for hour in self.hours_missing:
            if hour.date() not in grouped_hours_by_day:
                grouped_hours_by_day[hour.date()] = []
            grouped_hours_by_day[hour.date()].append(hour.hour)

        count = 0
        for day, hours in grouped_hours_by_day.items():
            if self.progress:
                self.progress.update_percentage(count / len(grouped_hours_by_day.items()) * 100)
            self.hook.download_hours_on_same_day(
                day.year,
                day.month,
                day.day,
                hours,
                self.grib_dir_path
            )
            count += 1


class Era5ForStationCropper():
    
    def __init__(self, station: StationData, era5_path: str, era5_target_path: str):
        self.station = station
        self.era5_path = era5_path
        self.era5_target_path = era5_target_path
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def execute(self):
        self.era5_path = self.crop_time_axis()
        self.era5_path = self.drop_along_time_axis()
        self.era5_path = self.crop_lat_lon_to_grid(do_export=True)
        print("Era5 for station cropped and exported to:", self.era5_target_path)
    
    def crop_lat_lon_to_grid(self, do_export=False, width=8, height=8):
        station_lat = self.station.metadata.get("latitude")
        station_lon = self.station.metadata.get("longitude") % 360
        saves_to = self.temp_dir.name + "/lat_lon_cropped.nc"
        xr_era5 = xr.open_dataset(self.era5_path)
        # reduce the lon and lat grid to width x height
        print("Lat: ", station_lat)
        print("Lon: ", station_lon)
        
        
        nearest_lon_idx, nearest_lat_idx = utils.find_nearest_lon_lat(
            xr_era5.lon.values, xr_era5.lat.values,
            station_lon, station_lat
        ) 

        print("nearest_lat_idx:", nearest_lat_idx, xr_era5.lat.values)
        print("nearest_lon_idx:", nearest_lon_idx, xr_era5.lon.values)
    
        nearest_lat = xr_era5.lat.values[nearest_lat_idx]
        nearest_lon = xr_era5.lon.values[nearest_lon_idx]
            
        print("nearest_lat:", nearest_lat)
        print("nearest_lon:", nearest_lon)
            
        if width % 2 == 0:
            # longitude
            nearest_is_smaller = None
            if station_lon < 10 or station_lon > 350: # avoid mistakes near the meridian
                nearest_is_smaller = nearest_lon + 20 % 360 < station_lon + 20 % 360
            else:
                nearest_is_smaller = nearest_lon < station_lon
            if nearest_is_smaller:
                print("nearest lon is smaller")
                crop_lon_idx_min = nearest_lon_idx - width // 2 + 1
                crop_lon_idx_max = nearest_lon_idx + width // 2
            else:
                print("nearest lon is bigger")
                crop_lon_idx_min = nearest_lon_idx - width // 2
                crop_lon_idx_max = nearest_lon_idx + width // 2 - 1
                
            # latitude
            # assert latitude is sorted descending
            assert xr_era5.lat.values[0] > xr_era5.lat.values[-1]
            nearest_is_bigger = nearest_lat > station_lat
            if nearest_is_bigger:
                print("nearest lat is bigger")
                crop_lat_idx_min = nearest_lat_idx - height // 2 + 1
                crop_lat_idx_max = nearest_lat_idx + height // 2
            else:
                print("nearest lat is smaller")
                crop_lat_idx_min = nearest_lat_idx - height // 2
                crop_lat_idx_max = nearest_lat_idx + height // 2 - 1
            
        else:
            crop_lon_idx_min = nearest_lon_idx - width // 2
            crop_lon_idx_max = nearest_lon_idx + width // 2
            crop_lat_idx_min = nearest_lat_idx - height // 2
            crop_lat_idx_max = nearest_lat_idx + height // 2
            
        
        print("crop_lon_idx_min:", crop_lon_idx_min)
        print("crop_lon_idx_max:", crop_lon_idx_max)    
        print("crop_lat_idx_min:", crop_lat_idx_min)
        print("crop_lat_idx_max:", crop_lat_idx_max)
        
        
        xr_era5 = xr_era5.isel(
            lon=slice(crop_lon_idx_min, crop_lon_idx_max + 1), # does not include the last index
            lat=slice(crop_lat_idx_min, crop_lat_idx_max + 1)
        )
        
        # Verify the longitude and latitude values used for cropping
        print("Lon values after cropping:", xr_era5['lon'].values)
        print("Lat values after cropping:", xr_era5['lat'].values)
        
        xr_era5.to_netcdf(saves_to)
        
        if do_export:
            os.system(f"cp {saves_to} {self.era5_target_path}")
            return self.era5_target_path
        return saves_to
            
    def crop_time_axis(self, do_export=False):
        xr_era5 = xr.open_dataset(self.era5_path)
        self.station.df = self.station.df.sort_index()
        first_station_hour = self.station.df.index.min()
        last_station_hour = self.station.df.index.max()
        xr_era5 = xr_era5.sel(time=slice(first_station_hour, last_station_hour))
        saves_to = self.temp_dir.name + "/start_end_cropped.nc"
        xr_era5.to_netcdf(saves_to)
        if do_export:
            os.system(f"cp {saves_to} {self.era5_target_path}")
            self.cleanup()
            return self.era5_target_path
        return saves_to
    
    def drop_along_time_axis(self, do_export=False):
        missing_hours = self.station.find_gaps()
        xr_era5 = xr.open_dataset(self.era5_path)
        hours_to_drop = []
        for hour in missing_hours:
            if hour in xr_era5.time.values:
                hours_to_drop.append(hour)
                if len(hours_to_drop) > 1000:
                    xr_era5 = xr_era5.drop_sel(time=hours_to_drop)
                    hours_to_drop = []
        xr_era5 = xr_era5.drop_sel(time=hours_to_drop)
        saves_to = self.temp_dir.name + "/dropped_missing_hours.nc"
        xr_era5.to_netcdf(saves_to)
        if do_export:
            os.system(f"cp {saves_to} {self.era5_target_path}")
            self.cleanup()
            return self.era5_target_path
        return saves_to
    
    def cleanup(self):
        self.temp_dir.cleanup()