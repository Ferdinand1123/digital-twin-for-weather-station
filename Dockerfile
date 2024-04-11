FROM continuumio/miniconda3:latest

# Set the working directory
WORKDIR /

# Copy the application code into the container
COPY era5 /era5
COPY infilling /infilling
COPY station /station
COPY train_station_twin /train_station_twin
COPY utils /utils
COPY web_interface /web_interface
COPY app.py /app.py
COPY copernicus_api.env /copernicus_api.env
COPY requirements.txt /requirements.txt

# Clone the git repository
RUN git clone https://github.com/FREVA-CLINT/climatereconstructionAI.git crai

# Activate the Conda environment & set the FLASK_APP environment variable & install the requirements
# install the requirements
RUN conda env create -f /crai/environment.yml && \
    echo "conda activate crai"  >> ~/.bashrc && \
    pip install -r /requirements.txt

# Start the flask app
CMD ["conda", "run", "-n", "crai", "flask", "run", "--port=3000"]