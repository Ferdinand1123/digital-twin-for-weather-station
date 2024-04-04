import tempfile

class DataSubmission:
    def __init__(self):
        self.data = None
        self.temp_submitted_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir.name
        self.nc_dir_path = "data/nc_files"

    def submit(self, files, metadata):
        # Submit data to the server
        print("Data Submission in progress")
        print("Number of uploaded files:", len(files))
        print("Metadata:", metadata)
        for file in files:
            print("Saving File:", file.filename)
            self.save_file(file)
        return self.temp_dir_path
    
    def save_file(self, file):
        # Save the file to the temporary directory
        file.save(f"{self.temp_dir_path}/{file.filename}")