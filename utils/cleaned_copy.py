import numpy as np
import xarray as xr

class CreateCleanedCopy:
    def __init__(self, original_path, cleaned_path):
        self.original_path = original_path
        self.cleaned_path = cleaned_path
        self._create_cleaned_nc_files()
        
    def _create_cleaned_nc_files(self):
        # rewrite all tas values to np.nan
        with xr.open_dataset(self.original_path) as ds:
            ds['tas'].values[:] = np.nan
            ds.to_netcdf(self.cleaned_path)
        return self.cleaned_path