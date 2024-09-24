import os
import numpy as np
import xarray as xr
from datetime import datetime
import pandas as pd
import tqdm
import re
from typing import Any

class DatToNcConverter:

    def __init__(self, name, directory=None, target_directory=None, keep_original=False):
        self.name = name
        self.directory = directory if directory is not None else os.getcwd() + "/station_data_as_dat/" + self.name.capitalize()
        self.target_directory = target_directory if target_directory is not None else os.getcwd() + "/station_data_as_nc/"
        self.files = self.get_files()
        self.dataframe = None
        self.original_df = None
        self.keep_original = keep_original
        self.nc_data = None
        self.meta_data = self.extract_meta_data()
        self.variables = ["bmp180_temp", "bmp180_pres", "bmp180_slp", "bmp180_alt", 
                          "bmp280_temp", "bmp280_pres", "bmp280_slp", "bmp280_alt", 
                          "bme_temp", "bme_pres", "bme_slp", "bme_alt", "bme_hum", 
                          "htu_temp", "htu_hum", "mcp9808", "tipping", "vis_light", 
                          "ir_light", "uv_light", "wind_dir", "wind_speed"]

    # determine files in directory
    def get_files(self):
        files = []
        for file in os.listdir(self.directory):
            if file.endswith(".dat"):
                files.append(file)
        return sorted(files)
    
    # convert .dat file to dataframe and append to dataframe
    def convert_to_dataframe(self, file) -> pd.DataFrame:
        format_config = self.get_tas_format_config()
        separator = format_config.get("separator", "\s+")
        header = format_config.get("header", 0)
        df = pd.read_csv(os.path.join(self.directory, file), sep=separator, header=header)
        return self.process_dataframe(df)

    def extract_meta_data(self):
        meta_data = {}
        location_pattern = re.compile(r'Location: ([\d.-]+) deg Lat, ([\d.-]+) deg Lon')
        elevation_pattern = re.compile(r'Elevation: (\d+) m')
        rtf_files = [file for file in os.listdir(self.directory) if file.endswith('.rtf')]

        if not rtf_files:
            print("Error: No .rtf files found in the directory.")
            return meta_data

        rtf_file_path = os.path.join(self.directory, rtf_files[0])

        try:
            with open(rtf_file_path, 'r') as file:
                content = file.read()
                match_location = location_pattern.search(content)
                if (match_location):
                    latitude = float(match_location.group(1))
                    longitude = float(match_location.group(2))
                    meta_data['latitude'] = latitude
                    meta_data['longitude'] = longitude
                match_elevation = elevation_pattern.search(content)
                if (match_elevation):
                    elevation = int(match_elevation.group(1))
                    meta_data['elevation'] = elevation
        except FileNotFoundError:
            print(f"Error: File {rtf_file_path} not found.")
        return meta_data

    # extract a whole folder of .dat files into to self.dataframe
    def extract(self, first_n_files=None, progress=None):
        self.dataframe = pd.DataFrame()
        if self.keep_original:
            self.original_df = pd.DataFrame()
        print(f"Extracting {self.name}...")
        if first_n_files is None:
            first_n_files = len(self.files)
        c = 0
        for file in tqdm.tqdm(self.files[:first_n_files]):
            if progress:
                progress.update_percentage(c / first_n_files * 100)
                c += 1
            df = self.convert_to_dataframe(file)
            self.dataframe = pd.concat([self.dataframe, df])
        return self.dataframe
    
    # process dataframe to netcdf compatible format datatype
    def process_dataframe(self, df):
        df["datetime"] = df.apply(lambda row: datetime(int(row["year"]), int(row["mon"]), int(row["day"]), int(row["hour"]), int(row["min"])), axis=1)
        df = df.drop(columns=["year", "mon", "day", "hour", "min"])
        df = df.replace(-999.99, np.nan)

        df = df.set_index("datetime")
        
        for var in self.variables:
            if var in df.columns:
                df[var] = df[var].apply(lambda x: x if -45 <= x <= 45 else np.nan)
        
        return df

    def transform(self):
        if self.keep_original:
            self.original_df = self.dataframe.drop(columns=self.variables)
            self.original_df = self.original_df.reindex(pd.date_range(start=self.dataframe.index.min(), end=self.dataframe.index.max(), freq="T"))

        mapping = {var: var for var in self.variables}
        
        intersect_columns = list(set(self.dataframe.columns).intersection(set(mapping.keys())))
        self.dataframe = self.dataframe[intersect_columns]
        
        self.dataframe = self.dataframe.rename(columns=mapping)

    def load(self, location):
        data_vars = {var: (["time", "lat", "lon"], self.dataframe[var].values.reshape(-1, 1, 1)) for var in self.variables if var in self.dataframe.columns}
        ds = xr.Dataset(data_vars, coords={"time": self.dataframe.index.values, "lat": [self.meta_data["latitude"]], "lon": [self.meta_data["longitude"]]})

        save_to_path = os.path.join(location, self.name.lower() + ".nc")
        print(f"Saving to {save_to_path}")
        if os.path.exists(save_to_path):
            os.remove(save_to_path)
        ds.to_netcdf(save_to_path)
        return save_to_path

    def execute(self, location=None, first_n_files=None):
        self.extract(first_n_files=first_n_files)
        self.transform()
        if location is None:
            location = self.target_directory
        self.load(location)
        
    def get_tas_format_config(self):
        return {
            "separator": "\s+",
            "header": 0,
            "digit_precision": 2,
        }

# Example usage
directory = "measurements/Vienna"
converter = DatToNcConverter(name="Vienna", directory=directory)
converter.execute()
