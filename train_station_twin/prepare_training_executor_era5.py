import os
import shutil
import time
import xarray as xr
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


class TrainingPreparation:
    def __init__(self, base_dir, station_name="DefaultStation"):
        """
        Initializes the TrainingPreparation class by creating the necessary directory structure.

        Args:
            base_dir (str): The base directory where the station directory will be created.
            station_name (str, optional): Name of the station. Defaults to "DefaultStation".
        """
        self.station_name = station_name
        timestamp = time.strftime("%Y%m%d-%H")
        self.station_dir = os.path.join(base_dir, f"{self.station_name}_{timestamp}")
        os.makedirs(self.station_dir, exist_ok=True)
        logging.info(f"Created station directory at {self.station_dir}.")

        # Create data, model, and log directories
        self.data_dir = os.path.join(self.station_dir, 'data')
        self.model_dir = os.path.join(self.station_dir, 'model')
        self.log_dir = os.path.join(self.station_dir, 'log')

        for directory in [self.data_dir, self.model_dir, self.log_dir]:
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Created directory: {directory}")

        # Create train, val, test directories inside data
        self.train_dir = os.path.join(self.data_dir, 'train')
        self.val_dir = os.path.join(self.data_dir, 'val')
        self.test_dir = os.path.join(self.data_dir, 'test')

        for directory in [self.train_dir, self.val_dir, self.test_dir]:
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Created directory: {directory}")

    def copy_and_prepare_data(self, dataset_type, input_src, output_src):
        """
        Copies the input and output datasets into the specified dataset_type directory.
        Converts data from float64 to float32, checks alignment, and variable names.

        Args:
            dataset_type (str): One of 'train', 'val', or 'test'.
            input_src (str): Path to the input NetCDF file.
            output_src (str): Path to the output NetCDF file.
        """
        logging.info(f"Starting to copy and prepare data for {dataset_type} dataset.")

        if dataset_type not in ['train', 'val', 'test']:
            logging.error(f"Invalid dataset_type: {dataset_type}. Must be 'train', 'val', or 'test'.")
            raise ValueError(f"Invalid dataset_type: {dataset_type}. Must be 'train', 'val', or 'test'.")

        # Get the destination directory
        dest_dir = getattr(self, f"{dataset_type}_dir")

        # Define destination paths
        input_dest = os.path.join(dest_dir, 'input.nc')
        output_dest = os.path.join(dest_dir, 'output.nc')

        # Copy input file
        if os.path.isfile(input_src):
            shutil.copy(input_src, input_dest)
            logging.info(f"Copied input file from {input_src} to {input_dest}.")
            self._convert_to_float32(input_dest)
        else:
            logging.error(f"Input file {input_src} does not exist.")
            raise FileNotFoundError(f"Input file {input_src} does not exist.")

        # Copy output file
        if os.path.isfile(output_src):
            shutil.copy(output_src, output_dest)
            logging.info(f"Copied output file from {output_src} to {output_dest}.")
            self._convert_to_float32(output_dest)
        else:
            logging.error(f"Output file {output_src} does not exist.")
            raise FileNotFoundError(f"Output file {output_src} does not exist.")

        # Check alignment
        if not self._check_alignment(input_dest, output_dest):
            logging.error(f"Alignment check failed for {dataset_type} dataset.")
            raise ValueError(f"Alignment check failed for {dataset_type} dataset.")
        else:
            logging.info(f"Alignment check passed for {dataset_type} dataset.")

        # Check variable names
        if not self._check_variable_names(input_dest, output_dest):
            logging.error(f"Variable names check failed for {dataset_type} dataset.")
            raise ValueError(f"Variable names check failed for {dataset_type} dataset.")
        else:
            logging.info(f"Variable names check passed for {dataset_type} dataset.")

        logging.info(f"Completed copying and processing data for {dataset_type} dataset.")

    def _convert_to_float32(self, file_path):
        """
        Converts the data in a NetCDF file to float32.

        Args:
            file_path (str): Path to the NetCDF file to be converted.
        """
        try:
            ds = xr.open_dataset(file_path)
            ds = ds.astype('float32')
            ds.to_netcdf(file_path)
            ds.close()
            logging.info(f"Converted {file_path} to float32.")
        except Exception as e:
            logging.error(f"Error converting {file_path} to float32: {e}")
            raise

    def _check_alignment(self, input_file, output_file):
        """
        Checks if the input and output NetCDF files have aligned 'time' coordinates.

        Args:
            input_file (str): Path to the input NetCDF file.
            output_file (str): Path to the output NetCDF file.

        Returns:
            bool: True if aligned, False otherwise.
        """
        try:
            ds_input = xr.open_dataset(input_file)
            ds_output = xr.open_dataset(output_file)

            input_time = ds_input['time']
            output_time = ds_output['time']

            if not input_time.equals(output_time):
                logging.error(f"Time axes do not match between {input_file} and {output_file}.")
                ds_input.close()
                ds_output.close()
                return False

            ds_input.close()
            ds_output.close()
            return True
        except Exception as e:
            logging.error(f"Error checking alignment between {input_file} and {output_file}: {e}")
            return False

    def _check_variable_names(self, input_file, output_file):
        """
        Checks if the input and output NetCDF files have the expected variable names.

        Args:
            input_file (str): Path to the input NetCDF file.
            output_file (str): Path to the output NetCDF file.

        Returns:
            bool: True if variable names are acceptable, False otherwise.
        """
        try:
            ds_input = xr.open_dataset(input_file)
            ds_output = xr.open_dataset(output_file)

            input_vars = set(ds_input.data_vars)
            output_vars = set(ds_output.data_vars)

            # Implement the logic to check variable names
            # For now, we'll check that both have at least one variable
            if not input_vars:
                logging.error(f"No data variables found in input file {input_file}.")
                ds_input.close()
                ds_output.close()
                return False

            if not output_vars:
                logging.error(f"No data variables found in output file {output_file}.")
                ds_input.close()
                ds_output.close()
                return False

            ds_input.close()
            ds_output.close()
            return True
        except Exception as e:
            logging.error(f"Error checking variable names between {input_file} and {output_file}: {e}")
            return False

    def _write_common_args(self, common_args_path, input_filename='input.nc', output_filename='output.nc', data_types_in="tas", data_types_out="tas",
                        n_target_data=1, encoding_layers=3, pooling_layers=0,
                        device='cpu', n_filters=18, out_channels=1,
                        loss_criterion=3):
        """
        Retrieves the common arguments for both training and evaluation.

        Args:
            input_filename (str): Name of the input data file.
            output_filename (str): Name of the output data file.
            data_types_in (str): Data type(s) for the input data.
            data_types_out (str): Data type(s) for the output data.
            n_target_data (int, optional): Number of target data. Defaults to 1.
            encoding_layers (int, optional): Number of encoding layers. Defaults to 3.
            pooling_layers (int, optional): Number of pooling layers. Defaults to 0.
            device (str, optional): Device used by PyTorch ('cuda' or 'cpu'). Defaults to 'cpu'.
            n_filters (int, optional): Number of filters. Defaults to 18.
            out_channels (int, optional): Number of output channels. Defaults to 1.
            loss_criterion (int, optional): Index defining the loss function. Defaults to 3.
            normalize_data (bool, optional): Whether to normalize data. Defaults to True.

        Returns:
            list: A list of common argument strings.
        """

        if common_args_path is None:
            common_args_path = os.path.join(self.station_dir, 'common_args.txt')
        
        common_args = f"""
--data-root-dir {self.data_dir}
--data-names {input_filename},{output_filename}
--data-types {data_types_in},{data_types_out}
--n-target-data {n_target_data}
--encoding-layers {encoding_layers}
--pooling-layers {pooling_layers}
--device {device}
--n-filters {n_filters}
--out-channels {out_channels}
--loss-criterion {loss_criterion}
--normalize-data
        """.strip()
        try:
            with open(common_args_path, 'w') as f:
                f.write(common_args)  # Ensure the file ends with a newline
            logging.info(f"Common arguments written to {common_args_path}.")
            return common_args_path
        except Exception as e:
            logging.error(f"Failed to write common arguments to {common_args_path}: {e}")
            raise


    def prepare_training_args(self, total_iterations=10000, output_path=None,
                              common_args_path=None,
                              input_filename='input.nc', output_filename='output.nc',
                              data_types_in="tas", data_types_out="tas",
                              n_target_data=1, encoding_layers=3, pooling_layers=0,
                              device='cpu', n_filters=18, out_channels=1,
                              loss_criterion=3):
        """
        Prepares the training arguments by writing common args and training-specific args,
        and saves them to a training arguments text file.

        Args:
            total_iterations (int, optional): Number of training iterations. Defaults to 10000.
            output_path (str, optional): Path to save the training arguments file.
                                         Defaults to 'train_args.txt' in the station directory.
            input_filename (str, optional): Name of the input data file. Defaults to 'input.nc'.
            output_filename (str, optional): Name of the output data file. Defaults to 'output.nc'.
            data_types_in (str, optional): Data type(s) for the input data. Defaults to "tas".
            data_types_out (str, optional): Data type(s) for the output data. Defaults to "tas".
            n_target_data (int, optional): Number of target data. Defaults to 1.
            encoding_layers (int, optional): Number of encoding layers. Defaults to 3.
            pooling_layers (int, optional): Number of pooling layers. Defaults to 0.
            device (str, optional): Device used by PyTorch ('cuda' or 'cpu'). Defaults to 'cpu'.
            n_filters (int, optional): Number of filters. Defaults to 18.
            out_channels (int, optional): Number of output channels. Defaults to 1.
            loss_criterion (int, optional): Index defining the loss function. Defaults to 3.
            normalize_data (bool, optional): Whether to normalize data. Defaults to True.

        Returns:
            str: Path to the training arguments file.
        """
        if output_path is None:
            output_path = os.path.join(self.station_dir, 'train_args.txt')

        # Get common arguments
        common_args_path = self._write_common_args(
            common_args_path=common_args_path,
            input_filename=input_filename,
            output_filename=output_filename,
            data_types_in=data_types_in,
            data_types_out=data_types_out,
            n_target_data=n_target_data,
            encoding_layers=encoding_layers,
            pooling_layers=pooling_layers,
            device=device,
            n_filters=n_filters,
            out_channels=out_channels,
            loss_criterion=loss_criterion
            )
        

        # Define training-specific arguments
        train_specific_args = f"""
--snapshot-dir {self.model_dir}
--n-threads 0
--max-iter {total_iterations}
--log-interval 500
--eval-timesteps 0,1
--log-dir {self.log_dir}
        """.strip()


        # Write training arguments to train_args.txt by reading common_args.txt and appending training-specific args
        try:
            with open(common_args_path, 'r') as f:
                common_content = f.read() 
            with open(output_path, 'w') as f:
                f.write(common_content + '\n' + train_specific_args)
            logging.info(f"Training arguments saved to {output_path}.")
            return output_path
        except Exception as e:
            logging.error(f"Failed to write training arguments to {output_path}: {e}")
            raise

    def prepare_eval_args(self, model_path, output_dir, model_name="best.pth", output_path=None):
        """
        Prepares the evaluation arguments by appending evaluation-specific args to common args,
        and saves them to an evaluation arguments text file.

        Args:
            model_path (str): Full path to the folder of trained model file (e.g., 'model/ckpt').
            output_dir (str): Directory where the evaluation outputs will be stored.
            output_path (str, optional): Path to save the evaluation arguments file.
                                         Defaults to 'eval_args.txt' in the station directory.

        Returns:
            str: Path to the evaluation arguments file.
        """
        if output_path is None:
            output_path = os.path.join(self.station_dir, 'eval_args.txt')

        if output_dir is None:
            output_dir = os.path.join(self.station_dir, 'evaluation_outputs')  

        # Define common_args.txt path
        common_args_path = os.path.join(self.station_dir, 'common_args.txt')


        # Define evaluation-specific arguments
        model_dir = model_path
        model_name = model_name

        eval_specific_args = f"""
--model-dir {model_dir}
--model-names {model_name}
--evaluation-dirs {output_dir}
--log-dir {self.log_dir}
--use-train-stats
        """.strip()


        # Write to eval_args.txt
        try:
            with open(common_args_path, 'r') as f:
                common_content = f.read() 
            with open(output_path, 'w') as f:
                f.write(common_content + '\n' + eval_specific_args)
            logging.info(f"Training arguments saved to {output_path}.")
            return output_path
        except Exception as e:
            logging.error(f"Failed to write training arguments to {output_path}: {e}")
            raise

