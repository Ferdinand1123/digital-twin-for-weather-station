
from flask import Flask, request, send_file


from .station.data_submission import DataSubmission, DataStorage
from .station.station import StationData
from .infilling.infilling_process import InfillingProcess
from .infilling.infilling_plotter import InfillingsPlotter

# import sleep
import time

app = Flask(__name__)

# Max content length for uploaded files
MAX_CONTENT_LENGTH = 1024 ** 3 # 1 GB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

data_storage = DataStorage()

@app.route('/api/data-submission', methods=['POST'])
def data_submission_api_point():
    uploaded_files = request.files.getlist('measurements')
    model_file = request.files.get('model')
    data_submission = DataSubmission()
    data_submission.submit(uploaded_files, model_file)
    name = data_submission.name
    uid = data_storage.add_data_submission(data_submission)
    return uid

@app.route('/api/fill-in/<uid>', methods=['GET'])
def api_fill_in_at_data_submission(uid):
    data_submission = data_storage.get_data_submission(uid)
    folder_path = data_submission.measurement_dir.name
    model_path = data_submission.model_path
    
    station = StationData(
        name=data_submission.name,
        folder_path=folder_path)
    
    infilling_process = InfillingProcess(
        station=station,
        model_path=model_path)
    
    result_plotter = InfillingsPlotter()
    
    infilling_process.execute()    
    output_path = infilling_process.write_results(result_plotter)
    result_plotter.plot()
    
    response = send_file(output_path, as_attachment=True)
    
    time.sleep(100)
    
    infilling_process.cleanup()
    data_submission.cleanup()
    
    return response

@app.route('/api/available-datasets', methods=['GET'])
def get_available_datasets():
    return data_storage.get_all_available_datasets()


# serve index.html and other frontend files
@app.route('/web/<path:path>')
def send_frontend_files(path):
    return send_file(f'./web_interface/{path}')
