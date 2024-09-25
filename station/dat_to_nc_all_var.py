"""
Converts all .dat files in a directory to a .nc file in the working directory, including all variables.

Modules used:

    * os
    * numpy
    * xarray
    * datetime
    * pandas
    * tqdm (for progress bar)
    * re (for metadata extraction)

"""

import os
import numpy as np
import xarray as xr
from datetime import datetime
import pandas as pd
import tqdm
import re
import concurrent.futures

def circular_mean(series):
    """
    Calculate the mean direction for circular data (e.g., wind direction).
    """
    radians = np.deg2rad(series.dropna())
    sin_mean = np.nanmean(np.sin(radians))
    cos_mean = np.nanmean(np.cos(radians))
    mean_angle = np.arctan2(sin_mean, cos_mean)
    mean_angle_deg = np.rad2deg(mean_angle)
    if mean_angle_deg < 0:
        mean_angle_deg += 360
    return mean_angle_deg

def custom_aggregation(var_name):
    """
    Define custom aggregation functions for different variables during resampling.
    """
    def aggregate(series):
        # Data quality checks
        if series.isna().sum() > 20:
            return np.nan
        if var_name != 'tipping' and series.nunique() <= 3:
            return np.nan

        if var_name == 'tipping':
            # Sum for precipitation
            return series.sum()
        elif var_name == 'wind_speed':
            # Mean for wind speed
            return np.nanmean(series)
        elif var_name == 'wind_dir':
            # Circular mean for wind direction
            return circular_mean(series)
        else:
            # Median for other variables
            return np.nanmedian(series)
    return aggregate

class DatToNcAllVar:
    """
    Class to convert .dat files to a NetCDF (.nc) file, including all variables.
    """
    def __init__(self, name, directory=None, target_directory=None, hourly=True,
                 grid_blueprint=None, keep_original=False):
        self.name = name

        # Use os.path.join for cross-platform compatibility
        default_directory = os.path.join(os.getcwd(), "station_data_as_dat", self.name.capitalize())
        self.directory = directory if directory is not None else default_directory

        default_target_directory = os.path.join(os.getcwd(), "station_data_as_nc")
        self.target_directory = target_directory if target_directory is not None else default_target_directory

        # Ensure the directories exist
        if not os.path.exists(self.directory):
            raise FileNotFoundError(f"The directory {self.directory} does not exist.")
        if not os.path.exists(self.target_directory):
            os.makedirs(self.target_directory)

        self.files = self.get_files()
        self.dataframe = None
        self.original_df = None
        self.keep_original = keep_original
        self.nc_data = None
        self.meta_data = {}  # Initialize as empty dict
        self.hourly = hourly
        self.grid_blueprint = grid_blueprint

    def get_files(self):
        """
        Retrieve and sort all .dat files in the directory.
        """
        files = [file for file in os.listdir(self.directory) if file.endswith(".dat")]
        return sorted(files)

    def convert_to_dataframe(self, file) -> pd.DataFrame:
        """
        Load a .dat file into a DataFrame and process it.
        """
        # Load into DataFrame using specified separator and header
        format_config = self.get_tas_format_config()
        separator = format_config.get("separator", r"\s+")
        header = format_config.get("header", 0)
        file_path = os.path.join(self.directory, file)
        df = pd.read_csv(file_path, sep=separator, header=header)
        return self.resample_to_hourly_steps(df)

    def extract_meta_data(self):
        """
        Extract metadata (latitude, longitude, elevation) from .rtf file.
        """
        meta_data = {}
        # Define patterns for extracting information
        location_pattern = re.compile(r'Location: ([\d.-]+) deg Lat, ([\d.-]+) deg Lon')
        elevation_pattern = re.compile(r'Elevation: (\d+) m')

        # Search for .rtf files in the directory
        rtf_files = [file for file in os.listdir(self.directory) if file.endswith('.rtf')]

        if not rtf_files:
            print("Error: No .rtf files found in the directory.")
            return meta_data

        # Use the first .rtf file found
        rtf_file_path = os.path.join(self.directory, rtf_files[0])

        try:
            with open(rtf_file_path, 'r') as file:
                content = file.read()

                # Extract coordinates
                match_location = location_pattern.search(content)
                if match_location:
                    latitude = float(match_location.group(1))
                    longitude = float(match_location.group(2))
                    meta_data['latitude'] = latitude
                    meta_data['longitude'] = longitude

                # Extract elevation
                match_elevation = elevation_pattern.search(content)
                if match_elevation:
                    elevation = int(match_elevation.group(1))
                    meta_data['elevation'] = elevation
        except FileNotFoundError:
            print(f"Error: File {rtf_file_path} not found.")

        return meta_data


    def extract(self, first_n_files=None, progress=None):
        # Initialize an empty list to store DataFrames
        dataframes = []
        if self.keep_original:
            self.original_df = pd.DataFrame()
        print(f"Extracting {self.name}...")
        if first_n_files is None:
            first_n_files = len(self.files)
        files_to_process = self.files[:first_n_files]

        # Use ThreadPoolExecutor for I/O-bound tasks or ProcessPoolExecutor for CPU-bound tasks - here, we use the latter since it is faster 
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # Map the convert_to_dataframe function to the list of files
            futures = [executor.submit(self.convert_to_dataframe, file) for file in files_to_process]
            for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
                df = future.result()
                dataframes.append(df)
                if progress:
                    progress.update_percentage(len(dataframes) / first_n_files * 100)
        
        '''    old way of doing it:
            if first_n_files is None:
                first_n_files = len(self.files)
            c = 0

            # Collect DataFrames in a list for efficient concatenation
            dataframes = []
            files_to_process = self.files[:first_n_files]

            for file in tqdm.tqdm(files_to_process):
                if progress:
                    progress.update_percentage(c / first_n_files * 100)
                df = self.convert_to_dataframe(file)
                dataframes.append(df)
                c += 1
        '''
        
        # Concatenate all DataFrames at once
        self.dataframe = pd.concat(dataframes)
        return self.dataframe


    def resample_to_hourly_steps(self, df):
        """
        Convert date columns to datetime, clean data, and resample to hourly intervals.
        """
        # Rename columns for consistency
        df.rename(columns={'mon': 'month', 'min': 'minute'}, inplace=True)

        # Convert to datetime
        df['datetime'] = pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute']])
        df = df.drop(columns=['year', 'month', 'day', 'hour', 'minute'])

        # Replace placeholder values with NaN
        df = df.replace(-999.99, np.nan)

        # Identify temperature sensor columns
        temperature_sensors = [col for col in df.columns if 'temp' in col or col == 'mcp9808']

        # Clean temperature data using vectorized operations
        for sensor in temperature_sensors:
            df[sensor] = df[sensor].where(df[sensor].between(-45, 45))

        # Create 'tas' as the average of available temperature sensors
        if temperature_sensors:
            df['tas'] = df[temperature_sensors].mean(axis=1)
            # Convert from Celsius to Kelvin
            df['tas'] = df['tas'] + 273.15

        # Set datetime as the index
        df = df.set_index("datetime")

        if self.hourly:
            # Resample to hourly intervals with custom aggregation
            hourly_df = pd.DataFrame()
            for var_name in df.columns:
                hourly_series = df[var_name].resample('h').apply(custom_aggregation(var_name))
                hourly_df[var_name] = hourly_series
        else:
            # Keep original minutely data
            hourly_df = df

        return hourly_df

    def transform(self):
        """
        Final transformations on the combined DataFrame.
        """
        if self.keep_original:
            self.original_df = self.dataframe.copy()
            self.original_df = self.original_df.reindex(
                pd.date_range(start=self.dataframe.index.min(), end=self.dataframe.index.max(), freq="h")
            )

        # Ensure all data types are appropriate
        for col in self.dataframe.columns:
            self.dataframe[col] = pd.to_numeric(self.dataframe[col], errors='ignore')

    def load(self, location):
        """
        Create an xarray Dataset from the DataFrame and save it to a NetCDF file.
        """
        # Prepare data variables for the dataset
        data_vars = {}
        for var_name in self.dataframe.columns:
            # Reshape data to match dimensions
            data = self.dataframe[var_name].values.reshape(-1, 1, 1)
            data_vars[var_name] = (["time", "lat", "lon"], data)

        # Use default coordinates if metadata is missing
        default_latitude = 0.0  # Replace with your default latitude
        default_longitude = 0.0  # Replace with your default longitude

        lat = self.meta_data.get('latitude', default_latitude)
        lon = self.meta_data.get('longitude', default_longitude)

        # Create the xarray Dataset with all variables
        ds = xr.Dataset(
            data_vars,
            coords={
                "time": self.dataframe.index.values,
                "lat": [lat],  # Use lat directly
                "lon": [lon],  # Use lon directly
            },
        )

        # Warning if lat or lon is not found
        if lat == default_latitude or lon == default_longitude:
            print("Warning: Latitude or Longitude not found in metadata. Using default values.")

        # Save the dataset to a NetCDF file
        save_to_path = os.path.join(location, f"{self.name.lower()}.nc")
        print(f"Saving to {save_to_path}")

        # Remove existing file if necessary
        if os.path.exists(save_to_path):
            os.remove(save_to_path)

        ds.to_netcdf(save_to_path)
        return save_to_path

    def execute(self, location=None, first_n_files=None):
        """
        Main method to execute the conversion process.
        """
        # Load metadata first
        self.meta_data = self.extract_meta_data()
        if not self.meta_data:
            print("Metadata is missing or incomplete. Using default values.")

        # Proceed to extract data files
        self.extract(first_n_files=first_n_files)
        self.transform()
        if location is None:
            location = self.target_directory
        self.load(location)


    def get_tas_format_config(self):
        """
        Configuration for TAS format (if needed).
        """
        return {
            "separator": r"\s+",
            "header": 0,
            "digit_precision": 2,
        }
    

''' Example usage

# Initialize the converter
converter = DatToNcAllVar(
    name="Vienna_AllVar",
    directory="measurements/Vienna",
    target_directory="station_data_as_nc",
    hourly=True,
    keep_original=False
)

# Run the conversion process
converter.execute()

ds = xr.open_dataset("station_data_as_nc/vienna.nc")
'''
