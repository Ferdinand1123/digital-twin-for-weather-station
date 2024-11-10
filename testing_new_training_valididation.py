from train_station_twin.validation_executor_era5 import EvaluationExecutor
from train_station_twin.training_executor_era5 import TrainingExecutor


# Number of training iterations
iterations = 10000

# Base directory where all files will be stored
base_dir = "testing_training/"

# Path to your ERA5 data file (optional)
era5_data_path = 'testing_training/Data/vienna_station_input.nc'  # Set to None if you want to download

# Set prepare_data to False if your data is already prepared
ground_truth_data_path = "testing_training/Data/vienna_station_filltas.nc"


# Optional station name for naming purposes
station_name = "ViennaTraining"

# Assuming you have an instance of TrainingExecutor named 'executor'
executor = TrainingExecutor(
    iterations=iterations,
    base_dir=base_dir,
    era5_data_path=era5_data_path,
    ground_truth_data_path=ground_truth_data_path,
    input_var_name='tas',
    target_var_name='tas',
    station_name=station_name
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
