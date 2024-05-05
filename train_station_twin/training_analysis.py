import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import utils.utils as utils

def era5_vs_reconstructed_comparision_to_df(era5_path, reconstructed_path, measurements_path):
    
    era5_data = xr.open_dataset(era5_path)
    reconstructed_data = xr.open_dataset(reconstructed_path)
    measurements_data = xr.open_dataset(measurements_path)    
    
    station_lat = measurements_data.lat.values[0]
    station_lon = measurements_data.lon.values[0]

    lon_nearest_idx, lat_nearest_idx = utils.find_nearest_lon_lat(
        era5_data.lon.values, era5_data.lat.values,
        station_lon, station_lat
    )
    
    era5_nearest_values = era5_data.variables["tas"][:, lon_nearest_idx, lat_nearest_idx]
    
    reconstructed_data_values = reconstructed_data.variables["tas"].stack(grid=['lat', 'lon']).values
    
    measurements_data_values = measurements_data.variables["tas"][...].mean(axis=(1,2))
    

    # timeaxis 
    time = era5_data.variables["time"][:]

    # create dataframe with all values
    df = pd.DataFrame()

    df["time"] = time

    # index should be time
    df.set_index("time", inplace=True)

    df["era5_nearest"] = era5_nearest_values
    df["reconstructed_median"] = [np.median(x) for x in reconstructed_data_values]
    df["reconstructed_with_time_context_median"] = [np.median(x) for x in reconstructed_data_values]
    df["measurements"] = measurements_data_values

    return df

def plot_n_steps_of_df(df, coords, as_delta, n=None, title=None, save_to=False):
    station_lon = coords.get("station_lon")
    station_lat = coords.get("station_lat")
    era5_lons = coords.get("era5_lons")
    era5_lats = coords.get("era5_lats")
    

    time = df.index.values
    if n is None:
        n = len(df)
    
    # random slice of n consecutive datapoints
    import random
    slice_start = random.randint(0, len(time) - n)
    time_slice = slice(slice_start, slice_start + n)

    time = time[time_slice]

    assert "reconstructed_median" in df.columns, "reconstructed_median column is missing"
    if not as_delta:
        era5_nearest_values = df["era5_nearest"].values - 273.15
        
        reconstructed_median_values = df["reconstructed_median"] - 273.15
        
        measurements_values = df["measurements"].values - 273.15
    else:
        era5_nearest_values = df["era5_nearest"].values
        reconstructed_median_values = df["reconstructed_median"]
        reconstructed_median_with_time_context_values = np.array(df["reconstructed_with_time_context_median"])
        measurements_values = np.array(df["measurements"].values)
    
    correlation_reconstructed = df["reconstructed_median"].corr(df["measurements"])
    correlation_era5_nearest = df["era5_nearest"].corr(df["measurements"])
  
    rmse_reconstructed = np.sqrt(np.nanmean((reconstructed_median_values[time_slice] - measurements_values[time_slice])**2))
    rmse_era5_nearest = np.sqrt(((era5_nearest_values[time_slice] - measurements_values[time_slice])**2).mean())
    
    
    if as_delta:
     #   era5_mid_values = era5_mid_values - measurements_values
        era5_nearest_values = era5_nearest_values - measurements_values
        reconstructed_median_values = reconstructed_median_values - measurements_values
        measurements_values = measurements_values - measurements_values  
        
        # y-axis title, temperature difference  
        plt.ylabel("Delta (data - measurement) [C°]")

    else:
        plt.ylabel("Temperature at surface [C°]")
    
    nearest_lon_idx, nearest_lat_idx = utils.find_nearest_lon_lat(
        asc_lon_list=era5_lons, desc_lat_list=era5_lats,
        station_lon=station_lon, station_lat=station_lat
    )
    
    plt.plot(time, era5_nearest_values[time_slice], label=f"ERA5 nearest point (lon: {(era5_lons[nearest_lon_idx] - 360):.3f}, lat: {era5_lats[nearest_lat_idx]:.3f})",
             color="red")
    # plt.plot(time, era5_mid_values[time_slice], label="ERA5 nearest 4 points")
    
    plt.plot(time, reconstructed_median_values[time_slice], label="Reconstructed for validation", color="blue")

    plt.plot(time, measurements_values[time_slice], label="Measurements", color="black")

    # x-axis labels 90 degrees
    plt.xticks(rotation=45)
    
    # title
    if title is not None:
        plt.title(title)
    
    
    # font size of legend
    plt.rcParams.update({'font.size': 10})
    
    # font size of axis labels
    plt.rcParams.update({'axes.labelsize': 12})
    
    # font size of title
    plt.rcParams.update({'axes.titlesize': 26})

    
    plt.legend(bbox_to_anchor=(1, 1.15), loc='upper right', borderaxespad=0.)
    
    # text below diagram with RMSE and Correlation in fontsize 10
    plt.text(0.06,0.95, (f"RMSE reconstructed: {rmse_reconstructed:.2f} C°\n" if rmse_reconstructed else "" ) +
             f"RMSE ERA5 nearest point: {rmse_era5_nearest:.2f} C°",
            
             fontsize=10, transform=plt.gcf().transFigure)
    
    plt.text(0.3, 0.95, (f"Correlation reconstructed: {correlation_reconstructed:.3f}\n" if correlation_reconstructed else "") +
             f"Correlation ERA5 nearest point: {correlation_era5_nearest:.3f}",
             
             fontsize = 10, transform=plt.gcf().transFigure)
    
    # figure size A4 landscape
    plt.gcf().set_size_inches(17.5, 10.5)
    
    
    plt.subplots_adjust(left=0.06)

    plt.show()
    
    if save_to:
        path = save_to + "/" + title + ".png"
        plt.savefig(path)
        plt.close()
        return path
    else:
        plt.close()
        return None

