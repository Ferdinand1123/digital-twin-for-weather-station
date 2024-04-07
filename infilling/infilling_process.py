import tempfile
import subprocess
import xarray as xr
import numpy
import pandas as pd
import os


from ..crai.climatereconstructionai import evaluate
from ..era5.era5_download_hook import Era5DownloadHook
from ..era5.era5_from_grip_to_nc import Era5DataFromGribToNc
from ..station.station import StationData

from ..utils.cleaned_copy import CreateCleanedCopy


class InfillingProcess:
    def __init__(self, station: StationData, model_path):
        self.model_path = model_path
        self.station = station
            
        self.era5_file_name = "era5_merged.nc"
        self.cleaned_file_name = "cleaned.nc"
        self.subfolder_name = "test"    
            
        self.target_directory = tempfile.TemporaryDirectory()
        self.prepare_target_directory()
       
        self.station_nc_file_path = self.station.export_as_nc(
            target_directory=self.target_directory.name + '/' + self.subfolder_name
        )
        self.era5_path = self.target_directory.name + '/' + \
            self.subfolder_name + '/' + self.era5_file_name
        self.cleaned_input_path = self.target_directory.name + '/' + \
            self.subfolder_name + '/' + self.cleaned_file_name
        self.eval_args_path = self.target_directory.name + '/eval_args.txt'
        
        self.output_dir = tempfile.TemporaryDirectory()
        

    def execute(self):
        self.get_era5_for_station()
        self.get_eval_args_txt()
        self.crai_evaluate()     

    def prepare_target_directory(self):
        subprocess.run(f"mkdir {self.target_directory.name}/{self.subfolder_name}",
                       shell=True)

    def get_era5_for_station(self):
        hours_missing = self.station.find_gaps()
        print(self.station.metadata)
        era5_hook = Era5DownloadHook(lat=self.station.metadata.get("latitude"),
                                    lon=self.station.metadata.get("longitude"))
    
        temp_grib_dir = tempfile.TemporaryDirectory()
        
        grouped_hours_by_day = {}
        
        if not hours_missing:
            print("No missing hours")
            return
        
        for hour in hours_missing:
            if hour.date() not in grouped_hours_by_day:
                grouped_hours_by_day[hour.date()] = []
            grouped_hours_by_day[hour.date()].append(hour.hour)
        
        for day, hours in grouped_hours_by_day.items():
            era5_hook.download_hours_on_same_day(
                day.year,
                day.month,
                day.day,
                hours,
                temp_grib_dir.name
            )
          
        Era5DataFromGribToNc(
            temp_grib_dir.name, 
            era5_file_path=self.era5_path
        )
          
            
        cleaned_nc_file_with_era5_dimensions = CreateCleanedCopy(
            original_path=self.era5_path,
            cleaned_path=self.cleaned_input_path
        )
        
        
        
    def get_eval_args_txt(self):
        eval_args = f"""
            --data-root-dir {self.target_directory.name}
            --model-dir {'/'.join(self.model_path.split('/')[0:-1])}
            --model-names {self.model_path.split('/')[-1]}
            --data-names {self.era5_file_name},{self.cleaned_file_name}
            --data-types tas,tas
            --n-target-data 1
            --pooling-layers 0
            --evaluation-dirs {self.output_dir.name}
            --device cpu
            --n-filters 18
            --out-channels 1
            --loss-criterion 3
            --normalize-data
            --use-train-stats
            """
        
        print("####### eval args", eval_args)
        
        with open(self.eval_args_path, 'w') as f:
            f.write(eval_args)
        return self.eval_args_path
    
    def crai_evaluate(self):     
        evaluate(self.eval_args_path)
        
    def write_results(self, plotter=False):
        eval_results_path = self.output_dir.name + "/output_output.nc"
        assert os.path.exists(eval_results_path), f"Output file {eval_results_path} does not exist"
        xarray = xr.open_dataset(eval_results_path)
        tas_values = xarray["tas"].values[:].mean(axis=(1,2))
        hours = xarray.time.values
        df = pd.DataFrame(data={"tas": tas_values}, index=hours)
        
        #sort the dataframe by index
        df = df.sort_index()
        
        if plotter:
            plotter.pass_data(
                input_df=self.station.original_df,
                output_df=df
            )
        
        
        filled_in_df = self.station.original_df.copy()
        filled_in_df.update(df)

        filled_df_in_original_format = self.station.converter.transform_df_to_tas(
            filled_in_df
        )
        # naming convention YYYY-MM-DD_YYYY-MM-DD.dat
        first_timestamp_str = filled_df_in_original_format.index[0].strftime("%Y%m%d")
        last_timestamp_str = filled_df_in_original_format.index[-1].strftime("%Y%m%d")
        output_path = self.output_dir.name + \
            "/" + first_timestamp_str + "_" + last_timestamp_str + ".dat"
        self.station.converter.export_a_df_to_tas(
            filled_df_in_original_format,
            output_path
        )
        return output_path
        
    def cleanup(self):
        if self.target_directory:
            self.target_directory.cleanup()
        if self.output_dir:
            self.output_dir.cleanup()