import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg (non-interactive)

import matplotlib.pyplot as plt

class InfillingsPlotter():
    def __init__(self):
        self.input_df = None
        self.output_df = None
        self.full_df = None
    
    def pass_data(self, input_df, output_df):
        self.input_df = input_df
        self.output_df = output_df
        # rename the columns to measured and reconstructed
        self.input_df = self.input_df.rename(columns={"tas": "Measured"})
        self.output_df = self.output_df.rename(columns={"tas": "Reconstructed"})
    
    def _transform_df(self):
        self.full_df = self.input_df.join(self.output_df, how="outer")
        
        # make sure the dataframes are sorted by index
        self.full_df = self.full_df.sort_index()
        
        # transfer from K to C
        self.full_df["Measured"] = self.full_df["Measured"] - 273.15
        self.full_df["Reconstructed"] = self.full_df["Reconstructed"] - 273.15
    
    def plot(self, path="output.png"):
        self._transform_df()
        assert not self.full_df.empty, "Dataframe is empty"
        
        plt.plot(self.full_df.index, self.full_df["Measured"], label="Measured")
        plt.plot(self.full_df.index, self.full_df["Reconstructed"], label="Reconstructed")
        
        plt.legend()
        
        # rotate the x-axis labels
        plt.xticks(rotation=45)
        
        plt.savefig(path)
        plt.close()