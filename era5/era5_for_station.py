from ..crai.station_reconstruct.dat_to_nc import DatToNcConverter
from ..station.station import StationData

import tempfile


class CropEra5ForStation():
    
    def __init__(self, station: StationData, era5_path: str, era5_target_path: str):
        self.station = station
        self.era5_path = era5_path
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def execute(self):
        self.crop_lat_lon_to_grid()
        self.crop_time_axis()
        self.drop_along_time_axis()
        self.temp_dir.cleanup()
    
    def crop_lat_lon_to_grid(self, width=8, height=8):
        pass
    
    def crop_time_axis(self):
        pass
    
    def drop_along_time_axis(self):
        pass