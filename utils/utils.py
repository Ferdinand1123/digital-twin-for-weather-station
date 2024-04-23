import numpy as np
import xarray as xr
from station.data_submission import DataSubmission, data_storage
import os

class FillAllTasWithValuesInNcFile():
    def __init__(self, values, original_path, save_to_path):
        if not isinstance(values, list) and not isinstance(values, np.ndarray):
            self.values = [values]
        else:
            self.values = values

        self.original_path = original_path
        self.save_to_path = save_to_path
        self._create_filled_nc_files()

    def _create_filled_nc_files(self):
        if len(self.values) == 1:
            value = self.values[0]
            with xr.open_dataset(self.original_path) as ds:
                ds['tas'].values[:] = value
                ds.to_netcdf(self.save_to_path)
        else:
            # Get the shape of the 'tas' variable
            with xr.open_dataset(self.original_path) as ds:
                tas_shape = ds['tas'].shape

                # Reshape self.values to match the shape of 'tas'
                repeated_values = self.values[:, np.newaxis, np.newaxis] * np.ones(
                    (len(self.values), 8, 8))

                # Assign the repeated values to the 'tas' variable
                ds['tas'].values[:, :, :] = repeated_values
                ds.to_netcdf(self.save_to_path)

        return self.save_to_path


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
        if self.folder_path:
            if not os.path.exists(self.folder_path):
                self.percentage = 0
            else:
                self.percentage = len(os.listdir(self.folder_path)) * 5
        if self.phase == "":
            return ""
        elif self.percentage == "":
            return f"{self.phase}..."
        else:
            return f"{self.phase}... {self.percentage}%"

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
        title += f"\n{dataset.time.values[time_index].astype('datetime64[s]').astype('O')}"

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

            # Show the plot
            plt.show()
    return time_index_list


def pretty_lat(lat):
    lat = round(lat, 3)
    if lat > 0:
        return f"{abs(lat)}°N"
    else:
        return f"{abs(lat)}°S"


def pretty_lon(lon):
    lon = (lon + 180) % 360 - 180
    lon = round(lon, 3)
    if lon > 0:
        return f"{abs(lon)}°E"
    else:
        return f"{abs(lon)}°W"


def find_nearest_lon_lat(asc_lon_list, desc_lat_list, station_lon, station_lat):
    lat_nearest_idx = np.searchsorted(
        list(reversed(desc_lat_list)), station_lat)
    lat_nearest_idx = len(desc_lat_list) - lat_nearest_idx
    lon_nearest_idx = np.searchsorted(asc_lon_list, station_lon)
    return lon_nearest_idx, lat_nearest_idx
