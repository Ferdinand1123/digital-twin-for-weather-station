import os
import re
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm

class DatToNcConverter2:
    """
    Class to convert .dat files to a NetCDF (.nc) file, including all variables.
    """

    def __init__(self, name, directory, target_directory, hourly=True, save_raw=False, raw_directory = None, save_processed = False, processed_directory = None):
        self.name = name
        self.directory = directory
        self.target_directory = target_directory
        self.hourly = hourly

        # Ensure the directories exist
        if not os.path.exists(self.directory):
            raise FileNotFoundError(f"The directory {self.directory} does not exist.")
        if not os.path.exists(self.target_directory):
            os.makedirs(self.target_directory)

        self.meta_data = {}
        
        self.save_raw = save_raw
        self.raw_df = pd.DataFrame()  # Raw concatenated DataFrame
        self.raw_directory = raw_directory

        self.save_processed = save_processed
        self.processed_df = pd.DataFrame()  # Processed DataFrame
        self.processed_directory = processed_directory

        self.resampled_df = pd.DataFrame()  # Resampled DataFrame
        self.files = self.get_files()

    def get_files(self):
        """
        Retrieve and sort all .dat files in the directory.
        """
        files = [file for file in os.listdir(self.directory) if file.endswith(".dat")]
        return sorted(files)

    def extract_meta_data(self):
        """
        Extract metadata (latitude, longitude, elevation) from a .rtf file in the given directory.
        """
        meta_data = {}
        try:
            # Define patterns for extracting information
            location_pattern = re.compile(r'Location:\s*([\d.-]+)\s*deg\s*Lat,\s*([\d.-]+)\s*deg\s*Lon')
            elevation_pattern = re.compile(r'Elevation:\s*(\d+)\s*m')

            # Search for .rtf files in the directory
            rtf_files = [file for file in os.listdir(self.directory) if file.endswith('.rtf')]

            if not rtf_files:
                print("Error: No .rtf files found in the directory.")
                return meta_data

            # Use the first .rtf file found
            rtf_file_path = os.path.join(self.directory, rtf_files[0])

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

            self.meta_data = meta_data

        except FileNotFoundError:
            print("Error: Metadata file not found.")
            self.meta_data = meta_data
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            self.meta_data = meta_data

    def read_and_concatenate_dat_files(self):
        """
        Read all .dat files in the directory, create DataFrames with datetime, and concatenate them.
        """
        dataframes = []

        for file in tqdm(self.files, desc="Reading .dat files"):
            file_path = os.path.join(self.directory, file)
            try:
                # Load into pandas DataFrame, first line are the column names
                df = pd.read_csv(file_path, sep=r'\s+', header=0)
                # Rename columns for consistency
                df.rename(columns={'mon': 'month', 'min': 'minute'}, inplace=True)
                # Convert to datetime
                required_columns = ['year', 'month', 'day', 'hour', 'minute']
                if not all(col in df.columns for col in required_columns):
                    print(f"Missing required date columns in file {file}: {df.columns}")
                    continue
                # Ensure date columns are integers
                for col in required_columns:
                    df[col] = df[col].astype(int)
                df['datetime'] = pd.to_datetime(df[required_columns], errors='coerce')
                # Drop rows with invalid datetime
                df = df.dropna(subset=['datetime'])
                # Set datetime as the index
                df = df.set_index('datetime')
                # Drop original date columns
                df = df.drop(columns=required_columns)
                dataframes.append(df)
            except Exception as e:
                print(f"Error reading file {file}: {e}")
                continue

        if dataframes:
            self.raw_df = pd.concat(dataframes)
        else:
            print("No dataframes were read.")
            self.raw_df = pd.DataFrame()

    def process_dataframe(self):
        """
        Process the DataFrame to mark NaN values and clean data.
        """
        df = self.raw_df.copy()
        try:
            # Replace placeholder values with NaN
            df = df.replace(-999.99, np.nan)

            # Identify temperature sensor columns
            temperature_sensors = [col for col in df.columns if 'temp' in col.lower() or col.lower() == 'mcp9808']

            # Clean temperature data
            for sensor in temperature_sensors:
                df[sensor] = df[sensor].where(df[sensor].between(-45, 45), np.nan)

            # Optionally, create 'tas' as the average of available temperature sensors
            # Uncomment if needed
            # if temperature_sensors:
            #     df['tas'] = df[temperature_sensors].mean(axis=1)
            #     # Convert from Celsius to Kelvin
            #     df['tas'] = df['tas'] + 273.15

            self.processed_df = df



        except Exception as e:
            print(f"Error during processing: {e}")
            self.processed_df = df

    def resample_dataframe(self):
        """
        Resample the DataFrame from minutes to hourly intervals using custom aggregation.
        """
        df = self.processed_df.copy()

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
                # Exclude if the series has too many missing values
                if series.isna().sum() > 20:
                    return np.nan
                # Exclude if the series has fewer than 3 unique values (except for 'tipping')
                if var_name != 'tipping' and series.nunique() <= 3:
                    return np.nan

                if var_name == 'tipping':
                    # Sum for precipitation
                    return series.sum()
                elif var_name == 'wind_speed':
                    # Mean for wind speed
                    return series.mean()
                elif var_name == 'wind_dir':
                    # Circular mean for wind direction
                    return circular_mean(series)
                else:
                    # Median for other variables
                    return series.median()
            return aggregate

        if self.hourly:
            # Resample to hourly intervals with custom aggregation
            hourly_df = pd.DataFrame()
            print("Resampling data to hourly intervals...")
            for var_name in tqdm(df.columns, desc="Resampling variables"):
                hourly_series = df[var_name].resample('h').apply(custom_aggregation(var_name))
                hourly_df[var_name] = hourly_series
            self.resampled_df = hourly_df
        else:
            self.resampled_df = df


    def save_to_netcdf(self):
        """
        Create an xarray Dataset from the resampled DataFrame and save it to a NetCDF file.
        """
        df = self.resampled_df.copy()
        try:
            # Ensure the DataFrame is not empty
            if df is None or df.empty:
                print("No data to load into NetCDF.")
                return None

            # Prepare data variables for the dataset
            data_vars = {}
            for var_name in df.columns:
                # Reshape data to match dimensions
                data = df[var_name].values.reshape(-1, 1, 1)
                data_vars[var_name] = (["time", "lat", "lon"], data)

            # Use default coordinates if metadata is missing
            default_latitude = 0.0
            default_longitude = 0.0

            lat = self.meta_data.get('latitude', default_latitude)
            lon = self.meta_data.get('longitude', default_longitude)

            # Create the xarray Dataset with all variables
            ds = xr.Dataset(
                data_vars,
                coords={
                    "time": df.index.values,
                    "lat": [lat],
                    "lon": [lon],
                },
            )

            # Warning if lat or lon is not found
            if lat == default_latitude or lon == default_longitude:
                print("Warning: Latitude or Longitude not found in metadata. Using default values.")

            # Save the dataset to a NetCDF file
            output_path = os.path.join(self.target_directory, f"{self.name.lower()}.nc")
            print(f"Saving to {output_path}")

            # Remove existing file if necessary
            if os.path.exists(output_path):
                os.remove(output_path)

            ds.to_netcdf(output_path)
            print("NetCDF file saved successfully.")
            return output_path

        except Exception as e:
            print(f"Error saving NetCDF file: {e}")
            return None

    def execute(self):
        """
        Execute all steps to convert .dat files to NetCDF.
        """
        # Step 1: Extract metadata
        self.extract_meta_data()

        # Step 2 & 3: Read all .dat files and concatenate them
        self.read_and_concatenate_dat_files()
        if self.raw_df.empty:
            print("No data was read from the .dat files.")
            return

        if self.save_raw:
            # Optionally, save the raw data
            raw_csv_path = os.path.join(f"{self.raw_directory}", f"{self.name.lower()}_raw.csv")
            self.raw_df.to_csv(raw_csv_path)

        # Step 4: Process the DataFrame to mark NaN values
        self.process_dataframe()

        if self.save_processed:
            # Optionally, save the raw data
            processed_csv_path = os.path.join(f"{self.processed_directory}", f"{self.name.lower()}_processed.csv")
            self.processed_df.to_csv(processed_csv_path)


        # Step 5: Resample from minutes to hours using custom aggregation
        self.resample_dataframe()

        # Step 6: Save the processed data to a NetCDF file
        self.save_to_netcdf()

        print("Data processing complete.")

"""
# Instantiate the converter
name = "Vienna_AllVar"
directory = "measurements/Vienna"
target_directory = "station_data_as_nc"
hourly = True  # Set to False if you don't want to resample to hourly
keep_original = True  # Set to True if you want to keep raw data

converter = DatToNcConverter(
    name=name,
    directory=directory,
    target_directory=target_directory,
    hourly=hourly,
    keep_original=keep_original
)

# Run the conversion process
converter.execute()

# Access and inspect the raw DataFrame
if converter.keep_original:
    raw_df = converter.raw_df
    print("Raw DataFrame:")
    print(raw_df.info())
    print(raw_df.head())

# Access and inspect the processed DataFrame
processed_df = converter.processed_df
print("Processed DataFrame:")
print(processed_df.info())
print(processed_df.head())

"""