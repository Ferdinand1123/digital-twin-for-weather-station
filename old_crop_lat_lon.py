def find_nearest_lon_lat(asc_lon_list, desc_lat_list, station_lon, station_lat):
    print("search:", station_lon , " in asc_lon_list:", asc_lon_list)
    lat_nearest_idx = np.searchsorted(
        list(reversed(desc_lat_list)), station_lat)
    lat_nearest_idx = len(desc_lat_list) - lat_nearest_idx
    lon_nearest_idx = np.searchsorted(asc_lon_list, station_lon)
    print("returning:", lon_nearest_idx)
    return lon_nearest_idx, lat_nearest_idx


class Era5ForStationCropper():
    
    def __init__(self, station: StationData, era5_path: str, era5_target_path: str):
        self.station = station
        self.era5_path = era5_path
        self.era5_target_path = era5_target_path
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def execute(self):
        self.era5_path = self.crop_time_axis()
        self.era5_path = self.drop_along_time_axis()
        self.era5_path = self.crop_lat_lon_to_grid(do_export=True)
        print("Era5 for station cropped and exported to:", self.era5_target_path)
    
    def crop_lat_lon_to_grid(self, do_export=False, width=8, height=8):
        station_lat = self.station.metadata.get("latitude")
        station_lon = self.station.metadata.get("longitude") % 360
        saves_to = self.temp_dir.name + "/lat_lon_cropped.nc"
        xr_era5 = xr.open_dataset(self.era5_path)
        # reduce the lon and lat grid to width x height
        print("Lat: ", station_lat)
        print("Lon: ", station_lon)
        
        
        nearest_lon_idx, nearest_lat_idx = utils.find_nearest_lon_lat(
            xr_era5.lon.values, xr_era5.lat.values,
            station_lon, station_lat
        ) 

        print("nearest_lat_idx:", nearest_lat_idx, xr_era5.lat.values)
        print("nearest_lon_idx:", nearest_lon_idx, xr_era5.lon.values)
    
        nearest_lat = xr_era5.lat.values[nearest_lat_idx]
        nearest_lon = xr_era5.lon.values[nearest_lon_idx]
            
        print("nearest_lat:", nearest_lat)
        print("nearest_lon:", nearest_lon)
            
        if width % 2 == 0:
            # longitude
            nearest_is_smaller = None
            if station_lon < 10 or station_lon > 350: # avoid mistakes near the meridian
                nearest_is_smaller = nearest_lon + 20 % 360 < station_lon + 20 % 360
            else:
                nearest_is_smaller = nearest_lon < station_lon
            if nearest_is_smaller:
                print("nearest lon is smaller")
                crop_lon_idx_min = nearest_lon_idx - width // 2 + 1
                crop_lon_idx_max = nearest_lon_idx + width // 2
            else:
                print("nearest lon is bigger")
                crop_lon_idx_min = nearest_lon_idx - width // 2
                crop_lon_idx_max = nearest_lon_idx + width // 2 - 1
                
            # latitude
            # assert latitude is sorted descending
            assert xr_era5.lat.values[0] > xr_era5.lat.values[-1]
            nearest_is_bigger = nearest_lat > station_lat
            if nearest_is_bigger:
                print("nearest lat is bigger")
                crop_lat_idx_min = nearest_lat_idx - height // 2 + 1
                crop_lat_idx_max = nearest_lat_idx + height // 2
            else:
                print("nearest lat is smaller")
                crop_lat_idx_min = nearest_lat_idx - height // 2
                crop_lat_idx_max = nearest_lat_idx + height // 2 - 1
            
        else:
            crop_lon_idx_min = nearest_lon_idx - width // 2
            crop_lon_idx_max = nearest_lon_idx + width // 2
            crop_lat_idx_min = nearest_lat_idx - height // 2
            crop_lat_idx_max = nearest_lat_idx + height // 2
            
        
        print("crop_lon_idx_min:", crop_lon_idx_min)
        print("crop_lon_idx_max:", crop_lon_idx_max)    
        print("crop_lat_idx_min:", crop_lat_idx_min)
        print("crop_lat_idx_max:", crop_lat_idx_max)
        
        
        xr_era5 = xr_era5.isel(
            lon=slice(crop_lon_idx_min, crop_lon_idx_max + 1), # does not include the last index
            lat=slice(crop_lat_idx_min, crop_lat_idx_max + 1)
        )
        
        # Verify the longitude and latitude values used for cropping
        print("Lon values after cropping:", xr_era5['lon'].values)
        print("Lat values after cropping:", xr_era5['lat'].values)
        
        xr_era5.to_netcdf(saves_to)
        
        if do_export:
            os.system(f"cp {saves_to} {self.era5_target_path}")
            return self.era5_target_path
        return saves_to
    
    