import tempfile
import uuid
import shutil
import os
import json
import time


class DataSubmission:
    def __init__(self, name="", cookie=False):
        self.data = None
        self.measurement_dir = tempfile.TemporaryDirectory()
        self.measurement_dir_path = self.measurement_dir.name
        self.model_dir = tempfile.TemporaryDirectory()
        self.model_path = None
        self.name = name
        self.cookie = cookie
        self.status = ""

    def submit(self, files, model):
        # Submit data to the server
        print("Number of uploaded files:", len(files))
        for file in files:
            file.save(self.measurement_dir_path + "/" + file.filename)
        if model:
            self.model_path = self.model_dir.name + "/" + model.filename
            model.save(self.model_path)
        if not self.name:
            self.generate_name()
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
            self.name += "_model-" + self.model_path.split("/")[-1].split(".")[0]
          
    def add_model(self, model_source_path):
        self.model_path = self.model_dir.name + "/" + model_source_path.split("/")[-1]
        shutil.copy(model_source_path, self.model_path)
        self.generate_name()
        return
    
    def update_progress_status(self, status):
        self.status = status
        data_storage.connected_socket_responder.emit(self.cookie)
        return
    
        
    def cleanup(self):
        # Clean up the temporary directories
        if self.measurement_dir:
            self.measurement_dir.cleanup()
        if self.model_dir:
            self.model_dir.cleanup()


class DataStorage:
    def __init__(self):
        self.connected_socket_responder = None
        self._data_submissions = {}
        
    def add_data_submission(self, data_submission: DataSubmission) -> str:
        uid = str(uuid.uuid4())
        self._data_submissions[uid] = data_submission
        self.connected_socket_responder.emit(data_submission.cookie)
        return uid
        
    def get_data_submission(self, uid) -> DataSubmission:
        return self._data_submissions.get(uid)
    
    def get_all_available_datasets(self, cookie):
        # return names, uids of all available datasets
        return_list = [{
            "name": data.name,
            "uid": uid,
            "has_model": data.model_path is not None,
            "status": str(data.status)
        } for uid, data in self._data_submissions.items() if data.cookie == cookie]
        return return_list
    
    def delete_data_submission(self, uid):
        data_submission = self._data_submissions.get(uid)
        if data_submission:
            data_submission.cleanup()
            del self._data_submissions[uid]
        self.connected_socket_responder.emit(data_submission.cookie)
        return
    
        

class ConnectedSocketResponsder():
    
    def __init__(self, socketio):
        self._conns = {}
        self.socketio = socketio
        
        
    def add_connection(self, conn, cookie):
        if not cookie in self._conns.keys():
            self._conns[cookie] = []
        if not conn in self._conns[cookie]:
            self._conns[cookie].append(conn)
        
    def emit(self, cookie):
        for conn in self._conns[cookie]:
            available_datasets = data_storage.get_all_available_datasets(cookie)
            print("Emitting to:", conn, "datasets:", available_datasets)
            self.socketio.emit('update', available_datasets, room=conn)
        return
                
            
data_storage = DataStorage()