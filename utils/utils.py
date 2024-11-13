import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from sklearn.metrics import r2_score, mean_squared_error
from scipy.stats import pearsonr

class FillAllTasWithValuesInNcFile():
    def __init__(self, var, values, original_path, save_to_path):
        if not isinstance(values, list) and not isinstance(values, np.ndarray):
            self.values = [values]
        else:
            self.values = values

        self.var = var
        self.original_path = original_path
        self.save_to_path = save_to_path
        self._create_filled_nc_files()

    def _create_filled_nc_files(self):
        if len(self.values) == 1:
            value = self.values[0]
            with xr.open_dataset(self.original_path) as ds:
                ds[self.var].values[:] = value
                ds.to_netcdf(self.save_to_path)
        else:
            # Get the shape of the 'tas' variable
            with xr.open_dataset(self.original_path) as ds:
                tas_shape = ds[self.var].shape

                # Reshape self.values to match the shape of 'tas'
                repeated_values = self.values[:, np.newaxis, np.newaxis] * np.ones(
                    (len(self.values), 8, 8))

                # Assign the repeated values to the 'tas' variable
                ds[self.var].values[:, :, :] = repeated_values
                ds.to_netcdf(self.save_to_path)

        return self.save_to_path

class Fill_NC_With_Station_Values():
    def __init__(self, var, measurements_values, original_path, save_to_path, size=8):
        """
        Args:
            var: variable to fill str 
            measurements_values:  station measurment values to fill, list or numpy array
            original_path: path to file with original size, str
            save_to_path: path to output, str
            size: size of the grid, default is 8, int

        Returns:
            bool: True if aligned, False otherwise. 
        """
        # Initialize the class with variable name, measurement values, paths, and grid size
        # Ensure measurements_values is a list or numpy array for consistency
        if not isinstance(measurements_values, (list, np.ndarray)):
            self.measurements_values = [measurements_values]
        else:
            self.measurements_values = measurements_values

        self.size = size
        self.var = var
        self.original_path = original_path
        self.save_to_path = save_to_path
        self._create_filled_nc_file()

    def _create_filled_nc_file(self):
        # Open the original NetCDF file
        with xr.open_dataset(self.original_path) as ds:
            # Check if we have a single value or multiple values to fill
            if len(self.measurements_values) == 1:
                # Single value: fill the entire variable with this constant
                ds[self.var].values[:] = self.measurements_values[0]
            else:
                # Multiple values: expand each to a grid and assign to variable
                repeated_values = np.array(self.measurements_values)[:, None, None] * np.ones((len(self.measurements_values), self.size, self.size))
                ds[self.var].values[:, :, :] = repeated_values

            # Save modified data to the new NetCDF file
            ds.to_netcdf(self.save_to_path)

class ProgressStatus():

    def __init__(self):
        self.phase = ""
        self.percentage = ""
        self.folder_path = ""

    def update_phase(self, phase):
        if self.phase != phase:
            self.phase = phase
            self.percentage = ""
            self.folder_path = ""
        return

    def update_percentage(self, percent):
        if self.percentage != percent:
            self.percentage = percent
        return

    def __repr__(self):
        return self.__str__()

    def __str__(self):   
        if self.phase == "":
            return ""
        if self.folder_path:
            if not os.path.exists(self.folder_path):
                self.percentage = 0
            else:
                self.percentage = min(100, len(os.listdir(self.folder_path)) * 1) # if log interval is equal to 1%
        elif self.percentage == "":
            return f"{self.phase}..."
        return f"{self.phase}... {int(self.percentage)}%"

def plot_n_steps_of_area_from_nc_file(path, n=1, vars="tas", title="", vmin=None, vmax=None):

    dataset = xr.open_dataset(path)

    n = min(n, dataset.time.size)
    time_index_list = np.random.choice(dataset.time.size, n, replace=False)

    lat_slice = slice(None)
    lon_slice = slice(None)
    _lon = dataset.lon.values[lon_slice]
    _lat = dataset.lat.values[lat_slice]

    # if not list make it a list
    if not isinstance(vars, list):
        vars = [vars]

    for time_index in time_index_list:
        # set title
        title = f"\n{dataset.time.values[time_index].astype('datetime64[s]').astype('O')}"

        # subtitle lat lon area
        subtitle = f"\nLat: {pretty_lat(_lat[0])} to {pretty_lat(_lat[-1])}" + \
            f"\nLon: {pretty_lon(_lon[0])} to {pretty_lon(_lon[-1])}"

        for var in vars:

            # plot
            fig, ax = plt.subplots(
                subplot_kw={'projection': ccrs.PlateCarree()})
            # Plot the temperature data with a quadratic colormap
            _data = dataset.variables[var].values[time_index,
                                                  lat_slice, lon_slice]
            pcm = ax.pcolormesh(_lon, _lat, _data, cmap='viridis',
                                shading='auto', vmin=vmin, vmax=vmax)

            # Add coastlines
            ax.coastlines()

            # Add colorbar
            cbar = plt.colorbar(pcm, ax=ax, label='Temperature')

            # Set labels and title
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            plt.title(title + (f"\n[{var}]" if len(vars) > 1 else ""))

            # position title a higher
            plt.subplots_adjust(top=1)

            # Add subtitle
            plt.figtext(0.125, 0.05, subtitle, wrap=True,
                        horizontalalignment='left', fontsize=12)
            
            # fig size
            fig.set_size_inches(10, 10)

            # Show the plot
            plt.show()
            
    return time_index_list


def pretty_lat(lat, precision=0):
    lat = round(lat, max(3, precision))
    if lat > 0:
        return f"{abs(lat)}°N"
    else:
        return f"{abs(lat)}°S"


def pretty_lon(lon, precision=0):
    print("displaying lon:", lon)
    lon = (lon + 180) % 360 - 180
    lon = round(lon, max(3, precision))
    print("as", lon)
    if lon > 0:
        return f"{abs(lon)}°E"
    else:
        return f"{abs(lon)}°W"


def find_nearest_lon_lat(asc_lon_list, asc_lat_list, station_lon, station_lat):
    print("search:", station_lon , " in asc_lon_list:", asc_lon_list)
    
    # Find the nearest longitude index
    lon_nearest_idx = np.searchsorted(asc_lon_list, station_lon)
    if lon_nearest_idx == len(asc_lon_list):
        lon_nearest_idx -= 1
    elif lon_nearest_idx > 0 and (abs(station_lon - asc_lon_list[lon_nearest_idx-1]) < abs(station_lon - asc_lon_list[lon_nearest_idx])):
        lon_nearest_idx -= 1
    print("nearest_lon_idx:", lon_nearest_idx)
    
    # Find the nearest latitude index
    lat_nearest_idx = np.searchsorted(asc_lat_list, station_lat)
    if lat_nearest_idx == len(asc_lat_list):
        lat_nearest_idx -= 1
    elif lat_nearest_idx > 0 and (abs(station_lat - asc_lat_list[lat_nearest_idx-1]) < abs(station_lat - asc_lat_list[lat_nearest_idx])):
        lat_nearest_idx -= 1
    print("nearest_lat_idx:", lat_nearest_idx)
    
    return lon_nearest_idx, lat_nearest_idx


def plot_measurements_df(df):
    fig, ax = plt.subplots(1, 1)
    ax.plot(df.index, df.tas, label="tas")
    ax.legend()
    
    # turn x-axis labels
    plt.xticks(rotation=45)
    
    # set title
    plt.title("Temperature over time")
    
    # figure size
    fig.set_size_inches(18.5, 10.5)
    
    plt.show()


def aggregate_per_timestep_xr(data: xr.Dataset, methods: list = ["median"], variables: list = None) -> xr.Dataset:
    """
    Aggregate specified variables in an xarray Dataset along the 'lat' and 'lon' dimensions 
    using multiple specified methods, returning the result as an xarray.Dataset.
    
    Parameters:
    data (xr.Dataset): Input Dataset with multiple variables and 'lat' and 'lon' dimensions.
    methods (list): List of aggregation methods to apply.
                    Options include "mean", "median", "sum", "max", "min", "std", and "var".
    variables (list, optional): List of variable names to aggregate. 
                                If None, all variables in the dataset are aggregated.
    
    Returns:
    xr.Dataset: Dataset with each aggregation result as a separate variable.
                Dimensions are 'time' and 'variable'.
    
    Example:
    aggregated_output_output = aggregate_per_timestep_xr(output_output, methods=["mean", "std", "var"], variables=["wind_speed", "t2m"])
    """
    # Use specified variables or default to all variables in the dataset
    variables = variables or list(data.data_vars)
    
    # Initialize an empty dictionary to store aggregated DataArrays
    result_dict = {}

    # Loop over each selected variable in the dataset
    for var in variables:
        if var not in data:
            raise ValueError(f"Variable '{var}' is not in the dataset.")
        
        # Loop over each specified aggregation method
        for method in methods:
            # Compute the aggregation along 'lat' and 'lon' dimensions
            if method == "median":
                aggregated_data = data[var].median(dim=["lat", "lon"])
            elif method == "mean":
                aggregated_data = data[var].mean(dim=["lat", "lon"])
            elif method == "sum":
                aggregated_data = data[var].sum(dim=["lat", "lon"])
            elif method == "max":
                aggregated_data = data[var].max(dim=["lat", "lon"])
            elif method == "min":
                aggregated_data = data[var].min(dim=["lat", "lon"])
            elif method == "std":
                aggregated_data = data[var].std(dim=["lat", "lon"])
            elif method == "var":
                aggregated_data = data[var].var(dim=["lat", "lon"])
            else:
                raise ValueError(f"Unsupported aggregation method: {method}.")

            # Add the aggregated data to the result dictionary
            result_dict[f"{method}_{var}"] = aggregated_data

    # Combine all aggregated data arrays into a single Dataset
    result_ds = xr.Dataset(result_dict)

    return result_ds





def calculate_metrics(ds1: xr.DataArray, ds2: xr.DataArray, var: str, output_path: str = None) -> dict:
    """
    Calculate R^2, RMSE, and Pearson correlation between two xarray DataArrays.
    Optionally write the results to a text file.
    
    Parameters:
    ds1 (xr.DataArray): First DataArray (e.g., ground truth).
    ds2 (xr.DataArray): Second DataArray (e.g., predictions).
    var (str): Variable name to select within the DataArrays.
    output_path (str, optional): Path to save the metrics in a text file. If None, no file is saved.

    Returns:
    dict: Dictionary containing R^2, RMSE, and Pearson correlation.

    Example:
    metrics = calculate_metrics(aggregated_output_output.mean_wind_speed, aggregated_output_gt.mean_wind_speed, var="temperature", output_path="metrics_results.txt")
    """
    # Align datasets to ensure they share the same time axis
    ds1, ds2 = xr.align(ds1, ds2)

    # Select the variable and flatten data, removing NaNs for comparison
    ds1_flat = ds1.values.flatten()
    ds2_flat = ds2.values.flatten()

    # Remove NaN values from both arrays
    mask = ~np.isnan(ds1_flat) & ~np.isnan(ds2_flat)
    ds1_flat = ds1_flat[mask]
    ds2_flat = ds2_flat[mask]

    # Calculate metrics
    r2 = r2_score(ds1_flat, ds2_flat)
    rmse = np.sqrt(mean_squared_error(ds1_flat, ds2_flat))
    pearson_corr, _ = pearsonr(ds1_flat, ds2_flat)

    # Compile metrics into a dictionary
    metrics = {
        "R^2": r2,
        "RMSE": rmse,
        "Pearson Correlation": pearson_corr
    }

    # Optionally write metrics to a text file
    if output_path:
        with open(output_path, "w") as f:
            for key, value in metrics.items():
                f.write(f"{key}: {value:.4f}\n")

    return metrics