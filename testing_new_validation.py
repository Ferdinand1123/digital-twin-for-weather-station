from train_station_twin.validation_executor_era5 import EvaluationExecutor
from train_station_twin.training_executor_era5 import TrainingExecutor



evaluator = EvaluationExecutor(
    model_dir="testing_training/ViennaTraining_20241110-1620/model",        # Use model directory from training
    target_dir="testing_training/ViennaTraining_20241110-1620/target",      # Use target directory from training
    log_dir="testing_training/ViennaTraining_20241110-1620/log",            # Use log directory from training
    input_var_name="tas",
    target_var_name="tas",
    device='cpu',
    normalize_data=True,
    model_names=['final.pth', 'best.pth']
)

# Execute the evaluation
evaluator.execute()
print("Model evaluation completed.")