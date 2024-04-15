from station.station import StationData
from era5.era5_download_hook import Era5DownloadHook
from era5.era5_for_station import DownloadEra5ForStation, Era5ForStationCropper
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc

from infilling.evaluation_executer import EvaluatuionExecuter

from utils.utils import FillAllTasWithValuesInNcFile
from train_station_twin.training_analysis import era_vs_reconstructed_comparision_to_df, plot_n_steps_of_df

import subprocess
# from crai.climatereconstructionai import train

import tempfile
import os
import shutil

import xarray as xr


class TrainingExecuter():

    def __init__(self, station: StationData):
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

    def execute(self):
        self.get_era5_for_station()
        self.transform_station_to_expected_output()
        self.copy_train_folder_as_val_folder()
        path = self.get_train_args_txt()
        model_dir_path = self.crai_train(path)
        return self.make_zip_folder(model_dir_path)
    
    def visualize(self):
        # to be used after execute
        assert os.path.exists(self.get_path_of_final_model())
        assert os.path.exists(self.era5_path)
        
        evaluation = EvaluatuionExecuter(
            station=self.station,
            model_path=self.get_path_of_final_model()
        )
        # don't run evaluation.execute() because it will optain ERA5 to infill gaps
        
        # copy the era5 training data to the evaluation directory
        shutil.copy(self.era5_path, evaluation.era5_path)
        path = evaluation.get_eval_args_txt()
        reconstructed_path = evaluation.crai_evaluate(path)
        
        df = era_vs_reconstructed_comparision_to_df(
            era5_data = xr.open_dataset(self.era5_path),
            reconstructed_data = xr.open_dataset(reconstructed_path),
            measurements_data=xr.open_dataset(self.station_nc_file_path)
        )
        
        plot_n_steps_of_df(df)   


    def get_era5_for_station(self):
        era5_hook = Era5DownloadHook(lat=self.station.metadata.get("latitude"),
                                     lon=self.station.metadata.get("longitude"))

        temp_grib_dir = tempfile.TemporaryDirectory()

        DownloadEra5ForStation(
            station=self.station,
            grib_dir_path=temp_grib_dir.name,
            hook=era5_hook
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
        assert all(station_nc.time.values == era5_nc.time.values)

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
            --max-iter 1000
            --log-interval 5000
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

    def crai_train(self, train_args_path):
        print("Active conda environment:", os.environ['CONDA_DEFAULT_ENV'])
        # give the crai worker pid full access to all passed directories
        for dir in [self.target_dir, self.model_dir, self.log_dir]:
            print(f"chmod -R 777 {dir.name}")
            subprocess.run(f"chmod -R 777 {dir.name}", shell=True)
        command = [
            "python", "-m", "crai.climatereconstructionai.train",
            "--load-from-file", train_args_path
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)                                    
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print("Error during training:", e)
            print("Check the log files in", self.log_dir.name)
            print(e.stderr)
            raise e
        return self.model_dir.name

    def get_path_of_final_model(self):
        return self.model_dir.name + '/' + self.model_dir_subfolder_name + '/final.pth'

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
