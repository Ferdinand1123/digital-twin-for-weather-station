import matplotlib
import pandas as pd

matplotlib.use('Agg')  # Set the backend to Agg (non-interactive)

import matplotlib.pyplot as plt

class InfillingPlotter():
    def __init__(self):
        self.input_df = None
        self.output_df = None
        self.full_df = None
        self.sensor_name = None
    
    def pass_data(self, input_df, output_df, sensor_name):
        self.input_df = input_df
        self.output_df = output_df
        self.sensor_name = sensor_name
        # rename the columns to measured and reconstructed
        self.output_df = self.output_df.rename(columns={f"filled_{self.sensor_name}": "Reconstructed"})
    
    def _transform_df(self):
        self.full_df = self.input_df.join(self.output_df, how="outer")
        
        # make sure the dataframes are sorted by index
        self.full_df = self.full_df.sort_index()
        
        # transfer from K to C
        self.full_df[self.sensor_name] = self.full_df[self.sensor_name] - 273.15
        self.full_df["Reconstructed"] = self.full_df["Reconstructed"] - 273.15
    
    def plot(self, path):
        self._transform_df()
        assert not self.full_df.empty, "Dataframe is empty"
        
        plt.plot(self.full_df.index, self.full_df[self.sensor_name], label="Measurements")
        plt.plot(self.full_df.index, self.full_df["Reconstructed"], label="Reconstructed")
        
        plt.legend()
        
        # rotate the x-axis labels
        plt.xticks(rotation=45)
        
        plt.savefig(path)
        plt.close()
        
    def plot_n_steps_of_filled_in_df(df, n=None, title=None, show_in_steps=False):

        time = df.index.values

        era5_nearest_values = df["era5_nearest"].values - 273.15
        reconstructed_median_values = df["filled_in_gaps"].values - 273.15
        
        measurements_values = df["measurements"].values - 273.15

        import random

        if n is None:
            n = len(df)
        
        break_loop = 0
        we_have_measurements_and_reconstructed_values_in_this_timeframe = False 
        while not we_have_measurements_and_reconstructed_values_in_this_timeframe and break_loop < 1000:
                
            # random slice of n consecutive datapoints
            
            slice_start = random.randint(0, len(time) - n)
            time_slice = slice(slice_start, slice_start + n)

            if n == len(df):
                we_have_measurements_and_reconstructed_values_in_this_timeframe = True
            else:
                break_loop += 1
                # check in time slice if we have measurements and reconstructed values
                we_have_measurements_and_reconstructed_values_in_this_timeframe = not (np.all(np.isnan(measurements_values[time_slice])) or np.all(np.isnan(reconstructed_median_values[time_slice])))
            
        time = time[time_slice]
        
        make_plots_with_era5 = [False, True, True] if show_in_steps else [True]
        make_plots_with_filled = [False, False, True] if show_in_steps else [True]
        for show_era, show_filled in zip(make_plots_with_era5, make_plots_with_filled):
        
            plt.ylabel("Temperature at surface [C°]")
            

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

        
            # figure size A4 landscape
            plt.gcf().set_size_inches(16, 8)
            
            if show_era:
                plt.plot(time, era5_nearest_values[time_slice], label="ERA5 nearest point", color="grey", linestyle="--" if n <= 168 else "-")  
            
            plt.plot(time, measurements_values[time_slice], label="Measurements", color="black", linestyle="-", marker="o" if n <= 168 else "")
        
            if show_filled:            
                plt.plot(time, reconstructed_median_values[time_slice], label="Reconstructed", color="#d13297", linestyle="-", marker="o" if n <= 168 else "")
        
            plt.legend()
            plt.show()
            
    def create_filled_in_gaps_df(full_era5_data, filled_gaps_data, measurements_data):

        def single_df(time, tas, name):
            df = pd.DataFrame()
            df["time"] = time
            df.set_index("time", inplace=True)
            df[name] = tas
            return df
        
        lon_left_idx, lon_right_idx, lon_nearest_idx = get_left_right_nearest_elem_in_sorted_array(era5_data.lon.values, station_lon % 360)
        lat_left_idx, lat_right_idx, lat_nearest_idx = get_left_right_nearest_elem_in_sorted_array(era5_data.lat.values, station_lat)

        era5_nearest_values = full_era5_data.variables["tas"][:, lon_nearest_idx, lat_nearest_idx]
        reconstructed_values = filled_gaps_data.variables["tas"].stack(grid=['lat', 'lon']).values
        reconstructed_values = [np.median(x) for x in reconstructed_values]
        
        measurements_values = measurements_data.variables["tas"].stack(grid=['lat', 'lon']).values
        measurements_values = [np.median(x) for x in measurements_values]
        
        era_df = single_df(full_era5_data.variables["time"], era5_nearest_values, "era5_nearest")
        reconstructed_df = single_df(filled_gaps_data.variables["time"], reconstructed_values, "filled_in_gaps")
        measurements_df = single_df(measurements_data.variables["time"], measurements_values, "measurements")
        
        # merge on time
        merged = pd.concat([era_df, reconstructed_df, measurements_df], axis=1)
        # drop rows where reconstructed and measurements are both nan simultaneously
        return merged.dropna(subset=["filled_in_gaps", "measurements"], how="all")
        
        