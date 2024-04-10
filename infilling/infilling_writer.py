import tempfile
import os
import xarray as xr
import pandas as pd
import uuid

from infilling.infilling_plotter import InfillingPlotter

class InfillingWriter():
    
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plotter = InfillingPlotter()
    
    def write_results(self, eval_results_path, station, plot=False):
            
        assert os.path.exists(eval_results_path), f"Output file {eval_results_path} does not exist"
        
        xarray = xr.open_dataset(eval_results_path)
        tas_values = xarray["tas"].values[:].mean(axis=(1,2))
        hours = xarray.time.values
        df = pd.DataFrame(data={"tas": tas_values}, index=hours)
        
        #sort the dataframe by index
        df = df.sort_index()
        
        plot_path = None
        
        if plot:
            self.plotter.pass_data(
                input_df=station.original_df,
                output_df=df
            )
            uid = str(uuid.uuid4())
            plot_path = self.temp_dir.name + "/" + uid + ".png"
            self.plotter.plot(path=plot_path)
            
        
        filled_in_df = station.original_df.copy()
        filled_in_df.update(df)

        filled_df_in_original_format = station.converter.transform_df_to_tas(
            filled_in_df
        )
        
        # naming convention YYYY-MM-DD_YYYY-MM-DD.dat
        first_timestamp_str = filled_df_in_original_format.index[0].strftime("%Y%m%d")
        last_timestamp_str = filled_df_in_original_format.index[-1].strftime("%Y%m%d")
        output_path = self.temp_dir.name + \
            "/infilled_" + first_timestamp_str + "_" + last_timestamp_str + ".dat"
        station.converter.export_a_df_to_tas(
            filled_df_in_original_format,
            output_path
        )
        
        return output_path, plot_path
  
    def cleanup(self):
        self.temp_dir.cleanup()