import tempfile

class DataSubmission:
    def __init__(self):
        self.data = None
        self.measurement_dir = tempfile.TemporaryDirectory()
        self.model_dir = tempfile.TemporaryDirectory()
        self.model_path = None
        self.name = None

    def submit(self, files, model):
        # Submit data to the server
        self.set_dataset_name_from_files(files, model)
        print(f"Data Submission {self.name} in progress")
        print("Number of uploaded files:", len(files))
        for file in files:
            file.save(self.measurement_dir.name + "/" + file.filename)
        self.model_path = self.model_dir.name + "/" + model.filename
        model.save(self.model_path)
        return
    
    def set_dataset_name_from_files(self, files, model):
        print("Getting dataset name from files", files)
        # use the name of the .rtf file
        rtf_file_name = None
        for file in files:
            if file.filename.endswith(".rtf"):
                rtf_file_name = file.filename.split(".")[0]
                break
            
        rtf_file_name = rtf_file_name.replace(" ", "-")
        rtf_file_name = rtf_file_name.replace("_", "-")
        rtf_file_name = rtf_file_name.replace("metadata", "")
        rtf_file_name = rtf_file_name.strip("-")
        
        # sort the dat files by name
        files.sort(key=lambda x: x.filename)
        sorted_files = [file for file in files if file.filename.endswith(".dat")]
        first_file_name = sorted_files[0].filename
        last_file_name = sorted_files[-1].filename
        
        # reduce filenames to numerical part (to get the dates)
        # delete all non-numeric characters from the filenames
        first_file_name = "".join([c for c in first_file_name if c.isnumeric()])
        last_file_name = "".join([c for c in last_file_name if c.isnumeric()])
        
        first_last_name_str = first_file_name + "-" + last_file_name
        self.name = rtf_file_name + "_" + first_last_name_str + \
            "_model-" + model.filename.split(".")[0]
        
    
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
        uid = str(hash(data_submission))
        self._data_submissions[uid] = data_submission
        return uid
        
    def get_data_submission(self, uid) -> DataSubmission:
        return self._data_submissions.get(uid)
    
    def get_all_available_datasets(self):
        # return names, uids of all available datasets
        return_list = [{
            "name": data.name,
            "uid": uid
        } for uid, data in self._data_submissions.items()]
        print("Available datasets:", return_list)
        return return_list
