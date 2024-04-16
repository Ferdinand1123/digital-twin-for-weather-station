import pandas as pd

from station.dat_to_nc_converter import DatToNcConverter

class StationData:
        
    def __init__(self, name, folder_path: str) -> None:
        self.name = name
        self.converter = DatToNcConverter(name,
                                hourly=True,
                                directory=folder_path,
                                keep_original=True
                                )
        self.metadata = self.converter.meta_data
        self.converter.extract()
        self.converter.transform()
        self.df = self.converter.dataframe
        self.original_df = self.converter.original_df
        assert not self.df.empty, "Input Dataframe is empty"
        
    def find_gaps(self) -> None:
        hour_steps = self.df.index
        # find all hours between the first and last hour that are missing
        all_hours = pd.date_range(start=hour_steps.min(), end=hour_steps.max(), freq='h')
        missing_hours = all_hours.difference(hour_steps)
        return missing_hours.tolist()
    
    def get_all_months_in_df(self) -> None:
        # return all (year, month) tuples in the dataframe
        periods = self.df.index.to_period('M').unique().tolist()
        month_dict = {}
        for period in periods:
            if period.year not in month_dict:
                month_dict[period.year] = []
            month_dict[period.year].append(period.month)
        print("##### month dict", month_dict)
        return month_dict
    
    def export_as_nc(self, target_directory) -> None:
        # give netcdf rights to write in the target directory
        return self.converter.load(
            location = target_directory + "/")

    def __repr__(self) -> str:
        return f"{self.name} @ {self.metadata.get('latitude')}lat," + \
            f"{self.metadata.get('longitude')}lon between" + \
            f"{min(self.df.time.values)} and {max(self.df.time.values)}"