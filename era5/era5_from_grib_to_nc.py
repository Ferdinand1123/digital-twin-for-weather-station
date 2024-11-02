import os
import tempfile
import subprocess
import xarray as xr

class Era5DataFromGribToNc:
    
    def __init__(self, folder_path, era5_target_file_path) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir.name
        self._convert(folder_path)
        self._merge(era5_target_file_path)
        self.temp_dir.cleanup()

    def _convert(self, source_path):
        assert os.path.exists(source_path), "Folder with .grib files does not exist"
        assert len(os.listdir(source_path)), "No .grib files to convert"
        
        for file in os.listdir(source_path):
            if file.endswith(".grib"):
                print(f"Found {file}")
                self._convert_grib_to_nc(source_path, file)
        
    def _convert_grib_to_nc(self, source_path, file):
        # Paths for original and renamed NetCDF files
        nc_original_path = os.path.join(self.temp_dir_path, file.replace('.grib', '.nc'))
        nc_renamed_path = os.path.join(self.temp_dir_path, file.replace('.grib', '_renamed.nc'))
        
        # Convert GRIB to NetCDF using cdo
        cdo_command = f"cdo -f nc4 copy {os.path.join(source_path, file)} {nc_original_path}"
        subprocess.run(cdo_command, shell=True, check=True)
        assert os.path.exists(nc_original_path), "Conversion failed"
        
        # Open the original NetCDF file and rename variables
        ds = xr.open_dataset(nc_original_path)
        ds = self._rename_variables(ds)
        
        # Save to a new NetCDF file to avoid permission issues
        ds.to_netcdf(nc_renamed_path)
        assert os.path.exists(nc_renamed_path), "Renaming variables failed"
        
        # Optionally, remove the original NetCDF file if no longer needed
        os.remove(nc_original_path)
   
    def _rename_variables(self, ds):
        variable_mapping = {
            'var167': 't2m',      # 2 metre temperature
            'var228': 'tp',       # Total precipitation
            'var165': 'u10',      # 10 metre U wind component
            'var166': 'v10',      # 10 metre V wind component
            'var134': 'sp',       # Surface pressure
            # Add other mappings as needed
        }
        variables_to_rename = {var: new_var for var, new_var in variable_mapping.items() if var in ds.variables}
        ds = ds.rename(variables_to_rename)
        return ds

    def _merge(self, era5_file_path):
        assert os.path.exists(self.temp_dir_path), "Folder with unmerged .nc files does not exist"
        assert len(os.listdir(self.temp_dir_path)), "No .nc files to merge"
        
        print("Merging files...")
        cdo_command = f"cdo mergetime {self.temp_dir_path}/*.nc {era5_file_path}"
        subprocess.run(cdo_command, shell=True, check=True)
        assert os.path.exists(era5_file_path), "Merging failed"
        print(f"Merged ERA5 file saved into {era5_file_path}")
