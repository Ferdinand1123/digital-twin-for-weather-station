# run_training.py
from train_station_twin.training_executor_copy import SimplifiedTrainingExecutor


data_root_dir = 'simplified_training_copy/Data'  # Ensure this path is correct
model_output_dir = 'simplified_training_copy/'

executor = SimplifiedTrainingExecutor(data_root_dir, model_output_dir, max_iter=1000, device='cpu')
executor.execute_training()
executor.save_model()
