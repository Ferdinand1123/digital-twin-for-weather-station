import os
import shutil
import time
import xarray as xr
import logging
from crai.climatereconstructionai import train
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

class TrainingExecutor:
    def __init__(
        self,
        iterations,
        base_dir,
        era5_data_path,
        ground_truth_data_path,
        input_var_name='tas',
        target_var_name='tas',
        station_name="DefaultStation",
    ):
        self.station_name = station_name
        self.input_var_name = input_var_name
        self.target_var_name = target_var_name

        timestamp = time.strftime("%Y%m%d-%H%M")
        self.base_dir = os.path.join(base_dir, f"{self.station_name}_{timestamp}")
        os.makedirs(self.base_dir, exist_ok=True)

        self.target_dir = os.path.join(self.base_dir, 'target')
        self.model_dir = os.path.join(self.base_dir, 'model')
        self.log_dir = os.path.join(self.base_dir, 'log')

        for directory in [self.target_dir, self.model_dir, self.log_dir]:
            os.makedirs(directory, exist_ok=True)

        self.era5_file_name = "era5_input.nc"
        self.expected_output_file_name = "ground_truth.nc"
        self.subfolder_name = "train"
        self.model_dir_subfolder_name = "ckpt"

        self.era5_data_path = era5_data_path
        self.ground_truth_data_path = ground_truth_data_path

        self.prepare_target_directory()

        self.era5_path = os.path.join(self.target_dir, self.subfolder_name, self.era5_file_name)
        self.expected_output_path = os.path.join(self.target_dir, self.subfolder_name, self.expected_output_file_name)
        self.train_args_path = os.path.join(self.target_dir, 'train_args.txt')

        self.total_iterations = iterations

    def execute(self):
        logging.info("Starting training execution.")
        self.prepare_training_data()
        self.copy_train_folder_as_val_folder()
        path = self.get_train_args_txt()
        self.crai_train(path)
        logging.info("Training completed. Creating zip archive.")
        return self.make_zip_folder(self.model_dir)

    def prepare_training_data(self):
        logging.info("Preparing training data.")

        # Copy ERA5 data to the training directory
        shutil.copy(self.era5_data_path, self.era5_path)
        # Copy ground truth data to the training directory
        shutil.copy(self.ground_truth_data_path, self.expected_output_path) 

        # Convert data to float32
        logging.info("Converting data to float32.")
        self.convert_to_float32(self.era5_path)
        self.convert_to_float32(self.expected_output_path)

        # Verify that the time axes match
        logging.info("Verifying time axes alignment.")
        era5_nc = xr.open_dataset(self.era5_path)
        ground_truth_nc = xr.open_dataset(self.expected_output_path)

        if not all(era5_nc.time.values == ground_truth_nc.time.values):
            raise ValueError("Time axes of ERA5 data and ground truth data do not match.")
    
    def convert_to_float32(self, file_path):
        ds = xr.open_dataset(file_path)
        ds = ds.astype('float32')
        ds.to_netcdf(file_path) 

    def get_train_args(self):
        logging.info("Generating training arguments.")
        return f"""
            --data-root-dir {self.target_dir}
            --data-names {self.era5_file_name},{self.expected_output_file_name}
            --data-types {self.input_var_name},{self.target_var_name}
            --n-target-data 1
            --encoding-layers 3
            --pooling-layers 0
            --device cpu
            --n-filters 18
            --out-channels 1
            --snapshot-dir {self.model_dir}
            --n-threads 0
            --max-iter {self.total_iterations}
            --log-interval {max(1, self.total_iterations // 1000)}
            --eval-timesteps 0,1
            --loss-criterion 3
            --log-dir {self.log_dir}
            --normalize-data
        """.strip()

    def get_train_args_txt(self):
        train_args = self.get_train_args()
        with open(self.train_args_path, 'w') as f:
            f.write(train_args)
        logging.info(f"Training arguments saved to {self.train_args_path}.")
        return self.train_args_path

    def crai_train(self, train_args_path):
        logging.info("Starting model training.")
        try:
            train(train_args_path)
        except subprocess.CalledProcessError as e:
            logging.error("Error during training.")
            raise Exception("Error during training") from e
        logging.info("Model training completed.")

    def make_zip_folder(self, folder_path):
        logging.info("Creating zip archive of the model directory.")
        shutil.make_archive(folder_path, 'zip', folder_path)
        zip_file_name = f"{self.station_name}_model.zip"
        new_zip_file_path = os.path.join(self.base_dir, zip_file_name)
        shutil.move(f"{folder_path}.zip", new_zip_file_path)
        logging.info(f"Zip archive created at {new_zip_file_path}.")
        return new_zip_file_path

    def prepare_target_directory(self):
        os.makedirs(os.path.join(self.target_dir, self.subfolder_name), exist_ok=True)
        logging.info(f"Training data directory prepared at {self.target_dir}.")
        return os.path.join(self.target_dir, self.subfolder_name)

    def copy_train_folder_as_val_folder(self):
        logging.info("Copying training folder to validation folder.")
        src = os.path.join(self.target_dir, self.subfolder_name)
        dst = os.path.join(self.target_dir, 'val')
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logging.info(f"Validation data directory prepared at {dst}.")
        return dst
