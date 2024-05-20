import pandas as pd

from matplotlib import pyplot as plt

from station.dat_to_nc_converter import DatToNcConverter

class StationData:
        
    def __init__(self, name, folder_path: str, progress=None,
                 first_n_files=None, mask_years=[]) -> None:
        self.name = name
        self.converter = DatToNcConverter(name,
                                hourly=True,
                                directory=folder_path,
                                keep_original=True
                                )
        self.metadata = self.converter.meta_data
        self.converter.extract(first_n_files=first_n_files, progress=progress)
        self.converter.transform()
        
        
        self.df = self.converter.dataframe
        
        # plot self.converter.dataframe tas column
        # add nan values in gaps to avoid plotting lines
        self.plot_df = self.df.copy()
        self.plot_df.reindex(pd.date_range(start=self.plot_df.index.min(),
                                           end=self.plot_df.index.max(),
                                           freq='H'))
        
        plt.plot(self.plot_df.index, self.plot_df["tas"], label="Available measurements")
        plt.xlabel("Time")
        plt.ylabel("Temperature (K)")
        
        self.df = self.df[~self.df.index.year.isin(mask_years)]
        self.plot_df = self.df.copy()
        self.plot_df.reindex(pd.date_range(start=self.plot_df.index.min(),
                                           end=self.plot_df.index.max(),
                                           freq='H'))
        plt.plot(self.plot_df.index, self.plot_df["tas"], label="Measurements used for training")
        
        # fig size
        plt.figure(figsize=(20, 10))
        
        # position legend outside of plot
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        
        
        plt.show()
        
        assert not self.df.empty, "Input Dataframe is empty"
        
    def find_gaps(self) -> None:
        available_hour_steps = self.df.index
        all_hour_steps = self.converter.original_df.index
        # find all hours between the first and last hour that are missing
        missing_hours = all_hour_steps.difference(available_hour_steps)
        return missing_hours.tolist()
    
    def get_all_months_in_df(self) -> None:
        # return all (year, month) tuples in the dataframe
        periods = self.df.index.to_period('M').unique().tolist()
        month_dict = {}
        for period in periods:
            if period.year not in month_dict:
                month_dict[period.year] = []
            month_dict[period.year].append(period.month)
        return month_dict
    
    def export_as_nc(self, target_directory) -> None:
        # give netcdf rights to write in the target directory
        return self.converter.load(
            location = target_directory + "/")

    def __repr__(self) -> str:
        return f"{self.name} @ {self.metadata.get('latitude')}lat," + \
            f"{self.metadata.get('longitude')}lon between" + \
            f"{min(self.df.time.values)} and {max(self.df.time.values)}"