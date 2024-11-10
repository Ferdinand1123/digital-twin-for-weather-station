from train_station_twin.training_executor_era5 import TrainingExecutor
from utils.utils import ProgressStatus



# Initialize progress status handler
progress = ProgressStatus()

# Number of training iterations
iterations = 1000

# Base directory where all files will be stored
base_dir = "testing_training/"

# Path to your ERA5 data file (optional)
era5_data_path = 'testing_training/Data/vienna_station_input.nc'  # Set to None if you want to download

# Set prepare_data to False if your data is already prepared
ground_truth_data_path = "testing_training/Data/vienna_station_filltas.nc"


# Optional station name for naming purposes
station_name = "ViennaTraining"

# Initialize the TrainingExecutor
executor = TrainingExecutor(
    iterations=iterations,
    base_dir=base_dir,
    era5_data_path=era5_data_path,
    ground_truth_data_path=ground_truth_data_path,
    station_name=station_name,
)

# Execute the training
executor.execute()


