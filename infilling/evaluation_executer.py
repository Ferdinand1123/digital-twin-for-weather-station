import tempfile
import subprocess
import xarray as xr
import tempfile
import pandas as pd
import numpy as np
import os

from crai.climatereconstructionai import evaluate

from era5.era5_download_hook import Era5DownloadHook
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc
from era5.era5_for_station import DownloadEra5ForStationGaps
from station.station import StationData

from utils.utils import FillAllTasWithValuesInNcFile

class EvaluationExecuter:
    def __init__(self, station: StationData, model_path, progress=None):
        self.model_path = model_path
        self.station = station
        self.progress = progress
        
        self.era5_file_name = "era5_merged.nc"
        self.cleaned_file_name = "cleaned.nc"
        self.subfolder_name = "test"    
            
        self.target_directory = tempfile.TemporaryDirectory()
        self.subfolder_path = self.prepare_target_directory()
       
        self.station_nc_file_path = self.station.export_as_nc(
            target_directory=self.target_directory.name + '/' + self.subfolder_name
        )
        self.era5_path = self.subfolder_path + '/' + self.era5_file_name
        self.cleaned_input_path = self.subfolder_path + '/' + self.cleaned_file_name
        
        self.output_dir = tempfile.TemporaryDirectory()
        self.log_dir = tempfile.TemporaryDirectory()
        

    def execute(self):
        self.get_era5_for_station()
        self.create_cleaned_nc_file()
        path = self.get_eval_args_txt()
        return self.crai_evaluate(path)     

    def prepare_target_directory(self):
        subprocess.run(f"mkdir {self.target_directory.name}/{self.subfolder_name}",
                       shell=True)
        return self.target_directory.name + '/' + self.subfolder_name

    def get_era5_for_station(self):
        print(self.station.metadata)
        
        era5_hook = Era5DownloadHook(lat=self.station.metadata.get("latitude"),
                                    lon=self.station.metadata.get("longitude"))
    
        temp_grib_dir = tempfile.TemporaryDirectory()
        
        DownloadEra5ForStationGaps(
            station=self.station,
            grib_dir_path=temp_grib_dir.name,
            hook=era5_hook,
            progress=self.progress
        )
          
        Era5DataFromGribToNc(
            temp_grib_dir.name, 
            era5_target_file_path=self.era5_path
        )
        
        temp_grib_dir.cleanup()
                  
    def create_cleaned_nc_file(self):   
        FillAllTasWithValuesInNcFile(
            values=np.nan,
            original_path=self.era5_path,
            save_to_path=self.cleaned_input_path
        )
        
        
    def get_eval_args_txt(self):
        eval_args_path = self.target_directory.name + '/eval_args.txt'
        eval_args = f"""
            --data-root-dir {self.target_directory.name}
            --model-dir {'/'.join(self.model_path.split('/')[0:-1])}
            --model-names {self.model_path.split('/')[-1]}
            --data-names {self.era5_file_name},{self.cleaned_file_name}
            --data-types tas,tas
            --n-target-data 1
            --pooling-layers 0
            --evaluation-dirs {self.output_dir.name}
            --log-dir {self.log_dir.name}
            --device cpu
            --n-filters 18
            --out-channels 1
            --loss-criterion 3
            --normalize-data
            --use-train-stats
            """
        
        print("eval args:", eval_args)
        
        with open(eval_args_path, 'w') as f:
            f.write(eval_args)
        return eval_args_path
    
    def crai_evaluate(self, eval_args_path): 
        if self.progress:
            self.progress.update_phase("Evaluating")    
        try:   
            print("Active conda environment:", os.environ['CONDA_DEFAULT_ENV'])
            evaluate(eval_args_path)
        except Exception as e:
            print("Error during evaluation:", e)
            print("Check the log files in", self.log_dir.name)
        if self.progress:
            self.progress.update_phase("")
        return self.output_dir.name + "/output_output.nc"
              
    def cleanup(self):
        self.target_directory.cleanup()
        self.output_dir.cleanup()
        self.log_dir.cleanup()