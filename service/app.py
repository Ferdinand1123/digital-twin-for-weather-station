# flask to handle api requests

from flask import Flask, request, jsonify

from data_submission import DataSubmission
from dat_to_nc import DatToNC

app = Flask(__name__)

# Max content length for uploaded files
MAX_CONTENT_LENGTH = 1024 ** 3 # 1 GB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

@app.route('/api/data-submission', methods=['POST'])
def data_submission_api():
    uploaded_files = request.files.getlist('measurements')
    folder_path = DataSubmission().submit(uploaded_files, request.form)

    return "Data Submitted Successfully"
