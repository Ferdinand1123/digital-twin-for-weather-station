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
        
        df = self.converter.dataframe
        plot_df = df.reindex(pd.date_range(start=df.index.min(),
                                           end=df.index.max(),
                                           freq='H'))
        
        plt.plot(plot_df.index, plot_df["tas"], label="Measurements excluded in training")
        
        self.converter.dataframe = self.converter.dataframe[~self.converter.dataframe.index.year.isin(mask_years)]
        self.df = self.converter.dataframe
        df = self.df.copy()
        plot_df = df.reindex(pd.date_range(start=df.index.min(),
                                           end=df.index.max(),                                          
                                           freq='H'))
        
        plt.plot(plot_df.index, plot_df["tas"], label="Measurements used for training")
        
        # set title
        if len(mask_years) > 0:
            plt.title(f"Measured by {self.name}-Station with {', '.join(map(str, mask_years))} masked out @ {self.metadata.get('latitude')}lat," + \
                        f"{self.metadata.get('longitude')}lon")
        else:
            plt.title(f"Measured by {self.name}-Station @ {self.metadata.get('latitude')}lat," + \
                        f"{self.metadata.get('longitude')}lon")
        
        # rotate x-axis labels
        plt.xticks(rotation=45)
        
        # set y-axis label
        plt.ylabel("Temperature [K]")
        
        # position legend to the top right above/outside the plot
        plt.legend(loc='upper right', bbox_to_anchor=(1, 1.125))
        
        # font size of legend
        plt.rcParams.update({'font.size': 10})
    
        # font size of axis labels
        plt.rcParams.update({'axes.labelsize': 12})
        
        # font size of title
        plt.rcParams.update({'axes.titlesize': 16})
        
        # fig size
        plt.gcf().set_size_inches(20, 10)
        
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