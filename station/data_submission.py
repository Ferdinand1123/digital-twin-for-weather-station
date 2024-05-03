import tempfile
import uuid
import shutil
import os
import json
import time
from zipfile import ZipFile

from utils.utils import ProgressStatus
from station.station import StationData

import threading

class DataSubmission:
    def __init__(self, name="", cookie=False):
        self.data = None
        self.measurement_dir = tempfile.TemporaryDirectory()
        self.measurement_dir_path = self.measurement_dir.name # such that someone can create a DataSubmission without submit function and instead by adding the folder manually
        self.model_dir = tempfile.TemporaryDirectory()
        self.model_path = None
        self.pdf_path = None
        self.name = name
        self.cookie = cookie
        self.progress = ProgressStatus()
        self.station = None
        
    def initialize_station(self):
        self.progress.update_phase("Extracting Station")
        # Create StationData instance
        self.station = StationData(
            name=self.name,
            folder_path=self.measurement_dir_path,
            progress=self.progress
        )

        # Update progress phase
        self.progress.update_phase("")

    def submit(self, files, model):
        # Submit data to the server
        print("Number of uploaded files:", len(files))
        for file in files:
            if file.filename.endswith('.zip'):
                # Handle ZIP files
                 # Handle ZIP files
                zip_path = os.path.join(self.measurement_dir_path, file.filename)
                file.save(zip_path)  # Save the ZIP file

                # Extract contents of the ZIP file
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.measurement_dir_path)
                
                zip_folder = self.measurement_dir_path + "/" + file.filename.split(".zip")[0]

                move_files(zip_folder, self.measurement_dir_path)
                
                # Remove the ZIP file after extraction
                os.remove(zip_path)
                shutil.rmtree(zip_folder)
            else:
                # Handle other files
                file_path = os.path.join(self.measurement_dir_path, file.filename)
                file.save(file_path)
    
        if model:
            self.model_path = self.model_dir.name + "/" + model.filename
            model.save(self.model_path)
        if not self.name:
            self.generate_name()
        # Start a new thread to initialize station data
        threading.Thread(target=self.initialize_station, daemon=True).start()
        return
    
    def generate_name(self):
        filenames = os.listdir(self.measurement_dir_path)
        
        # use the name of the .rtf file
        rtf_file_name = None
        for filename in filenames:
            if filename.endswith(".rtf"):
                rtf_file_name = filename.split(".")[0]
                break
            
        rtf_file_name = rtf_file_name.replace(" ", "-")
        rtf_file_name = rtf_file_name.replace("_", "-")
        rtf_file_name = rtf_file_name.replace("metadata", "")
        rtf_file_name = rtf_file_name.strip("-")
        
        # sort the dat files by name
        filenames.sort()
        sorted_files = [filename for filename in filenames if filename.endswith(".dat")]
        first_file_name = sorted_files[0]
        last_file_name = sorted_files[-1]
        
        # reduce filenames to numerical part (to get the dates)
        # delete all non-numeric characters from the filenames
        first_file_name = "".join([c for c in first_file_name if c.isnumeric()])
        last_file_name = "".join([c for c in last_file_name if c.isnumeric()])
        
        first_last_name_str = first_file_name + "-" + last_file_name
        self.name = rtf_file_name + "_" + first_last_name_str
        if self.model_path:
            self.name += "_model-" + self.model_path.split("/")[-1].split(
                "model-")[-1].split(".")[0]
          
    def add_model(self, model_source_path):
        self.model_path = self.model_dir.name + "/" + model_source_path.split("/")[-1]
        shutil.copy(model_source_path, self.model_path)
        self.generate_name()
        return
    
    def add_pdf(self, pdf_source_path):
        self.pdf_path = self.model_dir.name + "/training.pdf"
        shutil.copy(pdf_source_path, self.pdf_path)
        return
    
        
    def cleanup(self):
        # Clean up the temporary directories
        if self.measurement_dir:
            self.measurement_dir.cleanup()
        if self.model_dir:
            self.model_dir.cleanup()


class DataStorage:
    def __init__(self):
        self._data_submissions = {}
        
    def add_data_submission(self, data_submission: DataSubmission) -> str:
        uid = str(uuid.uuid4())
        self._data_submissions[uid] = data_submission
        return uid
        
    def get_data_submission(self, uid) -> DataSubmission:
        return self._data_submissions.get(uid)
    
    def get_all_available_datasets(self, cookie):
        # return names, uids of all available datasets
        return_list = [{
            "name": data.name,
            "uid": uid,
            "has_model": data.model_path is not None,
            "has_pdf": data.pdf_path is not None,
            "status": str(data.progress)
        } for uid, data in self._data_submissions.items() if data.cookie == cookie]
        return return_list
    
    def delete_data_submission(self, uid):
        data_submission = self._data_submissions.get(uid)
        if data_submission:
            data_submission.cleanup()
            del self._data_submissions[uid]
        return
    

                
            
data_storage = DataStorage()


def move_files(source_dir, destination_dir):
    # Get list of files in the source directory
    files = os.listdir(source_dir)
    
    # Move each file to the destination directory
    for file in files:
        source_path = os.path.join(source_dir, file)
        destination_path = os.path.join(destination_dir, file)
        shutil.move(source_path, destination_path)