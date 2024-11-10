# Import necessary modules
import os
import shutil
import torch
import numpy as np
import matplotlib.pyplot as plt
import shlex

# Import the train function and other necessary components
from crai.climatereconstructionai import train
from crai.climatereconstructionai.utils.io import load_ckpt, load_model
from crai.climatereconstructionai.model.net import CRAINet
from crai.climatereconstructionai.utils.netcdfloader import NetCDFLoader

# Define the training executor class
class SimplifiedTrainingExecutor:
    def __init__(self, data_root_dir, model_output_dir, max_iter=1000, device='cpu'):
        """
        Initializes the training executor.

        Parameters:
        - data_root_dir: The root directory where the 'train', 'val', and 'test' folders are located.
        - model_output_dir: The directory where the model and logs will be saved.
        - max_iter: The maximum number of training iterations.
        - device: 'cpu' or 'cuda' for GPU acceleration.
        """
        self.data_root_dir = data_root_dir
        self.model_output_dir = model_output_dir
        self.max_iter = max_iter
        self.device = device

        # Create necessary directories if they don't exist
        os.makedirs(self.model_output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.model_output_dir, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.model_output_dir, 'ckpt'), exist_ok=True)

        # Define data and model parameters
        self.train_dir = os.path.join(self.data_root_dir, 'train')
        self.val_dir = os.path.join(self.data_root_dir, 'val')
        self.test_dir = os.path.join(self.data_root_dir, 'test')  # Optional

        # Check that the data directories exist
        assert os.path.exists(self.train_dir), "Train directory does not exist."
        assert os.path.exists(self.val_dir), "Validation directory does not exist."

        # Define the names of the data files (assuming consistent naming)
        self.data_names = ['input_data.nc', 'ground_truth.nc']  # Modify these names as per your files
        self.val_names = ['input_data.nc', 'ground_truth.nc']  # Modify as needed
        self.data_types = ['tas', 'tas']  # Assuming 'tas' variable in both files

    def prepare_arguments(self):
        """
        Prepares the arguments for the train function.
        """
        # Create a dictionary of arguments
        self.train_args = {
            '--data-root-dir': self.data_root_dir,
            '--data-names': ','.join(self.data_names),
            #'--val-names': ','.join(self.val_names),
            '--data-types': ','.join(self.data_types),
            '--n-target-data': '1',
            '--encoding-layers': '3',
            '--pooling-layers': '0',
            '--device': self.device,
            '--n-filters': '18',
            '--out-channels': '1',
            '--snapshot-dir': self.model_output_dir,
            '--n-threads': '0',
            '--max-iter': str(self.max_iter),
            '--log-interval': str(max(1, self.max_iter // 100)),
            '--eval-timesteps': '0,1',
            '--loss-criterion': '3',
            '--log-dir': os.path.join(self.model_output_dir, 'logs'),
            '--normalize-data': 'True',    # Flags without values
            '--early-stopping-patience': '10',    # Flags without values
        }

        # Build the arguments string
        args_list = []
        for k, v in self.train_args.items():
            if v == '':
                args_list.append(f"{k}")
            else:
                args_list.append(f"{k} {v}")

        # Join the arguments into a single string
        self.args_string = '\n'.join(args_list)

        # Write arguments to a text file stored in the model output directory
        self.train_args_file = os.path.join(self.model_output_dir, 'train_args.txt')
        with open(self.train_args_file, 'w') as f:
            f.write(self.args_string)

        print(f"Training arguments written to {self.train_args_file}")



    def execute_training(self):
        """
        Executes the training process.
        """
        # Prepare the arguments
        self.prepare_arguments()

        # Call the train function with the path to the arguments file
        train(self.train_args_file)

    def save_model(self):
        """
        Saves the trained model in a meaningful way.
        """
        # Assuming that the model is saved in self.model_output_dir + '/ckpt/final.pth'
        final_model_path = os.path.join(self.model_output_dir, 'ckpt', 'final.pth')
        assert os.path.exists(final_model_path), "Final model not found."

        # Rename or move the final model to a desired location
        meaningful_model_path = os.path.join(self.model_output_dir, 'trained_model.pth')
        shutil.copy(final_model_path, meaningful_model_path)
        print(f"Model saved to {meaningful_model_path}")

    def load_model(self):
        """
        Loads the trained model for evaluation.
        """
        # Load model checkpoint
        final_model_path = os.path.join(self.model_output_dir, 'ckpt', 'final.pth')
        assert os.path.exists(final_model_path), "Final model not found."

        # Load the checkpoint dictionary
        ckpt_dict = load_ckpt(final_model_path, self.device)

        # Initialize the model
        # Adjust parameters as needed to match your model
        img_size = (16, 16)  # Replace with your actual image size
        model = CRAINet(img_size=img_size,
                        enc_dec_layers=3,
                        pool_layers=0,
                        in_channels=1,  # Adjust based on your data
                        out_channels=1).to(self.device)

        # Load the model weights
        load_model(ckpt_dict, model, optimizer=None)

        self.model = model
        print("Model loaded for evaluation.")

    def evaluate_model(self):
        """
        Evaluates the trained model on test data.
        """
        # Ensure the model is loaded
        if not hasattr(self, 'model'):
            self.load_model()

        # Load test data
        test_dir = self.test_dir
        if not os.path.exists(test_dir):
            print("Test directory does not exist. Skipping evaluation.")
            return

        test_dataset = NetCDFLoader(self.data_root_dir, self.data_names, mask_dir=None, mask_names=None,
                                    data_split='test', data_types=self.data_types, time_steps=[0])

        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=1, shuffle=False)

        # Set model to evaluation mode
        self.model.eval()

        # Initialize lists to store results
        losses = []
        criterion = torch.nn.MSELoss()

        # Iterate over test data
        with torch.no_grad():
            for data in test_loader:
                inputs, masks, targets = data
                inputs = inputs.to(self.device)
                masks = masks.to(self.device)
                targets = targets.to(self.device)

                # Forward pass
                outputs = self.model(inputs, masks)

                # Compute loss
                loss = criterion(outputs, targets)
                losses.append(loss.item())

                # (Optional) Visualize or save outputs here

        # Compute average loss
        avg_loss = np.mean(losses)
        print(f"Average test loss: {avg_loss}")

        # Plot loss if desired
        plt.figure()
        plt.plot(losses)
        plt.title('Test Loss per Sample')
        plt.xlabel('Sample')
        plt.ylabel('Loss')
        plt.show()

    def plot_training_loss(self):
        """
        Plots the training and validation loss over iterations.
        """
        # Assuming that training logs are saved in a format that can be read
        # You may need to adjust this based on how the train function logs data
        log_dir = os.path.join(self.model_output_dir, 'logs')
        # Check if logs exist
        if not os.path.exists(log_dir):
            print("Log directory does not exist. Cannot plot training loss.")
            return

        # Assuming logs are saved as text files or can be read
        # For this example, we'll assume the losses are stored in a file called 'loss_log.txt'
        loss_log_path = os.path.join(log_dir, 'loss_log.txt')
        if not os.path.exists(loss_log_path):
            print("Loss log file does not exist. Cannot plot training loss.")
            return

        # Read the loss values
        iterations = []
        train_losses = []
        val_losses = []

        with open(loss_log_path, 'r') as f:
            for line in f:
                # Assuming each line is formatted as: iteration, train_loss, val_loss
                parts = line.strip().split(',')
                iteration = int(parts[0])
                train_loss = float(parts[1])
                val_loss = float(parts[2])

                iterations.append(iteration)
                train_losses.append(train_loss)
                val_losses.append(val_loss)

        # Plot the losses
        plt.figure()
        plt.plot(iterations, train_losses, label='Train Loss')
        plt.plot(iterations, val_losses, label='Validation Loss')
        plt.xlabel('Iteration')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()
        plt.show()


# Example usage:

# Set the data root directory and model output directory
#data_root_dir = 'simplified_training/Data'  # Replace with your data directory
#model_output_dir = 'simplified_training/'   # Replace with your desired output directory

# Create an instance of the training executor
#executor = SimplifiedTrainingExecutor(data_root_dir, model_output_dir, max_iter=1000, device='cpu')

# Execute the training
#executor.execute_training()

# Save the model
#executor.save_model()

# Load and evaluate the model
#executor.load_model()
#executor.evaluate_model()

# Plot training and validation loss
#executor.plot_training_loss()
