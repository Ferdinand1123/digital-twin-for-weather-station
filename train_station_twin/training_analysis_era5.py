import numpy as np
import pandas as pd
import xarray as xr
import utils.utils as utils
import numpy as np
import matplotlib.pyplot as plt
import os
from utils.utils import pretty_lat, pretty_lon

def era5_vs_reconstructed_comparison_to_df(era5_path, reconstructed_path, measurements_path, input_var_name='tas'):
    """
    Compares ERA5 data, reconstructed data, and measurements, and returns a DataFrame.
    
    Parameters:
    - era5_path: Path to the ERA5 input data (NetCDF file).
    - reconstructed_path: Path to the reconstructed data (NetCDF file).
    - measurements_path: Path to the ground truth measurements (NetCDF file).
    - input_var_name: Name of the variable to compare (default is 'tas').
    
    Returns:
    - df: DataFrame containing time series of ERA5 nearest point, reconstructed data, and measurements.
    """
    
    # Load datasets
    era5_data = xr.open_dataset(era5_path)
    reconstructed_data = xr.open_dataset(reconstructed_path)
    measurements_data = xr.open_dataset(measurements_path)    
    
    # Get station coordinates from measurements data
    station_lat = measurements_data.lat.values
    station_lon = measurements_data.lon.values

    # Find the nearest grid point in ERA5 data
    lon_nearest_idx, lat_nearest_idx = utils.find_nearest_lon_lat(
        era5_data.lon.values, era5_data.lat.values,
        station_lon, station_lat
    )
    
    # Extract ERA5 nearest point values
    era5_nearest_values = era5_data[input_var_name][:, lat_nearest_idx, lon_nearest_idx].values
    
    # Extract reconstructed data values
    reconstructed_data_values = reconstructed_data[input_var_name].stack(grid=['lat', 'lon']).values
    
    # Extract measurements data values
    measurements_data_values = measurements_data[input_var_name].values.flatten()
    
    # Get time axis
    time = era5_data['time'].values

    # Create DataFrame
    df = pd.DataFrame({
        'time': time,
        'era5_nearest': era5_nearest_values,
        'reconstructed_median': [np.median(x) for x in reconstructed_data_values],
        'measurements': measurements_data_values
    })
    
    # Set time as index
    df.set_index('time', inplace=True)
    
    return df



def plot_n_steps_of_df(df, era5_lats, era5_lons, station_lat, station_lon, as_delta=False, n=None, title=None, save_to=None):
    """
    Plots n steps of data from the DataFrame, comparing ERA5, reconstructed data, and measurements.
    
    Parameters:
    - df: DataFrame containing the data to plot.
    - era5_lats: Array of ERA5 latitudes.
    - era5_lons: Array of ERA5 longitudes.
    - station_lat: Latitude of the station.
    - station_lon: Longitude of the station.
    - as_delta: If True, plots the difference from measurements.
    - n: Number of time steps to plot (default is all).
    - title: Title of the plot.
    - save_to: Directory to save the plot (if None, the plot is shown but not saved).
    
    Returns:
    - path: Path to the saved plot (if saved), else None.
    """
    
    # Ensure station coordinates are within 0-360 degrees
    station_lon = station_lon % 360
    station_lat = station_lat % 360
    
    # Extract time values
    time = df.index.values
    total_time_steps = len(time)
    
    # Determine number of time steps to plot
    if n is None or n > total_time_steps:
        n = total_time_steps
    
    # Select a random starting point for the slice
    import random
    slice_start = random.randint(0, total_time_steps - n)
    time_slice = slice(slice_start, slice_start + n)
    
    # Slice the data
    time = time[time_slice]
    era5_nearest_values = df['era5_nearest'].values[time_slice]
    reconstructed_values = df['reconstructed_median'].values[time_slice]
    measurements_values = df['measurements'].values[time_slice]
    
    # Convert temperatures from Kelvin to Celsius if necessary
    if not as_delta:
        era5_nearest_values -= 273.15
        reconstructed_values -= 273.15
        measurements_values -= 273.15
    
    # Calculate RMSE and Correlation
    rmse_reconstructed = np.sqrt(np.nanmean((reconstructed_values - measurements_values) ** 2))
    rmse_era5_nearest = np.sqrt(np.nanmean((era5_nearest_values - measurements_values) ** 2))
    correlation_reconstructed = np.corrcoef(reconstructed_values, measurements_values)[0, 1]
    correlation_era5_nearest = np.corrcoef(era5_nearest_values, measurements_values)[0, 1]
    
    # Adjust values if plotting as delta
    if as_delta:
        era5_nearest_values -= measurements_values
        reconstructed_values -= measurements_values
        measurements_values = np.zeros_like(measurements_values)
        ylabel = "Delta (Data - Measurement) [°C]"
    else:
        ylabel = "Temperature at Surface [°C]"
    
    # Find nearest grid point indices
    nearest_lon_idx, nearest_lat_idx = utils.find_nearest_lon_lat(
        asc_lon_list=era5_lons, desc_lat_list=era5_lats,
        station_lon=station_lon, station_lat=station_lat
    )
    
    # Plotting
    plt.figure(figsize=(17.5, 10.5))
    plt.plot(time, era5_nearest_values, label=f"ERA5 Nearest Point ({pretty_lat(era5_lats[nearest_lat_idx], 4)}, {pretty_lon(era5_lons[nearest_lon_idx], 4)})", color="red")
    plt.plot(time, reconstructed_values, label="Reconstructed", color="blue")
    plt.plot(time, measurements_values, label="Measurements", color="black")
    
    plt.xticks(rotation=45)
    plt.ylabel(ylabel)
    plt.legend(loc='upper right')
    
    # Add RMSE and Correlation text
    textstr = '\n'.join((
        f"RMSE (Reconstructed): {rmse_reconstructed:.2f} °C",
        f"RMSE (ERA5 Nearest): {rmse_era5_nearest:.2f} °C",
        f"Correlation (Reconstructed): {correlation_reconstructed:.3f}",
        f"Correlation (ERA5 Nearest): {correlation_era5_nearest:.3f}"
    ))
    plt.gcf().text(0.02, 0.95, textstr, fontsize=10, verticalalignment='top')
    
    if title is not None:
        plt.title(title)
    
    plt.tight_layout()
    
    if save_to:
        if not os.path.exists(save_to):
            os.makedirs(save_to)
        filename = f"{title}.png" if title else "plot.png"
        path = os.path.join(save_to, filename)
        i = 1
        while os.path.exists(path):
            path = os.path.join(save_to, f"{os.path.splitext(filename)[0]}_{i}.png")
            i += 1
        plt.savefig(path)
        plt.close()
        return path
    else:
        plt.show()
        plt.close()
        return None


"""Step 1: Prepare the Data

Ensure that you have the following NetCDF files:

ERA5 input data (era5_data.nc)
Reconstructed data (reconstructed_data.nc)
Ground truth measurements (measurements_data.nc)

Step 2

df = era5_vs_reconstructed_comparison_to_df(
    era5_path='path/to/era5_data.nc',
    reconstructed_path='path/to/reconstructed_data.nc',
    measurements_path='path/to/measurements_data.nc',
    input_var_name='your_variable_name'  # Replace with your variable name
)

Step 3

# Load ERA5 data to get lats and lons
era5_data = xr.open_dataset('path/to/era5_data.nc')
era5_lats = era5_data.lat.values
era5_lons = era5_data.lon.values

# Station coordinates (ensure they are scalar values)
measurements_data = xr.open_dataset('path/to/measurements_data.nc')
station_lat = measurements_data.lat.values.item()
station_lon = measurements_data.lon.values.item()

Step 4

plot_n_steps_of_df(
    df=df,
    era5_lats=era5_lats,
    era5_lons=era5_lons,
    station_lat=station_lat,
    station_lon=station_lon,
    as_delta=False,  # Set to True if you want to plot differences
    n=100,           # Number of time steps to plot
    title='Temperature Comparison',
    save_to='path/to/save/plots'  # Set to None if you don't want to save
)
"""