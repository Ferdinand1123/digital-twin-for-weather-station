from station.station import StationData
from era5.era5_download_hook import Era5DownloadHook
from era5.era5_for_station import DownloadEra5ForStation, Era5ForStationCropper
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc


from utils.utils import FillAllTasWithValuesInNcFile, ProgressStatus

from crai.climatereconstructionai import train

import subprocess
import asyncio
import tempfile
import os
import shutil

import pty

import xarray as xr
import re

import numpy as np
import time

class TrainingExecutor_era5():

    def __init__(self, station: StationData, progress: ProgressStatus, iterations, local=False, era5_path=None):
        self.station = station
        self.era5_path_provided = era5_path is not None # updated by me
        self.era5_path = era5_path  # Path to existing ERA5 data, if provided
        assert station.name is not None
        assert station.metadata is not None
        assert station.metadata.get("latitude") is not None
        assert station.metadata.get("longitude") is not None
        if local:
            # make a temporary directory in the current working directory with the station name and the current time as YYYY-MM-DD_HH-MM-SS
            temp_path = f'./executed_trainings/{station.name}_{time.strftime("%Y%m%d-%H%M")}'
            os.mkdir(temp_path)
            self.target_dir = tempfile.TemporaryDirectory(dir=temp_path, prefix='target_')
            self.temp_dir = tempfile.TemporaryDirectory(dir=temp_path, prefix='temp_')
            self.model_dir = tempfile.TemporaryDirectory(dir=temp_path, prefix='model_')
            self.log_dir = tempfile.TemporaryDirectory(dir=temp_path, prefix='log_')
        else:
            self.target_dir = tempfile.TemporaryDirectory()
            self.temp_dir = tempfile.TemporaryDirectory()
            self.model_dir = tempfile.TemporaryDirectory()
            self.log_dir = tempfile.TemporaryDirectory()

        self.era5_file_name = "era5_merged.nc"
        self.expected_output_file_name = "cleaned.nc"
        self.subfolder_name = "train"
        self.model_dir_subfolder_name = "ckpt"

        self.prepare_target_directory()
        self.station_nc_file_path = self.station.export_as_nc(
            target_directory=self.target_dir.name + '/' + self.subfolder_name
        )

        if era5_path is None:
            self.era5_path = self.target_dir.name + '/' + self.subfolder_name + '/' + self.era5_file_name
        else:
            self.era5_path = self.target_dir.name + '/' + self.subfolder_name + '/' + self.era5_file_name
            # The execute method will copy the provided ERA5 data to self.era5_path            
        self.expected_output_path = self.target_dir.name + '/' + \
            self.subfolder_name + '/' + self.expected_output_file_name
        self.train_args_path = self.target_dir.name + '/train_args.txt'

        self.progress = progress
        self.total_iterations = iterations

    def execute(self):
        if not self.era5_path_provided:
            self.get_era5_for_station()
        else: 
            temp_path = os.path.join(self.target_dir.name, self.temp_dir.name, self.era5_file_name)

            shutil.copy(self.era5_path, temp_path)
            
            self.transform_era5_for_station()

        self.progress.update_phase("Preparing Training Set")
        self.transform_station_to_expected_output()
        self.copy_train_folder_as_val_folder()
        path = self.get_train_args_txt()
        model_dir_path = self.crai_train(path)
        self.progress.update_phase("")
        return self.make_zip_folder(model_dir_path)
    
    def get_sbatch_script(self):
        # make subdirectory for slurm logs
        user_home_dir = os.path.expanduser("~")
        script_txt = f'''#!/usr/bin/env bash

#SBATCH -J crai-train
#SBATCH --output {self.temp_dir.name}/slurm_logs/crai_crai-train_%j.log
#SBATCH -p gpu
#SBATCH -A bm1159
#SBATCH --time=12:00:00
#SBATCH --mem=485G
#SBATCH --exclusive
#SBATCH --constraint a100_80

cd {os.getcwd()}
module load python3

# Initialize Conda (add this line)
eval "$(conda shell.bash hook)"

conda activate {user_home_dir}/.conda/envs/crai

python -m climatereconstructionai.train --load-from-file {self.get_train_args_txt()}
'''
        # save script to file
        script_path = self.temp_dir.name + '/train_script.sh'
        with open(script_path, 'w') as f:
            f.write(script_txt)
        subprocess.run(['chmod', '+x', script_path])
        return script_path

    def execute_with_sbatch(self):
        # unsing already cropped data
        if not self.era5_path_provided:
            self.get_era5_for_station()
        else: 
            temp_path = os.path.join(self.target_dir.name, self.temp_dir.name, self.era5_file_name)

            shutil.copy(self.era5_path, temp_path)        
            self.transform_station_to_expected_output()
        self.copy_train_folder_as_val_folder()

        result = subprocess.run(['sbatch', self.get_sbatch_script()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Check if the command executed successfully
        if result.returncode == 0:
            # Extract the job ID from the output
            output_lines = result.stdout.splitlines()
            if output_lines:
                # The job ID is typically in the first line of the output
                job_id_line = output_lines[0]
                # Split the line by whitespace and get the last element (job ID)
                job_id = job_id_line.split()[-1]
                return job_id
            else:
                print("No output received from sbatch command.")
                return
        else:
            print("Error submitting batch job:", result.stderr.strip())
            return

    def transform_era5_for_station(self):

        temp_path = os.path.join(self.target_dir.name, self.temp_dir.name, self.era5_file_name)

        ds = xr.open_dataset(temp_path)
        ds = Era5DataFromGribToNc._rename_variables(ds)

        cropper = Era5ForStationCropper(
            station=self.station,
            era5_path=temp_path,
            era5_target_path= self.era5_path
        )

        cropper.execute()
        cropper.cleanup()

    def get_era5_for_station(self):
        era5_hook = Era5DownloadHook(lat=self.station.metadata.get("latitude"),
                                     lon=self.station.metadata.get("longitude"))

        temp_grib_dir = tempfile.TemporaryDirectory()

        DownloadEra5ForStation(
            station=self.station,
            grib_dir_path=temp_grib_dir.name,
            hook=era5_hook,
            progress=self.progress
        )

        era5_temp_path = self.temp_dir.name + '/' + self.era5_file_name

        Era5DataFromGribToNc(
            temp_grib_dir.name,
            era5_target_file_path=era5_temp_path
        )

        temp_grib_dir.cleanup()

        cropper = Era5ForStationCropper(
            station=self.station,
            era5_path=era5_temp_path,
            era5_target_path=self.era5_path
        )

        cropper.execute()
        cropper.cleanup()


    def transform_station_to_expected_output(self):

        station_nc = xr.open_dataset(self.station_nc_file_path)
        era5_nc = xr.open_dataset(self.era5_path)

        # assert the time axis is the same
        try:
            assert all(station_nc.time.values == era5_nc.time.values)
        except Exception as e:
            print("Time axis is not the same")
            print("Station time axis:", station_nc.time.values)
            print("ERA5 time axis:", era5_nc.time.values)
            print("Difference:", set(station_nc.time.values) - set(era5_nc.time.values), "or",
                    set(era5_nc.time.values) - set(station_nc.time.values))
            # raise e

        FillAllTasWithValuesInNcFile(
            values=station_nc.tas.values.flatten(),
            original_path=self.era5_path,
            save_to_path=self.expected_output_path
        )

    def get_train_args(self):
        return f"""
            --data-root-dir {self.target_dir.name}
            --data-names {self.era5_file_name},{self.expected_output_file_name}
            --data-types tas,tas
            --n-target-data 1
            --encoding-layers 3
            --pooling-layers 0
            --device cpu
            --n-filters 18
            --out-channels 1
            --snapshot-dir {self.model_dir.name}
            --n-threads 0
            --max-iter {self.total_iterations}
            --log-interval {self.total_iterations // 100}
            --eval-timesteps 0,1
            --loss-criterion 3
            --log-dir {self.log_dir.name}
            --normalize-data
        """.strip()

    def get_train_args_txt(self):
        train_args_path = self.target_dir.name + '/train_args.txt'
        train_args = self.get_train_args()
        print("train args:", train_args)
        with open(self.train_args_path, 'w') as f:
            f.write(train_args)
        return self.train_args_path

    async def crai_train(self, train_args_path):
        print("Active conda environment:", os.environ['CONDA_DEFAULT_ENV'])
        self.progress.update_phase("Training")
        self.progress.folder_path = self.model_dir.name + "/images"
        

        try:
            train(train_args_path)

        except subprocess.CalledProcessError as e:
            raise Exception("Error during training")

        return self.model_dir.name
    

    def get_path_of_final_model(self):
        # assert final is there
        final_model_default_path = self.model_dir.name + '/' + self.model_dir_subfolder_name + '/final.pth'
        human_friendly_path = final_model_default_path.replace('final.pth', f'{self.station.name}-model-{self.total_iterations}.pth')
        try:
            assert os.path.exists(final_model_default_path)
            shutil.copy(final_model_default_path, human_friendly_path)
        except AssertionError:
            assert os.path.exist(human_friendly_path), "Final model not found" + str(os.listdir(self.model_dir.name + '/' + self.model_dir_subfolder_name))
        return human_friendly_path

    def make_zip_folder(self, folder_path):
        shutil.make_archive(folder_path, 'zip', folder_path)
        zip_file_name = self.station.name + '_model.zip'
        new_zip_file_path = self.target_dir.name + '/' + zip_file_name
        shutil.move(folder_path + '.zip', new_zip_file_path)
        return new_zip_file_path

    def cleanup(self):
        self.target_dir.cleanup()
        self.temp_dir.cleanup()
        self.log_dir.cleanup()

    def prepare_target_directory(self):
        os.makedirs(self.target_dir.name + '/' + self.subfolder_name)
        return self.target_dir.name + '/' + self.subfolder_name

    def copy_train_folder_as_val_folder(self):
        shutil.copytree(
            self.target_dir.name + '/' + self.subfolder_name,
            self.target_dir.name + '/val'
        )
        return self.target_dir.name + '/val'
