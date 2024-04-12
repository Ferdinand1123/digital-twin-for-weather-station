FROM continuumio/miniconda3:latest
# Set the working directory
WORKDIR /app


# Install build tools including gcc and CDO
RUN apt-get update --fix-missing
RUN apt-get install -y gcc
RUN apt-get install -y cdo

# Clone the git repository
RUN git clone https://github.com/FREVA-CLINT/climatereconstructionAI.git crai

# Activate the Conda environment

RUN conda env create -f ./crai/environment.yml && conda init bash
RUN echo "source activate crai" > ~/.bashrc
ENV PATH /opt/conda/envs/crai/bin:$PATH

# Install the Python dependencies
RUN pip install ./crai
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

EXPOSE 3000

# Copy the application code into the container
COPY era5 ./era5
COPY station ./station
COPY infilling ./infilling
COPY train_station_twin ./train_station_twin
COPY web_interface ./web_interface
COPY app.py ./app.py
COPY copernicus_api.env ./copernicus_api.env

COPY boot.sh ./

RUN chmod +x boot.sh
ENTRYPOINT ["./boot.sh"]