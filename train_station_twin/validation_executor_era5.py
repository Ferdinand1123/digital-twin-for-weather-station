import os
import logging
from crai.climatereconstructionai import evaluate

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

class EvaluationExecutor:
    def __init__(
        self,
        model_dir,
        target_dir,
        log_dir,
        input_var_name='tas',
        target_var_name='tas',
        device='cpu',
        normalize_data=True,
        model_names=None,
    ):
        """
        Initialize the EvaluationExecutor.

        Parameters:
        - model_dir: Path to the directory containing the model checkpoints (should include 'ckpt' subdirectory).
        - target_dir: Path to the target directory containing the data (should have 'val' subdirectory).
        - log_dir: Path to the directory where logs are stored.
        - input_var_name: Name of the input variable.
        - target_var_name: Name of the target variable.
        - device: Device to run the evaluation on ('cpu' or 'cuda').
        - normalize_data: Whether to normalize the data.
        - model_names: List of model checkpoint filenames to evaluate (e.g., ['final.pth', 'best.pth']).
        """
        self.model_dir = os.path.join(model_dir, 'ckpt')  # Use 'ckpt' subdirectory
        self.target_dir = target_dir
        self.log_dir = log_dir
        self.input_var_name = input_var_name
        self.target_var_name = target_var_name
        self.device = device
        self.normalize_data = normalize_data
        if model_names is None:
            self.model_names = ['final.pth', 'best.pth']
        else:
            self.model_names = model_names

    def execute(self):
        logging.info("Starting model evaluation.")

        data_root_dir = self.target_dir
        # Data names
        era5_file_name = "era5_input.nc"
        ground_truth_file_name = "ground_truth.nc"
        data_names = f"{era5_file_name},{ground_truth_file_name}"
        data_types = f"{self.input_var_name},{self.target_var_name}"

        normalize_flag = '--normalize-data' if self.normalize_data else ''

        model_names_str = ','.join(self.model_names)

        # Evaluation directory
        evaluation_dir = os.path.join(self.target_dir, 'evaluation')
        os.makedirs(evaluation_dir, exist_ok=True)

        eval_args = f"""
            --data-root-dir {data_root_dir}
            --data-names {data_names}
            --data-types {data_types}
            --n-target-data 1
            --device {self.device}
            --model-dir {self.model_dir}
            --model-names {model_names_str}
            --evaluation-dirs {evaluation_dir}
            --eval-names output
            --log-dir {self.log_dir}
            --pooling-layers 0
            --device cpu
            --n-filters 18
            --out-channels 1
            --loss-criterion 3
            --normalize-data
            --use-train-stats
            {normalize_flag}
        """.strip()

        eval_args_path = os.path.join(self.target_dir, 'eval_args.txt')
        with open(eval_args_path, 'w') as f:
            f.write(eval_args)
        logging.info(f"Evaluation arguments saved to {eval_args_path}.")

        try:
            evaluate(eval_args_path)
        except Exception as e:
            logging.error("Error during evaluation.")
            raise Exception("Error during evaluation") from e
        logging.info("Model evaluation completed.")


"""# Assuming you have an instance of TrainingExecutor named 'executor'
executor = TrainingExecutor(
    iterations=1000,
    base_dir='/path/to/base/dir',
    era5_data_path='/path/to/era5_data.nc',
    ground_truth_data_path='/path/to/ground_truth.nc',
    input_var_name='tas',
    target_var_name='tas',
    station_name='MyStation'
)

# Execute the training
executor.execute()

# Create an instance of EvaluationExecutor
evaluator = EvaluationExecutor(
    model_dir=executor.model_dir,        # Use model directory from training
    target_dir=executor.target_dir,      # Use target directory from training
    log_dir=executor.log_dir,            # Use log directory from training
    input_var_name=executor.input_var_name,
    target_var_name=executor.target_var_name,
    device='cpu',
    normalize_data=True,
    model_names=['final.pth', 'best.pth']
)

# Execute the evaluation
evaluator.execute()
print("Model evaluation completed.")
"""