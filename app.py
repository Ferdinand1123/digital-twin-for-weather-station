
from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from station.data_submission import DataSubmission, data_storage
from station.station import StationData
from infilling.evaluation_executor import EvaluationExecutor
from infilling.infilling_writer import InfillingWriter
from train_station_twin.training_executor import TrainingExecutor
from train_station_twin.validation_executor import ValidationExecutor
from utils.utils import ProgressStatus

import time
import tempfile

import logging

app = Flask(__name__)
socketio = SocketIO(app)

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
    name = request.form.get('name')
    data_submission = DataSubmission(cookie=cookie, name=name)
    data_submission.submit(uploaded_files, model_file)
    name = data_submission.name
    uid =  data_storage.add_data_submission(data_submission)
    return uid

@app.route('/api/fill-in/<uid>', methods=['GET'])
def api_fill_in_at_data_submission(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    
    if not data_submission.model_path:
        return "Model missing", 404
    
    evaluation = EvaluationExecutor(
        station=data_submission.station,
        model_path=data_submission.model_path,
        progress=data_submission.progress)
    
    results_path = evaluation.execute()    
    
    infilling = InfillingWriter()
    
    output_path, plot_path = infilling.write_results(
        eval_results_path=results_path,
        station=data_submission.station,
        plot=True
    ) 
    data_submission.add_infilling(output_path)
    response = send_file(output_path, as_attachment=True)
    
    evaluation.cleanup()
    infilling.cleanup()
    
    return response

@app.route('/api/train/<uid>', methods=['GET'])
async def api_train_at_data_submission(uid):
    iterations = request.args.get('iterations')
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not iterations:
        return "Iterations count missing", 400
    try:
        iterations = int(iterations)
    except ValueError:
        return "Iterations count must be an integer", 400
    training = TrainingExecutor(
        station=data_submission.station,
        progress=data_submission.progress,
        iterations=iterations
    )
    
    output_path = await training.execute()
    data_submission.add_model(training.get_path_of_final_model())
    
    response = send_file(output_path, as_attachment=True)
    
    training.cleanup()
    
    return response


@app.route('/api/available-datasets/<cookie>', methods=['GET'])
def available_datasets(cookie):
    return data_storage.get_all_available_datasets(cookie)


@socketio.on('request_available_datasets')
def handle_request_available_datasets(cookie):
    data = data_storage.get_all_available_datasets(cookie)
    emit('available_datasets', data)


@app.route('/api/delete-dataset/<uid>', methods=['DELETE'])
def delete_dataset(uid):
    data_storage.delete_data_submission(uid)
    return "Dataset deleted"

@app.route('/api/validate-model/<uid>', methods=['GET'])
def get_pdf(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.model_path:
        return "Model missing", 404
    validation = ValidationExecutor(
        station=data_submission.station,
        model_path=data_submission.model_path,
        progress=data_submission.progress
    )
    data_submission.add_val_pdf(validation.get_pdf_path())
    data_submission.add_val_csv(validation.get_csv_path())
    data_submission.add_val_zip(validation.make_zip())
    return send_file(data_submission.val_pdf_path)

@app.route('/api/download-model/<uid>', methods=['GET'])
def send_model(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.model_path:
        return "Model missing", 404
    return send_file(data_submission.model_path)

@app.route('/api/download-validation-pdf/<uid>', methods=['GET'])
def send_validation_pdf(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.val_pdf_path:
        return "PDF missing", 404
    return send_file(data_submission.val_pdf_path)

@app.route('/api/download-validation-csv/<uid>', methods=['GET'])
def download_validation_csv(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.val_csv_path:
        return "CSV missing", 404
    return send_file(data_submission.val_csv_path)

@app.route('/api/download-validation-zip/<uid>', methods=['GET'])
def download_validation_zip(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.val_zip_path:
        return "ZIP missing", 404
    return send_file(data_submission.val_zip_path)

@app.route('/api/download-infilling/<uid>', methods=['GET'])
def download_infilling(uid):
    data_submission = data_storage.get_data_submission(uid)
    if not data_submission:
        return "Data submission not found", 404
    if not data_submission.infilling_path:
        return "Infilling missing", 404
    return send_file(data_submission.infilling_path)

# serve index.html and other frontend files
@app.route('/web/<path:path>')
def send_frontend_files(path):
    return send_file(f'./web_interface/{path}')


if __name__ == '__main__':
    app.run(app, port=3000)