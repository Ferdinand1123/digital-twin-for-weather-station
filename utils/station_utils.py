
import os
import numpy as np
import pandas as pd
import xarray as xr
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess



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

def apply_aggregation(df):
    """
    Resample the DataFrame to hourly intervals and apply custom aggregation.
    """
    df = df.replace(-999.99, np.nan)

    # Replace 0.0 values with NaN and apply range filter for 'mcp9808' column
    if 'mcp9808' in df.columns:
        df['mcp9808'] = df['mcp9808'].replace(0.0, np.nan)
        df['mcp9808'] = df['mcp9808'].apply(lambda x: x if -45 <= x <= 45 else np.nan)

    if 'htu_hum' in df.columns:
        df['htu_hum'] = df['htu_hum'].apply(lambda x: x if 0 <= x <= 100 else np.nan)

    if 'bmp280_pres' in df.columns: # naive filter based on histogram Vienna and Barbados
        df['bmp280_pres'] = df['bmp280_pres'].apply(lambda x: x if 900 <= x <= 1200 else np.nan)
    
    if 'bmp180_pres' in df.columns: # naive filter based on histogram Marhsall
        df['bmp180_pres'] = df['bmp180_pres'].apply(lambda x: x if 700 <= x <= 1000 else np.nan)

    # Dictionary to store custom aggregations for each variable
    aggregation_dict = {var: custom_aggregation(var) for var in df.columns}

    # Resample DataFrame to hourly intervals and apply custom aggregation for each variable
    hourly_df = df.resample('h').apply(lambda x: pd.Series({var: func(x[var]) for var, func in aggregation_dict.items()}))

    return hourly_df


def plot_event_comparison(event_time, 
                          hourly_df, 
                          minutely_df, 
                          variable_hourly, 
                          variable_minute, 
                          era5_variable, 
                          lat, 
                          lon, 
                          time_window=pd.Timedelta(hours=6),
                          era5_ds=None, 
                          same_y_axis=False,
                          title_suffix="",
                          save_fig=False,
                          save_path=None):
    """
    Plots a comparison between hourly and minutely measurements alongside ERA5 data for a specified event.

    Parameters:
    -----------
    event_time : pd.Timestamp
        The timestamp of the event to analyze.

    hourly_df : pd.DataFrame
        DataFrame containing hourly measurements with a DateTime index.

    minutely_df : pd.DataFrame
        DataFrame containing minutely measurements with a DateTime index.

    era5_ds : xarray.Dataset
        Xarray Dataset containing ERA5 data.

    variable_hourly : str
        Column name in `hourly_df` for the hourly measurement (e.g., "mcp9808", "tipping").

    variable_minute : str
        Column name in `minutely_df` for the minutely measurement (e.g., "mcp9808", "tipping").

    era5_variable : str
        Variable name in `era5_ds` for ERA5 data (e.g., "t2m", "tp").

    lat : float
        Latitude for ERA5 data extraction.

    lon : float
        Longitude for ERA5 data extraction.

    time_window : pd.Timedelta, optional
        Duration before and after the event to include in the analysis. Default is 6 hours.

    same_y_axis : bool, optional
        If True, plots all measurements on the same y-axis. If False, uses separate y-axes. Default is False.

    title_suffix : str, optional
        Additional string to append to the plot title. Useful for distinguishing between events. Default is "".

    save_fig : bool, optional
        If True, saves the figure to `save_path`. Default is False.

    save_path : str, optional
        File path to save the figure. Required if `save_fig` is True.

    Returns:
    --------
    None
    """
    # Define the time window
    start_time = event_time - time_window
    end_time = event_time + time_window

    # Filter the DataFrames within the time window
    filtered_hourly = hourly_df.loc[start_time:end_time]
    filtered_minutely = minutely_df.loc[start_time:end_time]
    if era5_ds:
        # Extract ERA5 data for the specified location and time window
        era5_data = era5_ds[era5_variable].sel(lat=lat, lon=lon, method='nearest')
        era5_filtered = era5_data.sel(time=slice(start_time, end_time))
        era5_pd = era5_filtered.to_pandas()

    # Ensure that the indices align for plotting
    # If not, consider resampling or interpolating
    # For simplicity, we'll assume they are aligned or handle missing data gracefully

    # Start plotting
    plt.figure(figsize=(16, 8))

    if variable_hourly == "tipping": 
        unit = "mm"
    elif variable_hourly == "wind_speed":
        unit = "m/s"
    else:
        unit = "°C"

    if same_y_axis:
        # Plot all data on the same y-axis
        plt.plot(filtered_hourly.index, filtered_hourly[variable_hourly], 
                 color='mediumblue', label=f"Hourly {variable_hourly.capitalize()}", linewidth=2, marker='x')
        plt.plot(filtered_minutely.index, filtered_minutely[variable_minute], 
                 color='orange', label=f"Minutely {variable_minute.capitalize()}", linewidth=2, marker='o', alpha=0.5, markersize=2)
        if era5_ds:
            plt.plot(era5_pd.index, era5_pd.values, 
                    color='green', label=f"ERA5 {era5_variable.upper()}", linewidth=2, marker='x')

        plt.xlabel("Datetime", fontsize=12)
        plt.ylabel(f"{variable_hourly.capitalize()} in {unit}", fontsize=12)
        plt.title(f"Event: {event_time} - {title_suffix}", fontsize=14)
        plt.grid(alpha=0.7)
        plt.legend(loc="upper right", fontsize=12)
    else:
        # Create primary y-axis
        ax1 = plt.gca()
        ax1.plot(filtered_hourly.index, filtered_hourly[variable_hourly], 
                 color='mediumblue', label=f"Hourly {variable_hourly.capitalize()}", linewidth=2, marker='x')
        ax1.set_xlabel("Datetime", fontsize=12)
        ax1.set_ylabel(f"{variable_hourly.capitalize()} in {unit} (Hourly)", fontsize=12)
        ax1.tick_params(axis='y')
        ax1.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)

        # Plot minutely data on the same primary y-axis
        ax1.plot(filtered_minutely.index, filtered_minutely[variable_minute], 
                 color='orange', label=f"Minutely {variable_minute.capitalize()}", linewidth=2, marker='o', alpha=0.5, markersize=2)
        if era5_ds:
            # Create secondary y-axis for ERA5 data
            ax2 = ax1.twinx()
            ax2.plot(era5_pd.index, era5_pd.values, 
                    color='green', label=f"ERA5 {era5_variable.upper()}", linewidth=2, marker='x')
            ax2.set_ylabel(f"ERA5 {era5_variable.upper()} in {unit}", fontsize=12)
            ax2.tick_params(axis='y')

            # Combine legends from both axes
            lines_1, labels_1 = ax1.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right", fontsize=12)

        plt.title(f"Event: {event_time} - {title_suffix}", fontsize=14)

    # Improve x-axis date formatting
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Optionally save the figure
    if save_fig:
        if save_path is None:
            raise ValueError("save_path must be provided if save_fig is True.")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")

    # Display the plot
    plt.show()

def statistics(df, hourly = True): 
    # turn objec index into datetime index
    df.index = pd.to_datetime(df.index)

    df = df.sort_index()

    if hourly:
        full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='h')  # min stands for minute frequency
        time_unit  = "hour"
    else:
        # Create a complete minute-wise index
        full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='min')  # min stands for minute frequency
        time_unit  = "minute"
    
    # Reindex the dataframe to include all minutes, filling missing with NaN
    df = df.reindex(full_index) 

    # Total timespan/steps
    total_time = full_index.shape[0]

    # Actual measurements not Nan
    actual_measurements = df.notna().sum()
    relative_measurements = actual_measurements / total_time * 100

    # Non - zero measurments 
    zero_measurements = (df == 0).sum()
    nan_count = df.isna().sum()
    
    non_zero_measurements = actual_measurements - zero_measurements
    relative_non_zero_measurements = non_zero_measurements / total_time * 100
    nonzerorelativetoactual = non_zero_measurements / actual_measurements * 100
    
    print(f"Total {time_unit}s: {total_time}")
    print(f"Total {time_unit}s: 100%")
    print(f"Actual measurements: {actual_measurements}")
    print(f"Relative measurements: {relative_measurements:.2f}%")
    print(f"Non-zero measurements: {non_zero_measurements}")
    print(f"Relative non-zero measurements: {relative_non_zero_measurements:.2f}%")
    print(f"Non-zero relative to actual: {nonzerorelativetoactual:.2f}%")
    print(f"Zero measurements: {zero_measurements}")
    print(f"NaN measurements: {nan_count}")


def plot_hist(df, var_name, station, save=False, log=False):

    if var_name == 'tipping': 
        var_name_plot = 'precipitation'
    elif var_name == 'mcp9808':
        var_name_plot = 'temperature'
    elif var_name == 'htu_hum':
        var_name_plot = 'humidity'
    elif var_name == 'bmp280_pres':
        var_name_plot = 'pressure'
    else:
        var_name_plot = var_name

    staion_name = station
    # Create a histogram with log scale on the y-axis
    
    plt.figure(figsize=(14,6) )
    plt.hist(df[var_name], bins=50, log=log, color='mediumblue', edgecolor='black')     

    # Add labels and title
    plt.xlabel(f"{var_name_plot.capitalize()} Bins")
    plt.ylabel("Count")
    plt.title(f"{station.capitalize()}: Histogram of {var_name_plot.capitalize()}")
    plt.grid(True)

    if save:
    # Check if the 'eda' directory exists, if not, create it
        save_dir = "eda"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        plt.savefig(f"eda/{staion_name}_{var_name}_hist.png")
        print(f"Figure saved as eda/{staion_name}_{var_name}_hist.png")

    # Display the plot
    plt.show()


def plot_variable_over_time(df, var_name, year=None, title_add_on = None):
    """
    Plots a specified variable over time from a DataFrame.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing the data with a datetime index.
    variable (str): The name of the column to plot.
    year (int, optional): The specific year to plot. If None, plots all available data.
    """
    # Check if the variable exists in the DataFrame
    if var_name not in df.columns:
        raise ValueError(f"Variable '{var_name}' not found in DataFrame columns.")
    
    if var_name == 'tipping': 
        var_name_plot = 'precipitation'
        unit = "mm"
    elif var_name == 'mcp9808':
        var_name_plot = 'temperature'
        unit = "°C"
    elif var_name == 'htu_hum':
        var_name_plot = 'humidity'
        unit = "%"
    elif var_name == 'bmp280_pres':
        var_name_plot = 'pressure'
        unit = "hPa"
    else:
        var_name_plot = var_name
        unit = ""
    # Filter by year if specified
    if year is not None:
        df = df[df.index.year == year]
    
    # Plotting
    plt.figure(figsize=(14, 8))
    plt.plot(df.index, df[var_name], marker = "x", label=f"{var_name} over time", color='green')
    plt.title(f"{var_name_plot.capitalize()} {title_add_on} Over Time in {unit}" + (f" in {year}" if year else ""))
    plt.xlabel("Date")
    plt.xticks(rotation=45)  # Rotate x-axis values

    plt.ylabel(f"{var_name_plot.capitalize()} in {unit}")
    plt.legend()
    plt.grid(alpha=0.7)
    plt.show()

# Example usage:
# df should be a DataFrame with a datetime index and a column named 'temperature' (or any chosen variable).
# plot_variable_over_time(df, 'temperature', year=2023)


def calculate_uv(row):


    speed = row['wind_speed']
    direction = row['wind_dir']

    if direction == 0.0:
        direction = np.nan  # replace 0.0 with NaN, naive filtering

    # Check for NaN values
    if pd.notna(speed) and pd.notna(direction):
        direction_rad = np.radians(direction)
        u = -speed * np.sin(direction_rad)
        v = -speed * np.cos(direction_rad)
        return pd.Series([u, v], index=['u', 'v'])
    else:
        return pd.Series([np.nan, np.nan], index=['u', 'v'])


