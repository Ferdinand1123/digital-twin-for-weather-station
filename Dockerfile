FROM continuumio/miniconda:latest
# Set the working directory
WORKDIR /app

# Copy the application code into the container
COPY era5 ./era5
COPY infilling ./infilling
COPY station ./station
COPY train_station_twin ./train_station_twin
COPY utils ./utils
COPY web_interface ./web_interface
COPY app.py ./app.py
COPY copernicus_api.env ./copernicus_api.env
COPY requirements.txt ./requirements.txt
COPY crai ./crai

COPY boot.sh ./

RUN chmod +x boot.sh

# Install build tools including gcc and CDO
# RUN apt-get update --fix-missing
# RUN apt-get install -y gcc
# RUN apt-get install -y cdo

# Clone the git repository
# RUN git clone https://github.com/FREVA-CLINT/climatereconstructionAI.git crai

# Activate the Conda environment
RUN conda env create -f ./crai/environment.yml

RUN echo "source activate crai" &gt; ~/.bashrc
ENV PATH /opt/conda/envs/crai/bin:$PATH

# Install the Python dependencies
RUN pip install ./crai
RUN pip install -r requirements.txt

EXPOSE 3000

ENTRYPOINT ["./boot.sh"]