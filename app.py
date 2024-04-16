
from flask import Flask, request, send_file

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from station.data_submission import DataSubmission, data_storage
from station.station import StationData
from infilling.evaluation_executer import EvaluatuionExecuter
from infilling.infilling_writer import InfillingWriter
from train_station_twin.training_executer import TrainingExecuter

from utils.utils import ProgressStatus

import time
import tempfile

import logging

app = Flask(__name__)

# Configure Flask app to log to stdout
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.INFO)

print("Starting the server")
print(f"using {tempfile.gettempdir()} as temporary directory")

# Max content length for uploaded files
MAX_CONTENT_LENGTH = 1024 ** 3 # 1 GB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.route('/api/data-submission', methods=['POST'])
def data_submission_api_point():
    uploaded_files =  request.files.getlist('measurements')
    model_file = request.files.get('model')
    cookie = request.form.get('cookie')
    data_submission = DataSubmission(cookie=cookie)
    data_submission.submit(uploaded_files, model_file)
    name = data_submission.name
    uid =  data_storage.add_data_submission(data_submission)
    return uid

@app.route('/api/fill-in/<uid>', methods=['GET'])
def api_fill_in_at_data_submission(uid):
    data_submission = data_storage.get_data_submission(uid)
    folder_path = data_submission.measurement_dir_path
    model_path = data_submission.model_path
    
    station = StationData(
        name=data_submission.name,
        folder_path=folder_path)
    
    evaluation = EvaluatuionExecuter(
        station=station,
        model_path=model_path)
    
    evaluation.extract()
    results_path = evaluation.execute()    
    
    infilling = InfillingWriter()
    
    output_path, plot_path = infilling.write_results(
        eval_results_path=results_path,
        station=station,
        plot=True
    ) 
    
    response = send_file(output_path, as_attachment=True)
    
    time.sleep(1000)
    
    evaluation.cleanup()
    infilling.cleanup()
    
    return response

@app.route('/api/train/<uid>', methods=['GET'])
async def api_train_at_data_submission(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    folder_path = data_submission.measurement_dir_path
    progress_status = ProgressStatus()
    data_submission.progress = progress_status
    progress_status.update_phase("Extracting Station Data")
    station = StationData(
        name=data_submission.name,
        folder_path=folder_path)
    progress_status.update_phase("Downloading ERA5 data")
    training = TrainingExecuter(
        station=station,
        progress=progress_status)
    
    output_path = training.execute()
    progress_status.update_phase("")
    data_submission.add_model(training.get_path_of_final_model())
    data_submission.add_pdf(training.get_pdf_path())
    
    response = send_file(output_path, as_attachment=True)
    
    training.cleanup()
    
    return response


@app.route('/api/available-datasets/<cookie>', methods=['GET'])
def available_datasets(cookie):
    return data_storage.get_all_available_datasets(cookie)


@app.route('/api/delete-dataset/<uid>', methods=['DELETE'])
def delete_dataset(uid):
    data_storage.delete_data_submission(uid)
    return "Dataset deleted"

@app.route('/api/training-results-as-pdf/<uid>', methods=['GET'])
def get_pdf(uid):
    data_submission = data_storage.get_data_submission(uid)
    return send_file(data_submission.pdf_path)

# serve index.html and other frontend files
@app.route('/web/<path:path>')
def send_frontend_files(path):
    return send_file(f'./web_interface/{path}')


if __name__ == '__main__':
    app.run(app, port=3000)