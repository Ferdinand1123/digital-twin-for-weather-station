def era_vs_reconstructed_comparision_to_df(era5_data, reconstructed_data, measurements_data):

    lat_nearest_idx = np.searchsorted(list(reversed(xr_era5.lat.values)), station_lat)
    lat_nearest_idx = len(xr_era5.lat.values) - nearest_lat_idx
    lon_nearest_idx = np.searchsorted(xr_era5.lon.values, station_lon)  
    
    era5_nearest_values = era5_data.variables["tas"][:, lon_nearest_idx, lat_nearest_idx]
    
    reconstructed_data_values = reconstructed_with_time_data.variables["tas"].stack(grid=['lat', 'lon']).values
    
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
    df["reconstructed_with_time_context_median"] = [np.median(x) for x in reconstructed_with_time_data_values]
    df["measurements"] = measurements_data_values

    return df

def plot_n_steps_of_df(df, as_delta, n=None, title=None, plot_trailing_time=False):

    plot_trailing_time = plot_trailing_time and not has_no_time_context

    time = df.index.values
    if n is None:
        n = len(df)
    
    # random slice of n consecutive datapoints
    import random
    slice_start = random.randint(0, len(time) - n)
    time_slice = slice(slice_start, slice_start + n)

    time = time[time_slice]

    if not as_delta:
        era5_nearest_values = df["era5_nearest"].values - 273.15
        if "reconstructed_median" in df.columns and not df["reconstructed_median"].isnull().all():
            reconstructed_median_values = df["reconstructed_median"] - 273.15
        else: 
            reconstructed_median_values = None
        reconstructed_median_with_time_context_values = df["reconstructed_with_time_context_median"] - 273.15
        
        measurements_values = df["measurements"].values - 273.15
    else:
        era5_nearest_values = df["era5_nearest"].values
        if "reconstructed_median" in df.columns and not df["reconstructed_median"].isnull().all():
            reconstructed_median_values = df["reconstructed_median"]
        else: 
            reconstructed_median_values = None
        reconstructed_median_with_time_context_values = np.array(df["reconstructed_with_time_context_median"])
        
        measurements_values = np.array(df["measurements"].values)
    
    if reconstructed_median_values is not None:
        correlation_reconstructed = df["reconstructed_median"].corr(df["measurements"])
    else:
        correlation_reconstructed = None
    correlation_reconstructed_with_time_context = df["reconstructed_with_time_context_median"].corr(df["measurements"])
    correlation_era5_nearest = df["era5_nearest"].corr(df["measurements"])
  
    if reconstructed_median_values is not None:
        rmse_reconstructed = np.sqrt(np.nanmean((reconstructed_median_values[time_slice] - measurements_values[time_slice])**2))
    else:
        rmse_reconstructed = None
    rmse_reconstructed_with_time_context = np.sqrt(np.nanmean((reconstructed_median_with_time_context_values[time_slice] - measurements_values[time_slice])**2)) 
    rmse_era5_nearest = np.sqrt(((era5_nearest_values[time_slice] - measurements_values[time_slice])**2).mean())
    
    
    
    if as_delta:
     #   era5_mid_values = era5_mid_values - measurements_values
        era5_nearest_values = era5_nearest_values - measurements_values
        if reconstructed_median_values is not None:
            reconstructed_median_values = reconstructed_median_values - measurements_values
        reconstructed_median_with_time_context_values = reconstructed_median_with_time_context_values - measurements_values
        measurements_values = measurements_values - measurements_values  
        
        # y-axis title, temperature difference  
        plt.ylabel("Delta (data - measurement) [C°]")

    else:
        plt.ylabel("Temperature at surface [C°]")
    
    _, _, nearest_lon_idx = get_left_right_nearest_elem_in_sorted_array(era5_data.lon.values, station_lon % 360)
    _, _, nearest_lat_idx = get_left_right_nearest_elem_in_sorted_array(era5_data.lat.values, station_lat) 
    plt.plot(time, era5_nearest_values[time_slice], label=f"ERA5 nearest point (lon: {(era5_data.lon.values[nearest_lon_idx] - 360):.3f}, lat: {era5_data.lat.values[nearest_lat_idx]:.3f})",
             color="red")
    # plt.plot(time, era5_mid_values[time_slice], label="ERA5 nearest 4 points")
    
    if reconstructed_median_values is not None:
        plt.plot(time, reconstructed_median_values[time_slice], label="Reconstructed for validation", color="blue")
    if plot_trailing_time:
        plt.plot(time, reconstructed_median_with_time_context_values[time_slice], label="Reconstructed for val. using also ERA5 step before & after", color="green") 

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

    plt.legend()
    # position legend below chart to the right
    plt.legend(bbox_to_anchor=(1, 1.15), loc='upper right', borderaxespad=0.)
    
        
    # text below diagram with RMSE and Correlation in fontsize 10
    plt.text(0.1,0.95, (f"RMSE reconstructed: {rmse_reconstructed:.2f} C°\n" if rmse_reconstructed else "" ) +
             (f"RMSE reconstr. (time context): {rmse_reconstructed_with_time_context:.2f} C°\n" if plot_trailing_time  else "") + 
             f"RMSE ERA5 nearest point: {rmse_era5_nearest:.2f} C°",
            
             fontsize=10, transform=plt.gcf().transFigure)
    
    plt.text(0.3, 0.95, (f"Correlation reconstructed: {correlation_reconstructed:.3f}\n" if correlation_reconstructed else "") +
             (f"Correlation reconstr. (time context): {correlation_reconstructed_with_time_context:.3f}\n" if plot_trailing_time else "") + 
             f"Correlation ERA5 nearest point: {correlation_era5_nearest:.3f}",
             
             fontsize = 10, transform=plt.gcf().transFigure)
    
    # figure size A4 landscape
    plt.gcf().set_size_inches(16, 8)
    
    plt.show()


