FROM continuumio/miniconda3:latest

# Set the working directory
WORKDIR /app

# Copy the application code into the container
COPY era5 /app/era5
COPY infilling /app/infilling
COPY station /app/station
COPY train_station_twin /app/train_station_twin
COPY utils /app/utils
COPY web_interface /app/web_interface
COPY app.py /app/app.py
COPY copernicus_api.env /app/copernicus_api.env
COPY requirements.txt /app/requirements.txt

# Install build tools including gcc and CDO
RUN apt-get update --fix-missing
RUN apt-get install -y gcc
RUN apt-get install -y cdo

# Clone the git repository
RUN git clone https://github.com/FREVA-CLINT/climatereconstructionAI.git crai

# Activate the Conda environment & set the FLASK_APP environment variable & install the requirements
# install the requirements
RUN conda env create -f ./crai/environment.yml && conda init bash
RUN ["conda", "run", "-n", "crai", "pip", "install", "./crai/"]
RUN ["conda", "run", "-n", "crai", "pip", "install", "-r", "./requirements.txt"]


# Start the flask app
CMD ["conda", "run", "-n", "crai", "python", "app.py"]