from fpdf import FPDF
import os
import shutil
import tempfile
import xarray as xr
from infilling.evaluation_executer import EvaluationExecuter

from station.station import StationData
from train_station_twin.training_analysis import era5_vs_reconstructed_comparision_to_df, plot_n_steps_of_df
from utils.utils import ProgressStatus

from era5.era5_download_hook import Era5DownloadHook
from era5.era5_from_grib_to_nc import Era5DataFromGribToNc
from era5.era5_for_station import DownloadEra5ForStation, Era5ForStationCropper

class ValidationExecuter():
    
    def __init__(self, station: StationData, model_path: str, progress: ProgressStatus):
        self.station = station
        self.progress = progress
        
        self.progress.update_phase("Validating")
        
        assert station.name is not None
        assert station.metadata is not None
        assert station.metadata.get("latitude") is not None
        assert station.metadata.get("longitude") is not None
        self.temp_dir = tempfile.TemporaryDirectory()


        self.era5_path = self.temp_dir.name + '/era5_for_station.nc'
        self.model_path = model_path
        self.station_nc_file_path = self.station.export_as_nc(self.temp_dir.name)
        


        self.get_era5_for_station()
        self.validate()
        
        self.progress.update_phase("")
    
    
    def get_era5_for_station(self):
        era5_hook = Era5DownloadHook(lat=self.station.metadata.get("latitude"),
                                     lon=self.station.metadata.get("longitude"))

        temp_grib_dir = tempfile.TemporaryDirectory()

        DownloadEra5ForStation(
            station=self.station,
            grib_dir_path=temp_grib_dir.name,
            hook=era5_hook,
            progress=self.progress
        )

        era5_temp_path = self.temp_dir.name + '/era5_temp'

        self.progress.update_phase("Converts grib to nc")

        Era5DataFromGribToNc(
            temp_grib_dir.name,
            era5_target_file_path=era5_temp_path
        )

        temp_grib_dir.cleanup()

        self.progress.update_phase("Cropping ERA5")

        cropper = Era5ForStationCropper(
            station=self.station,
            era5_path=era5_temp_path,
            era5_target_path=self.era5_path
        )

        cropper.execute()
        cropper.cleanup()
    
    def validate(self):
        # to be used after execute
        assert os.path.exists(self.model_path), "Model not found after training"
        assert os.path.exists(self.era5_path)

        self.progress.update_phase("Evaluating")

        evaluation = EvaluationExecuter(
            station=self.station,
            model_path=self.model_path
        )
        # don't run evaluation.execute() because it will optain ERA5 to infill gaps

        # copy the era5 training data to the evaluation directory
        shutil.copy(self.era5_path, evaluation.era5_path)

        # prepare expected output cleaned
        evaluation.create_cleaned_nc_file()
        args_path = evaluation.get_eval_args_txt()
        reconstructed_path = evaluation.crai_evaluate(args_path)

        self.progress.update_phase("Plotting")

        df = era5_vs_reconstructed_comparision_to_df(
            era5_path=self.era5_path,
            reconstructed_path=reconstructed_path,
            measurements_path=self.station_nc_file_path
        )
        
        # keep reconstructed_median and era5_nearest and measurements
        export_df = df[["reconstructed_median", "era5_nearest", "measurements"]]
        # rename columns
        export_df = export_df.rename(columns={
            "reconstructed_median": "Reconstructed",
            "era5_nearest": "ERA5",
            "measurements": "Measurements"
        })
        export_df.to_csv(self.get_csv_path(), index=True)

        coords = {
            "station_lon": self.station.metadata.get("longitude"),
            "station_lat": self.station.metadata.get("latitude"),
            "era5_lons": xr.open_dataset(self.era5_path).lon.values,
            "era5_lats": xr.open_dataset(self.era5_path).lat.values
        }

        pdf = FPDF(format='A3')
        pdf.add_page(orientation='L')

        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=True,
            title=f"{self.station.name}, Difference to Measurements", 
            save_to=self.temp_dir.name
        )

        pdf.image(saved_to_path, h=240)

        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=False,
            title=f"{self.station.name}",
            save_to=self.temp_dir.name
        )
        pdf.image(saved_to_path, h=240)

        for _ in range(5):
            saved_to_path = plot_n_steps_of_df(
                df,
                coords=coords,
                as_delta=False,
                n=168,
                title=f"{self.station.name}, Random 7 Days ({_})",
                save_to=self.temp_dir.name
            )
            pdf.image(saved_to_path, h=240)
        
        df = df.resample('D').mean()
        
        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=True,
            title=f"{self.station.name} - Daily, delta to measurements",
            save_to=self.temp_dir.name
        )
        
        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=False,
            title=f"{self.station.name} - Daily",
            save_to=self.temp_dir.name
        )
        
        pdf.image(saved_to_path, h=240)
        
        df = df.resample('M').mean()
        
        saved_to_path = plot_n_steps_of_df(
            df,
            coords=coords,
            as_delta=False,
            title=f"{self.station.name} - Monthly",
            save_to=self.temp_dir.name
        )
        
        pdf.image(saved_to_path, h=240)
        
        
        pdf.output(self.get_pdf_path())
        
        self.progress.update_phase("")
        
        return self.get_pdf_path(), self.get_csv_path()
        
    def get_pdf_path(self):
        return self.temp_dir.name + '/validation.pdf'
    
    def get_csv_path(self):
        return self.temp_dir.name + '/validation.csv'