import numpy as np
import xarray as xr

class FillAllTasWithValuesInNcFile():
    def __init__(self, values, original_path, save_to_path):
        if not isinstance(values, list) and not isinstance(values, np.ndarray):
            self.values = [values]
        else:
            self.values = values
            
        self.original_path = original_path
        self.save_to_path = save_to_path
        self._create_filled_nc_files()
        
    def _create_filled_nc_files(self):
        if len(self.values) == 1:
            value = self.values[0]
            with xr.open_dataset(self.original_path) as ds:
                ds['tas'].values[:] = value
                ds.to_netcdf(self.save_to_path)
        else:
            with xr.open_dataset(self.original_path) as ds:# Get the shape of the 'tas' variable
                tas_shape = ds['tas'].shape
                
                # Reshape self.values to match the shape of 'tas'
                repeated_values = self.values[:, np.newaxis, np.newaxis] * np.ones(
                    (len(self.values), 8, 8))
    
                # Assign the repeated values to the 'tas' variable
                ds['tas'].values[:, :, :] = repeated_values
                ds.to_netcdf(self.save_to_path)
        
        return self.save_to_path