from station.station import StationData
from era5.era5_download_hook import Era5DownloadHook
from era5.era5_for_station import DownloadEra5ForStation, Era5ForStationCropper
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc

from infilling.evaluation_executer import EvaluatuionExecuter

from utils.utils import FillAllTasWithValuesInNcFile, ProgressStatus


from fpdf import FPDF

from train_station_twin.training_analysis import era5_vs_reconstructed_comparision_to_df, plot_n_steps_of_df
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


class TrainingExecuter():

    def __init__(self, station: StationData, progress: ProgressStatus, iterations):
        self.station = station
        assert station.name is not None
        assert station.metadata is not None
        assert station.metadata.get("latitude") is not None
        assert station.metadata.get("longitude") is not None
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

        self.era5_path = self.target_dir.name + '/' + \
            self.subfolder_name + '/' + self.era5_file_name
        self.expected_output_path = self.target_dir.name + '/' + \
            self.subfolder_name + '/' + self.expected_output_file_name
        self.train_args_path = self.target_dir.name + '/train_args.txt'

        self.progress = progress
        self.total_iterations = iterations

    async def execute(self):
        self.get_era5_for_station()
        self.progress.update_phase("Preparing Training Set")
        self.transform_station_to_expected_output()
        self.copy_train_folder_as_val_folder()
        path = self.get_train_args_txt()
        model_dir_path = await self.crai_train(path)
        self.validate()
        self.progress.update_phase("")
        return self.make_zip_folder(model_dir_path)

    def validate(self):
        # to be used after execute
        assert os.path.exists(self.get_path_of_final_model()
                              ), "Model not found after training"
        assert os.path.exists(self.era5_path)

        evaluation = EvaluatuionExecuter(
            station=self.station,
            model_path=self.get_path_of_final_model()
        )
        # don't run evaluation.execute() because it will optain ERA5 to infill gaps

        # copy the era5 training data to the evaluation directory
        shutil.copy(self.era5_path, evaluation.era5_path)

        # prepare expected output cleaned
        reconstructed_path = evaluation.execute()

        df = era5_vs_reconstructed_comparision_to_df(
            era5_path=self.era5_path,
            reconstructed_path=reconstructed_path,
            measurements_path=self.station_nc_file_path
        )

        coords = {
            "station_lon": self.station.metadata.get("longitude"),
            "station_lat": self.station.metadata.get("latitude"),
            "era5_lons": xr.open_dataset(self.era5_path).lon.values,
            "era5_lats": xr.open_dataset(self.era5_path).lat.values
        }

        pdf = FPDF(format='A3')
        pdf.add_page(orientation='L')

        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=True,
            title=f"{self.station.name}, Reconstructed vs Measurements",
            save_to=self.model_dir.name
        )

        pdf.image(saved_to_path, h=260)

        saved_to_path_2 = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=False,
            title=f"{self.station.name}, Reconstructed",
            save_to=self.model_dir.name
        )
        pdf.image(saved_to_path_2, h=260)

        pdf.output(self.get_pdf_path())

    def get_pdf_path(self):
        return self.model_dir.name + '/validation.pdf'

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
            raise e

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
