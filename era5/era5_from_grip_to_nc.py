import os
import tempfile
import subprocess

class Era5DataFromGribToNc:
        
    def __init__(self, folder_path, era5_file_path) -> None:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.temp_dir_path = self.temp_dir.name
            self._convert(folder_path)
            self._merge(era5_file_path)
            self.temp_dir.cleanup()

    def _convert(self, source_path):
        assert os.path.exists(source_path), "Folder with .grib files does not exist"
        assert len(os.listdir(source_path)), "No .grib files to convert"
        
        for file in os.listdir(source_path):
            if file.endswith(".grib"):
                self._convert_grib_to_nc(source_path, file)
    
    def _convert_grib_to_nc(self, source_path, file):
        nc_copied_path = self.temp_dir_path + '/' + file.replace('grib', 'nc')
        nc_copied_path_temp = nc_copied_path + '_temp'
        cdo_command = f"cdo -f nc copy {source_path}/{file} {nc_copied_path_temp}"
        subprocess.run(cdo_command, shell=True)
        assert os.path.exists(nc_copied_path_temp), "Conversion failed"
        rename_variable_from_var167_to_tas_command = \
            f"cdo chname,var167,tas {nc_copied_path_temp} {nc_copied_path}"
        subprocess.run(rename_variable_from_var167_to_tas_command, shell=True)
       
            
    def _merge(self, era5_file_path):
        assert os.path.exists(self.temp_dir_path), "Folder with unmerged .nc files does not exist"
        assert len(os.listdir(self.temp_dir_path)), "No .nc files to merge"
        
        for file in os.listdir(self.temp_dir_path):
            if file.endswith(".nc"):
                print(f"Found {file}")
        cdo_command = f"cdo cat {self.temp_dir_path}/*.nc {era5_file_path}"
        
        subprocess.run(cdo_command, shell=True)
        assert os.path.exists(era5_file_path), "Merging failed"
        print(f"Merged era5 file saved into {era5_file_path}")
